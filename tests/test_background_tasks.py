from __future__ import annotations

import sys
import threading
import time

import pytest

from coworker.background_tasks import (
    AgentRunResult,
    BackgroundTaskManager,
    BackgroundTaskSpec,
    BackgroundTaskStore,
)


class FakeAgent:
    def __init__(self, *, gate: threading.Event | None = None, fail: bool = False):
        self.messages: list[str] = []
        self.steered: list[str] = []
        self.stopped = False
        self.gate = gate
        self.fail = fail

    def run(self, message, *, emit, cancel_event):
        self.messages.append(message)
        emit("event", "started\n")
        if self.gate is not None:
            self.gate.wait(timeout=3)
        if cancel_event.is_set():
            return AgentRunResult(status="cancelled")
        if self.fail:
            return AgentRunResult(status="failed", error="boom")
        return AgentRunResult(report=f"answer:{message}")

    def steer(self, message):
        self.steered.append(message)

    def stop(self):
        self.stopped = True
        if self.gate is not None:
            self.gate.set()


def _manager(tmp_path, **kwargs):
    store = BackgroundTaskStore(tmp_path / "coworker.db", **kwargs)
    return BackgroundTaskManager(store)


def _agent_spec(owner="s1", child="subagent-1"):
    return BackgroundTaskSpec(
        kind="agent",
        owner_session_id=owner,
        description="research",
        workspace=".",
        profile_id="explore",
        child_session_id=child,
    )


def test_agent_lifecycle_output_and_owner_isolation(tmp_path):
    manager = _manager(tmp_path)
    task = manager.start_agent(_agent_spec(), message="hello", adapter=FakeAgent())
    done = manager.wait(task.id, timeout=3, owner_session_id="s1")
    assert done.status == "completed"
    assert done.run_count == 1
    page = manager.read_output(task.id, owner_session_id="s1")
    assert "answer:hello" in "".join(c.text for c in page.chunks)
    assert page.next_cursor >= 2
    with pytest.raises(ValueError, match="unknown task"):
        manager.read_output(task.id, owner_session_id="other")
    manager.close()


def test_agent_message_steers_running_then_resumes_completed_context(tmp_path):
    manager = _manager(tmp_path)
    gate = threading.Event()
    adapter = FakeAgent(gate=gate)
    task = manager.start_agent(_agent_spec(), message="first", adapter=adapter)
    deadline = time.time() + 2
    while manager.get(task.id).status != "running" and time.time() < deadline:
        time.sleep(0.01)
    manager.send_message(task.id, "during", owner_session_id="s1")
    assert adapter.steered == ["during"]
    gate.set()
    assert manager.wait(task.id, timeout=3).status == "completed"

    again = manager.send_message(task.id, "second", owner_session_id="s1")
    assert again.status in {"queued", "running", "completed"}
    done = manager.wait(task.id, timeout=3)
    assert done.status == "completed" and done.run_count == 2
    assert adapter.messages == ["first", "second"]
    manager.close()


def test_stop_agent_and_completion_listener_isolated(tmp_path):
    manager = _manager(tmp_path)
    gate = threading.Event()
    adapter = FakeAgent(gate=gate)
    seen = []
    manager.register_completion_listener(lambda record: seen.append(record.status))
    manager.register_completion_listener(lambda _record: 1 / 0)
    task = manager.start_agent(_agent_spec(), message="wait", adapter=adapter)
    manager.stop(task.id, owner_session_id="s1")
    done = manager.wait(task.id, timeout=3)
    assert done.status == "cancelled"
    assert adapter.stopped is True
    assert seen == ["cancelled"]
    manager.close()


def test_change_listener_reports_created_status_output_and_terminal(tmp_path):
    manager = _manager(tmp_path)
    seen: list[tuple[str, str, int]] = []
    manager.register_change_listener(
        lambda event: seen.append(
            (event.change, event.task.status, event.task.output_size)
        )
    )
    manager.register_change_listener(lambda _event: 1 / 0)
    task = manager.start_agent(
        _agent_spec(), message="observe", adapter=FakeAgent()
    )
    assert manager.wait(task.id, timeout=3).status == "completed"
    assert seen[0][0] == "created"
    assert ("status", "running") in {(change, status) for change, status, _ in seen}
    assert any(change == "output" and size > 0 for change, _, size in seen)
    assert seen[-1][:2] == ("status", "completed")
    manager.close()


def test_parallel_gather_keeps_input_order_and_failures(tmp_path):
    manager = _manager(tmp_path)
    one = manager.start_agent(_agent_spec(child="c1"), message="one", adapter=FakeAgent())
    two = manager.start_agent(
        _agent_spec(child="c2"), message="two", adapter=FakeAgent(fail=True)
    )
    gathered = manager.gather([two.id, one.id], timeout=3, owner_session_id="s1")
    assert [r.id for r in gathered] == [two.id, one.id]
    assert [r.status for r in gathered] == ["failed", "completed"]
    manager.close()


def test_shell_task_runs_reads_and_rejects_messages(tmp_path):
    manager = _manager(tmp_path)
    command = (
        "Write-Output 12345"
        if sys.platform == "win32"
        else f'"{sys.executable}" -c "print(12345)"'
    )
    task = manager.start_shell(
        BackgroundTaskSpec(
            kind="shell",
            owner_session_id="s1",
            description="echo",
            workspace=str(tmp_path),
        ),
        command=command,
    )
    done = manager.wait(task.id, timeout=10)
    assert done.status == "completed" and done.exit_code == 0
    output = manager.read_output(task.id)
    assert "12345" in "".join(c.text for c in output.chunks)
    with pytest.raises(ValueError, match="do not accept"):
        manager.send_message(task.id, "no")
    manager.close()


def test_shell_task_can_be_stopped(tmp_path):
    manager = _manager(tmp_path)
    command = (
        "Write-Output started; Start-Sleep -Seconds 30"
        if sys.platform == "win32"
        else "echo started; sleep 30"
    )
    task = manager.start_shell(
        BackgroundTaskSpec(
            kind="shell",
            owner_session_id="s1",
            description="sleep",
            workspace=str(tmp_path),
        ),
        command=command,
    )
    deadline = time.time() + 3
    while time.time() < deadline:
        page = manager.read_output(task.id)
        if "started" in "".join(c.text for c in page.chunks):
            break
        time.sleep(0.02)
    stopped = manager.stop(task.id, owner_session_id="s1")
    assert stopped.status == "cancelled"
    manager.close()


class StickyAgent:
    """Ignores cooperative cancel so stop must force-cancel after the wait timeout."""

    def __init__(self):
        self.entered = threading.Event()
        self.stopped = False
        self._release = threading.Event()

    def run(self, message, *, emit, cancel_event):
        emit("event", "stuck\n")
        self.entered.set()
        # Intentionally ignore cancel_event; only test teardown releases the wait.
        self._release.wait(timeout=60)
        return AgentRunResult(status="completed", report="should-not-win")

    def steer(self, message):
        return None

    def stop(self):
        self.stopped = True


def test_agent_stop_force_cancels_when_adapter_ignores_signal(tmp_path):
    from coworker.background_tasks.manager import FORCE_CANCEL_ERROR

    manager = _manager(tmp_path)
    adapter = StickyAgent()
    task = manager.start_agent(_agent_spec(), message="hang", adapter=adapter)
    assert adapter.entered.wait(timeout=3)
    stopped = manager.stop(task.id, owner_session_id="s1", mode="immediate")
    assert stopped.status == "cancelled"
    assert stopped.error == FORCE_CANCEL_ERROR
    assert adapter.stopped is True
    page = manager.read_output(task.id, owner_session_id="s1")
    text = "".join(c.text for c in page.chunks)
    assert "stop requested" in text
    assert "force-cancelled" in text
    assert "wrap-up requested" not in text
    # Late worker finish must not revive the force-cancelled row.
    late = manager.wait(task.id, timeout=1, owner_session_id="s1")
    assert late.status == "cancelled" and late.error == FORCE_CANCEL_ERROR
    adapter._release.set()
    manager.close()


class WrapUpCompletingAgent:
    """Completes with a partial report when steered to wrap up (D-187)."""

    def __init__(self):
        self.entered = threading.Event()
        self.steered: list[str] = []
        self._finish = threading.Event()

    def run(self, message, *, emit, cancel_event):
        emit("event", "researching\n")
        self.entered.set()
        while not cancel_event.is_set():
            if self._finish.wait(timeout=0.05):
                emit("assistant", "partial report ready\n")
                return AgentRunResult(status="completed", report="partial report")
        return AgentRunResult(status="cancelled")

    def steer(self, message):
        self.steered.append(message)
        self._finish.set()

    def stop(self):
        return None


def test_wrap_up_stop_steers_and_allows_completed(tmp_path):
    manager = _manager(tmp_path)
    adapter = WrapUpCompletingAgent()
    task = manager.start_agent(_agent_spec(), message="research", adapter=adapter)
    assert adapter.entered.wait(timeout=3)
    stopped = manager.stop(task.id, owner_session_id="s1", mode="wrap_up")
    assert stopped.status == "completed"
    assert stopped.error is None
    assert adapter.steered
    assert any("部分报告" in m or "收尾" in m or "结束" in m for m in adapter.steered)
    page = manager.read_output(task.id, owner_session_id="s1")
    text = "".join(c.text for c in page.chunks)
    assert "wrap-up requested" in text
    assert "force-cancelled" not in text
    manager.close()


def test_wrap_up_stop_force_cancels_after_grace_when_ignored(tmp_path, monkeypatch):
    from coworker.background_tasks import manager as mgr_mod
    from coworker.background_tasks.manager import FORCE_CANCEL_ERROR

    monkeypatch.setattr(mgr_mod, "WRAP_UP_GRACE_SECONDS", 0.15)
    manager = _manager(tmp_path)
    adapter = StickyAgent()
    task = manager.start_agent(_agent_spec(), message="hang", adapter=adapter)
    assert adapter.entered.wait(timeout=3)
    stopped = manager.stop(task.id, owner_session_id="s1", mode="wrap_up")
    assert stopped.status == "cancelled"
    assert stopped.error == FORCE_CANCEL_ERROR
    page = manager.read_output(task.id, owner_session_id="s1")
    text = "".join(c.text for c in page.chunks)
    assert "wrap-up requested" in text
    assert "force-cancelled" in text
    adapter._release.set()
    manager.close()


def test_store_reconciles_incomplete_and_cleans_terminal_rows(tmp_path):
    store = BackgroundTaskStore(
        tmp_path / "coworker.db", retention_days=1, max_terminal_tasks=1
    )
    now = time.time()
    from coworker.background_tasks.models import BackgroundTaskRecord

    running = BackgroundTaskRecord(
        id="agent-old",
        kind="agent",
        status="running",
        owner_session_id="s1",
        description="old",
        created_at=now - 10,
        updated_at=now - 10,
    )
    store.put(running)
    assert store.reconcile_incomplete() == 1
    assert store.get("agent-old").status == "interrupted"

    for i in range(2):
        record = running.model_copy(
            update={
                "id": f"done-{i}",
                "status": "completed",
                "created_at": now + i,
                "updated_at": now + i,
                "finished_at": now + i,
            }
        )
        store.put(record)
    assert store.cleanup(now=now + 100) >= 1
    assert len(store.list()) <= 1
    store.close()


def test_local_executor_delegates_legacy_shell_tools_to_unified_manager(tmp_path):
    from coworker.tools import ToolRegistry
    from coworker.tools.shell import LocalExecutor, shell_tools

    manager = _manager(tmp_path)
    executor = LocalExecutor(
        cwd=tmp_path, background_manager=manager, owner_session_id="s1"
    )
    reg = ToolRegistry()
    reg.register_all(shell_tools(executor))
    command = "Write-Output unified" if sys.platform == "win32" else "echo unified"
    started = reg.execute(
        "run_shell", {"command": command, "run_in_background": True}
    )
    assert started["task_id"].startswith("shell-")
    deadline = time.time() + 5
    output = ""
    while time.time() < deadline:
        page = reg.execute("shell_task_output", {"task_id": started["task_id"]})
        output += page["output"]
        if page["status"] == "exited":
            break
        time.sleep(0.02)
    assert "unified" in output
    record = manager.get(started["task_id"], owner_session_id="s1")
    assert record is not None and record.kind == "shell" and record.status == "completed"
    assert manager.get(started["task_id"], owner_session_id="s2") is None
    executor.close()
    manager.close()
