"""Subagent orchestration over the existing TurnEngine and BackgroundTaskManager."""

from __future__ import annotations

import asyncio
import threading
import uuid
from typing import Callable

from ..background_tasks import (
    AgentRunResult,
    AgentTaskAdapter,
    BackgroundTaskManager,
    BackgroundTaskRecord,
    BackgroundTaskSpec,
)
from ..engine import TurnEngine
from ..events import EventType
from .cohort import DelegationCohortTracker
from .models import ForegroundSubagentResult, SubagentProfile
from .registry import SubagentProfileRegistry, builtin_subagent_profiles


EngineFactory = Callable[[BackgroundTaskRecord, SubagentProfile], TurnEngine]
EngineSaver = Callable[[BackgroundTaskRecord, TurnEngine], None]


class TurnEngineTaskAdapter(AgentTaskAdapter):
    def __init__(
        self,
        record: BackgroundTaskRecord,
        profile: SubagentProfile,
        *,
        engine_factory: EngineFactory,
        engine_saver: EngineSaver,
    ) -> None:
        self.record = record
        self.profile = profile
        self.engine_factory = engine_factory
        self.engine_saver = engine_saver
        self._engine: TurnEngine | None = None
        self._lock = threading.RLock()

    def _get_engine(self) -> TurnEngine:
        with self._lock:
            if self._engine is None:
                self._engine = self.engine_factory(self.record, self.profile)
            return self._engine

    def run(self, message, *, emit, cancel_event):
        engine = self._get_engine()

        async def execute() -> AgentRunResult:
            report = ""
            status = "failed"
            error = None
            watcher: asyncio.Task[None] | None = None

            async def watch_cancel() -> None:
                while not cancel_event.is_set():
                    await asyncio.sleep(0.05)
                engine.request_interrupt()

            try:
                if cancel_event.is_set():
                    engine.request_interrupt()
                    return AgentRunResult(status="cancelled")
                watcher = asyncio.create_task(watch_cancel())
                async for event in engine.run(
                    message,
                    source={
                        "kind": "subagent",
                        "parent_session_id": self.record.owner_session_id,
                        "task_id": self.record.id,
                    },
                    trace_source_kind="subagent",
                    parent_trace_id=self.record.parent_trace_id,
                ):
                    if cancel_event.is_set():
                        engine.request_interrupt()
                    if event.type == EventType.ASSISTANT_MESSAGE and event.data.get("text"):
                        report = str(event.data["text"])
                    elif event.type in {EventType.TOOL_STARTED, EventType.TOOL_FINISHED}:
                        name = str(event.data.get("name") or "tool")
                        emit("event", f"{event.type.value}:{name}\n")
                    elif event.type == EventType.TURN_END:
                        raw = str(event.data.get("status") or "failed")
                        status = "completed" if raw == "completed" else "cancelled" if raw == "interrupted" else "failed"
                    elif event.type == EventType.ERROR:
                        error = str(event.data.get("error") or "subagent failed")
            except Exception as exc:
                error = str(exc)
                status = "failed"
            finally:
                if watcher is not None:
                    watcher.cancel()
                    try:
                        await watcher
                    except asyncio.CancelledError:
                        pass
                self.engine_saver(self.record, engine)
            if cancel_event.is_set():
                status = "cancelled"
            return AgentRunResult(report=report, status=status, error=error)

        return asyncio.run(execute())

    def steer(self, message: str) -> None:
        self._get_engine().queue_steering(message)

    def stop(self) -> None:
        with self._lock:
            if self._engine is not None:
                self._engine.request_interrupt()


class SubagentRuntime:
    def __init__(
        self,
        task_manager: BackgroundTaskManager,
        *,
        engine_factory: EngineFactory,
        engine_saver: EngineSaver,
        profiles: SubagentProfileRegistry | None = None,
        cohort_tracker: DelegationCohortTracker | None = None,
    ) -> None:
        self.task_manager = task_manager
        self.engine_factory = engine_factory
        self.engine_saver = engine_saver
        self.profiles = profiles or builtin_subagent_profiles()
        self.cohort_tracker = cohort_tracker

    def adapter_for_record(self, record: BackgroundTaskRecord) -> TurnEngineTaskAdapter:
        if record.kind != "agent" or not record.profile_id:
            raise ValueError(f"task {record.id} is not an agent task")
        profile = self.profiles.require(record.profile_id)
        return TurnEngineTaskAdapter(
            record,
            profile,
            engine_factory=self.engine_factory,
            engine_saver=self.engine_saver,
        )

    def start(
        self,
        *,
        task: str,
        profile_id: str,
        owner_session_id: str,
        workspace: str,
        description: str | None = None,
        model: str | None = None,
        parent_trace_id: str | None = None,
        join_cohort: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> BackgroundTaskRecord:
        profile = self.profiles.require(profile_id)
        if profile.agent_id == "code" and not workspace:
            raise ValueError(f"subagent profile '{profile_id}' requires a workspace")
        child_session_id = f"__subagent__{uuid.uuid4().hex}"
        meta = {
            "agent_id": profile.agent_id,
            "isolation": profile.isolation,
            **(metadata or {}),
        }
        spec = BackgroundTaskSpec(
            kind="agent",
            owner_session_id=owner_session_id,
            description=(description or task).strip()[:240] or profile.title,
            workspace=workspace,
            profile_id=profile.id,
            child_session_id=child_session_id,
            parent_trace_id=parent_trace_id,
            model=model or profile.model,
            metadata=meta,
        )
        # Create a provisional record solely to bind the adapter. The manager assigns the
        # real task id, so adapter construction happens after start via a small proxy.
        holder: dict[str, TurnEngineTaskAdapter] = {}

        class LazyAdapter:
            def __init__(self) -> None:
                self.bound_record: BackgroundTaskRecord | None = None
                self.pending_steering: list[str] = []
                self.stop_pending = False

            def bind(self, record: BackgroundTaskRecord) -> None:
                self.bound_record = record

            def _adapter(self, record: BackgroundTaskRecord) -> TurnEngineTaskAdapter:
                if "value" not in holder:
                    holder["value"] = self_runtime.adapter_for_record(record)
                    for pending in self.pending_steering:
                        holder["value"].steer(pending)
                    self.pending_steering.clear()
                    if self.stop_pending:
                        holder["value"].stop()
                return holder["value"]

            def run(self, message, *, emit, cancel_event):
                if cancel_event.is_set():
                    return AgentRunResult(status="cancelled")
                record = self.bound_record
                if record is None:
                    raise RuntimeError("subagent adapter was not bound to a task")
                return self._adapter(record).run(
                    message, emit=emit, cancel_event=cancel_event
                )

            def steer(self, message):
                if "value" not in holder:
                    self.pending_steering.append(message)
                else:
                    holder["value"].steer(message)

            def stop(self):
                if "value" in holder:
                    holder["value"].stop()
                else:
                    self.stop_pending = True

        self_runtime = self
        record = self.task_manager.start_agent(
            spec, message=task, adapter=LazyAdapter()
        )
        if join_cohort and self.cohort_tracker is not None:
            self.cohort_tracker.register(
                record.owner_session_id,
                record.id,
                parent_trace_id=record.parent_trace_id,
                profile_id=record.profile_id or profile.id,
                description=record.description,
            )
        return record

    def run_foreground(self, **kwargs) -> ForegroundSubagentResult:
        kwargs = dict(kwargs)
        kwargs["join_cohort"] = False
        task = self.start(**kwargs)
        profile = self.profiles.require(task.profile_id or "")
        timeout = max(30.0, float(profile.max_turns * 30))
        done = self.task_manager.wait(
            task.id, timeout=timeout, owner_session_id=task.owner_session_id
        )
        if done.status not in {"completed", "failed", "cancelled", "interrupted"}:
            self.task_manager.stop(
                task.id, owner_session_id=task.owner_session_id, mode="wrap_up"
            )
            done = self.task_manager.wait(
                task.id, timeout=5, owner_session_id=task.owner_session_id
            )
        terminal_status = (
            done.status
            if done.status in {"completed", "failed", "cancelled", "interrupted"}
            else "interrupted"
        )
        terminal_error = done.error
        if terminal_status == "interrupted" and not terminal_error:
            terminal_error = "subagent did not stop before the foreground timeout"
        page = self.task_manager.read_output(
            task.id, owner_session_id=task.owner_session_id, max_chars=100_000
        )
        report = "".join(
            chunk.text for chunk in page.chunks if chunk.stream == "assistant"
        )
        return ForegroundSubagentResult(
            task_id=task.id,
            profile_id=profile.id,
            status=terminal_status,
            report=report,
            error=terminal_error,
        )
