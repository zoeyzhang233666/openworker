"""Unified lifecycle manager for in-process Agent runs and detached Shell processes."""

from __future__ import annotations

import concurrent.futures
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .models import (
    AgentRunResult,
    BackgroundTaskChange,
    BackgroundTaskRecord,
    BackgroundTaskSpec,
    TERMINAL_TASK_STATUSES,
    TaskOutputPage,
    TaskStatus,
)
from .store import BackgroundTaskStore


class AgentTaskAdapter(Protocol):
    def run(
        self,
        message: str,
        *,
        emit: Callable[[str, str], None],
        cancel_event: threading.Event,
    ) -> AgentRunResult: ...

    def steer(self, message: str) -> None: ...

    def stop(self) -> None: ...


AgentAdapterFactory = Callable[[BackgroundTaskRecord], AgentTaskAdapter]
CompletionListener = Callable[[BackgroundTaskRecord], None]
TaskChangeListener = Callable[[BackgroundTaskChange], None]


@dataclass
class _ActiveRun:
    cancel: threading.Event
    adapter: AgentTaskAdapter | "_ShellAdapter"
    future: concurrent.futures.Future[None]


FORCE_CANCEL_ERROR = "stop requested; force-cancelled"
IMMEDIATE_STOP_WAIT_SECONDS = 3.0
WRAP_UP_GRACE_SECONDS = 90.0
WRAP_UP_PROMPT = (
    "【收尾请求】请立即根据已收集的证据，在共享工作区用 write_file/edit_file 写好部分报告"
    "（标明未完成处），然后结束本任务。不要再开启新的长检索或新工具链。"
)


class _ShellAdapter:
    def __init__(self, command: str, cwd: str, env: dict[str, str] | None = None):
        self.command = command
        self.cwd = str(Path(cwd).expanduser().resolve())
        self.env = {**os.environ, **(env or {})}
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def run(
        self,
        _message: str,
        *,
        emit: Callable[[str, str], None],
        cancel_event: threading.Event,
    ) -> AgentRunResult:
        if cancel_event.is_set():
            return AgentRunResult(status="cancelled")
        if sys.platform == "win32":
            argv = ["powershell.exe", "-NoProfile", "-Command", self.command]
            kwargs: dict[str, object] = {
                "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
            }
        else:
            argv = ["/bin/bash", "-c", self.command]
            kwargs = {"start_new_session": True}
        proc = subprocess.Popen(
            argv,
            cwd=self.cwd,
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            **kwargs,
        )
        with self._lock:
            self._proc = proc
        assert proc.stdout is not None
        for line in proc.stdout:
            emit("stdout", line)
            if cancel_event.is_set():
                self.stop()
                break
        code = proc.wait()
        if cancel_event.is_set():
            return AgentRunResult(status="cancelled")
        if code == 0:
            return AgentRunResult(status="completed")
        return AgentRunResult(status="failed", error=f"shell exited with code {code}")

    @property
    def exit_code(self) -> int | None:
        with self._lock:
            return self._proc.poll() if self._proc is not None else None

    def steer(self, _message: str) -> None:
        raise ValueError("shell tasks do not accept messages")

    def stop(self) -> None:
        with self._lock:
            proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                )
            except (OSError, subprocess.SubprocessError):
                pass
            if proc.poll() is None:
                try:
                    proc.kill()
                except OSError:
                    pass
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError):
                pass


class BackgroundTaskManager:
    def __init__(
        self,
        store: BackgroundTaskStore,
        *,
        agent_adapter_factory: AgentAdapterFactory | None = None,
        max_workers: int = 8,
    ) -> None:
        self.store = store
        self.agent_adapter_factory = agent_adapter_factory
        self._pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(2, int(max_workers)), thread_name_prefix="chemclaw-task"
        )
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._active: dict[str, _ActiveRun] = {}
        self._agent_adapters: dict[str, AgentTaskAdapter] = {}
        self._abandoned: set[str] = set()
        self._listeners: dict[str, CompletionListener] = {}
        self._change_listeners: dict[str, TaskChangeListener] = {}
        self.store.reconcile_incomplete(reason="ChemClaw restarted; task was interrupted")

    def start_agent(
        self, spec: BackgroundTaskSpec, *, message: str, adapter: AgentTaskAdapter
    ) -> BackgroundTaskRecord:
        if spec.kind != "agent":
            raise ValueError("agent task requires kind='agent'")
        record = self._create_record(spec)
        binder = getattr(adapter, "bind", None)
        if callable(binder):
            binder(record)
        with self._lock:
            self._agent_adapters[record.id] = adapter
        return self._submit(record, message, adapter)

    def start_shell(
        self,
        spec: BackgroundTaskSpec,
        *,
        command: str,
        env: dict[str, str] | None = None,
    ) -> BackgroundTaskRecord:
        if spec.kind != "shell":
            raise ValueError("shell task requires kind='shell'")
        if not spec.workspace:
            raise ValueError("shell task requires a workspace")
        record = self._create_record(spec)
        return self._submit(record, "", _ShellAdapter(command, spec.workspace, env))

    def get(
        self, task_id: str, *, owner_session_id: str | None = None
    ) -> BackgroundTaskRecord | None:
        record = self.store.get(task_id)
        if record is None:
            return None
        if owner_session_id is not None and record.owner_session_id != owner_session_id:
            return None
        return record

    def list(
        self,
        *,
        owner_session_id: str | None = None,
        status: TaskStatus | None = None,
        limit: int = 100,
    ) -> list[BackgroundTaskRecord]:
        return self.store.list(
            owner_session_id=owner_session_id, status=status, limit=limit
        )

    def read_output(
        self,
        task_id: str,
        *,
        owner_session_id: str | None = None,
        cursor: int = 0,
        max_chars: int = 20_000,
    ) -> TaskOutputPage:
        self._require(task_id, owner_session_id)
        return self.store.read_output(task_id, cursor=cursor, max_chars=max_chars)

    def send_message(
        self, task_id: str, message: str, *, owner_session_id: str | None = None
    ) -> BackgroundTaskRecord:
        record = self._require(task_id, owner_session_id)
        if record.kind != "agent":
            raise ValueError("shell tasks do not accept messages")
        text = str(message or "").strip()
        if not text:
            raise ValueError("message is required")
        with self._lock:
            active = self._active.get(task_id)
            if active is not None and not active.future.done():
                active.adapter.steer(text)
                self._append_output(
                    task_id, stream="event", text="follow-up message queued\n"
                )
                return self._require(task_id, owner_session_id)
            adapter = self._agent_adapters.get(task_id)
            if adapter is None:
                if self.agent_adapter_factory is None:
                    raise ValueError("agent task cannot be resumed in this process")
                adapter = self.agent_adapter_factory(record)
                self._agent_adapters[task_id] = adapter
        queued = record.model_copy(
            update={
                "status": "queued",
                "updated_at": time.time(),
                "finished_at": None,
                "error": None,
                "exit_code": None,
            }
        )
        self.store.put(queued)
        self._notify_change("status", queued)
        return self._submit(queued, text, adapter)

    def stop(
        self,
        task_id: str,
        *,
        owner_session_id: str | None = None,
        mode: str = "immediate",
    ) -> BackgroundTaskRecord:
        if mode not in {"immediate", "wrap_up"}:
            raise ValueError(f"unknown stop mode: {mode}")
        record = self._require(task_id, owner_session_id)
        if mode == "wrap_up" and record.kind != "agent":
            mode = "immediate"

        if mode == "wrap_up":
            with self._lock:
                active = self._active.get(task_id)
                if active is None or active.future.done():
                    return record
                adapter = active.adapter
            self._append_output(task_id, stream="system", text="wrap-up requested\n")
            try:
                adapter.steer(WRAP_UP_PROMPT)
            except Exception:
                pass
            waited = self.wait(
                task_id,
                timeout=WRAP_UP_GRACE_SECONDS,
                owner_session_id=owner_session_id,
            )
            if waited.status in TERMINAL_TASK_STATUSES:
                return waited
            # Fall through to hard stop after grace.

        signalled = False
        with self._lock:
            active = self._active.get(task_id)
            if active is None or active.future.done():
                return self._require(task_id, owner_session_id)
            active.cancel.set()
            active.adapter.stop()
            signalled = True
        self._append_output(task_id, stream="system", text="stop requested\n")
        if not signalled:
            return self._require(task_id, owner_session_id)
        waited = self.wait(
            task_id,
            timeout=IMMEDIATE_STOP_WAIT_SECONDS,
            owner_session_id=owner_session_id,
        )
        if waited.status in TERMINAL_TASK_STATUSES:
            return waited
        return self._force_cancel(task_id, owner_session_id=owner_session_id)

    def _force_cancel(
        self, task_id: str, *, owner_session_id: str | None = None
    ) -> BackgroundTaskRecord:
        """Mark a stuck run cancelled so UI/parent gather can proceed.

        The worker future may still finish later; `_run` must not revive this terminal
        status once the task id is in `_abandoned`.
        """
        with self._condition:
            current = self._require(task_id, owner_session_id)
            if current.status in TERMINAL_TASK_STATUSES:
                return current
            self._abandoned.add(task_id)
            active = self._active.pop(task_id, None)
            if active is not None:
                active.cancel.set()
                try:
                    active.adapter.stop()
                except Exception:
                    pass
            finished = time.time()
            cancelled = current.model_copy(
                update={
                    "status": "cancelled",
                    "updated_at": finished,
                    "finished_at": finished,
                    "error": FORCE_CANCEL_ERROR,
                }
            )
            self.store.put(cancelled)
            self._notify_change("status", cancelled)
            listeners = list(self._listeners.values())
            for listener in listeners:
                try:
                    listener(cancelled)
                except Exception:
                    pass
            self._condition.notify_all()
        self._append_output(task_id, stream="system", text="stop force-cancelled\n")
        return cancelled

    def wait(
        self,
        task_id: str,
        *,
        timeout: float | None = None,
        owner_session_id: str | None = None,
    ) -> BackgroundTaskRecord:
        deadline = None if timeout is None else time.monotonic() + max(0.0, timeout)
        with self._condition:
            while True:
                record = self._require(task_id, owner_session_id)
                if record.status in TERMINAL_TASK_STATUSES:
                    return record
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return record
                self._condition.wait(timeout=remaining)

    def gather(
        self,
        task_ids: list[str] | tuple[str, ...],
        *,
        timeout: float | None = None,
        owner_session_id: str | None = None,
    ) -> list[BackgroundTaskRecord]:
        deadline = None if timeout is None else time.monotonic() + max(0.0, timeout)
        out: list[BackgroundTaskRecord] = []
        for task_id in task_ids:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            out.append(
                self.wait(
                    task_id, timeout=remaining, owner_session_id=owner_session_id
                )
            )
        return out

    def register_completion_listener(
        self, listener: CompletionListener
    ) -> Callable[[], None]:
        listener_id = uuid.uuid4().hex
        with self._lock:
            self._listeners[listener_id] = listener

        def unregister() -> None:
            with self._lock:
                self._listeners.pop(listener_id, None)

        return unregister

    def register_change_listener(
        self, listener: TaskChangeListener
    ) -> Callable[[], None]:
        """Observe persisted task changes without owning lifecycle semantics.

        Listeners are best-effort UI/transport adapters: failures never affect the task.
        REST/SQLite remains the recovery authority.
        """
        listener_id = uuid.uuid4().hex
        with self._lock:
            self._change_listeners[listener_id] = listener

        def unregister() -> None:
            with self._lock:
                self._change_listeners.pop(listener_id, None)

        return unregister

    def close(self, *, wait: bool = False) -> None:
        with self._lock:
            active = list(self._active.values())
        for item in active:
            item.cancel.set()
            item.adapter.stop()
        self._pool.shutdown(wait=wait, cancel_futures=not wait)

    def _create_record(self, spec: BackgroundTaskSpec) -> BackgroundTaskRecord:
        now = time.time()
        prefix = "agent" if spec.kind == "agent" else "shell"
        record = BackgroundTaskRecord(
            id=f"{prefix}-{uuid.uuid4().hex[:12]}",
            kind=spec.kind,
            status="queued",
            owner_session_id=spec.owner_session_id,
            description=spec.description.strip(),
            workspace=spec.workspace,
            profile_id=spec.profile_id,
            child_session_id=spec.child_session_id,
            parent_task_id=spec.parent_task_id,
            parent_trace_id=spec.parent_trace_id,
            model=spec.model,
            created_at=now,
            updated_at=now,
            metadata=dict(spec.metadata),
        )
        self.store.put(record)
        self._notify_change("created", record)
        return record

    def _submit(
        self,
        record: BackgroundTaskRecord,
        message: str,
        adapter: AgentTaskAdapter | _ShellAdapter,
    ) -> BackgroundTaskRecord:
        cancel = threading.Event()
        with self._lock:
            # Hold the lifecycle lock across submit + registration. A very short task may
            # otherwise finish and pop itself before `_active` has been installed.
            future = self._pool.submit(self._run, record.id, message, adapter, cancel)
            self._active[record.id] = _ActiveRun(cancel, adapter, future)
        return self._require(record.id, record.owner_session_id)

    def _run(
        self,
        task_id: str,
        message: str,
        adapter: AgentTaskAdapter | _ShellAdapter,
        cancel: threading.Event,
    ) -> None:
        record = self._require(task_id, None)
        now = time.time()
        running = record.model_copy(
            update={
                "status": "running",
                "started_at": now,
                "updated_at": now,
                "run_count": record.run_count + 1,
                "finished_at": None,
            }
        )
        self.store.put(running)
        self._notify_change("status", running)

        def emit(stream: str, text: str) -> None:
            if text:
                self._append_output(task_id, stream=stream, text=str(text))

        try:
            result = adapter.run(message, emit=emit, cancel_event=cancel)
        except Exception as exc:
            result = AgentRunResult(status="failed", error=str(exc))
        if result.report:
            emit("assistant", result.report)
        with self._condition:
            if task_id in self._abandoned:
                # stop() already published a terminal cancelled row; keep that authority.
                self._abandoned.discard(task_id)
                self._active.pop(task_id, None)
                self._condition.notify_all()
                return
            current = self._require(task_id, None)
            finished = time.time()
            status = "cancelled" if cancel.is_set() else result.status
            exit_code = adapter.exit_code if isinstance(adapter, _ShellAdapter) else None
            updated = current.model_copy(
                update={
                    "status": status,
                    "updated_at": finished,
                    "finished_at": finished,
                    "exit_code": exit_code,
                    "error": result.error,
                }
            )
            # Publish terminal state and completion callbacks under the lifecycle lock so
            # `wait()` cannot return before listeners for that run have fired.
            self.store.put(updated)
            self._notify_change("status", updated)
            self._active.pop(task_id, None)
            listeners = list(self._listeners.values())
            for listener in listeners:
                try:
                    listener(updated)
                except Exception:
                    pass
            self._condition.notify_all()
        try:
            self.store.cleanup()
        except Exception:
            pass

    def _append_output(self, task_id: str, *, stream: str, text: str) -> None:
        self.store.append_output(task_id, stream=stream, text=text)
        current = self.store.get(task_id)
        if current is not None:
            self._notify_change("output", current)

    def _notify_change(
        self, change: str, record: BackgroundTaskRecord
    ) -> None:
        event = BackgroundTaskChange(change=change, task=record)
        with self._lock:
            listeners = list(self._change_listeners.values())
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                pass

    def _require(
        self, task_id: str, owner_session_id: str | None
    ) -> BackgroundTaskRecord:
        record = self.get(task_id, owner_session_id=owner_session_id)
        if record is None:
            raise ValueError(f"unknown task: {task_id}")
        return record
