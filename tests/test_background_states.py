import threading
import time
import pytest

from coworker.background_tasks import BackgroundTaskManager, BackgroundTaskStore, BackgroundTaskSpec, AgentRunResult
from coworker.subagents import SubagentRuntime
from coworker.events import Event, EventType


@pytest.mark.parametrize("status", ["budget_paused", "truncated", "blocked", "completed", "interrupted"])
def test_child_preserves_engine_status(tmp_path, status):
    class Engine:
        async def run(self, *args, **kwargs):
            yield Event(EventType.ASSISTANT_MESSAGE, {"text": "partial"})
            yield Event(EventType.TURN_END, {"status": status, "text": "why"})
        def request_interrupt(self):
            pass
    manager = BackgroundTaskManager(BackgroundTaskStore(tmp_path / "tasks.db"))
    runtime = SubagentRuntime(manager, engine_factory=lambda *_: Engine(), engine_saver=lambda *_: None)
    try:
        result = runtime.run_foreground(task="read", profile_id="research", owner_session_id="s", workspace=str(tmp_path))
        assert result.status == status and result.reason == "why" and result.report == "partial"
    finally:
        manager.close()


def test_wait_timeout_leaves_task_running(tmp_path, monkeypatch):
    done = threading.Event()
    class Engine:
        async def run(self, *args, **kwargs):
            import asyncio
            while not done.is_set():
                await asyncio.sleep(.01)
            yield Event(EventType.TURN_END, {"status": "completed"})
        def request_interrupt(self):
            raise AssertionError("waiting timeout must not stop the task")
    manager = BackgroundTaskManager(BackgroundTaskStore(tmp_path / "tasks.db"))
    runtime = SubagentRuntime(manager, engine_factory=lambda *_: Engine(), engine_saver=lambda *_: None)
    original = manager.wait
    monkeypatch.setattr(manager, "wait", lambda id, **kw: original(id, timeout=.05))
    try:
        result = runtime.run_foreground(task="read", profile_id="research", owner_session_id="s", workspace=str(tmp_path))
        assert result.status in {"queued", "running"}
    finally:
        done.set()
        if 'result' in locals():
            original(result.task_id, timeout=2)
        manager.close()


def test_output_pages_preserve_every_character(tmp_path):
    from coworker.background_tasks.models import BackgroundTaskRecord
    store = BackgroundTaskStore(tmp_path / "tasks.db")
    store.put(BackgroundTaskRecord(id="a", kind="agent", status="completed", owner_session_id="s",
                                  description="long", created_at=1, updated_at=1))
    texts = ["起点" + "a" * 37 + "终点", "second" * 11]
    for text in texts:
        store.append_output("a", stream="assistant", text=text)
    cursor = offset = 0
    parts = []
    for _ in range(100):
        page = store.read_output("a", cursor=cursor, offset=offset, max_chars=7)
        parts.extend(c.text for c in page.chunks)
        cursor, offset = page.next_cursor, page.next_offset
        if not page.truncated:
            break
    assert "".join(parts) == "".join(texts)
    store.close()


def test_max_five_active_per_group(tmp_path):
    manager = BackgroundTaskManager(BackgroundTaskStore(tmp_path / "tasks.db"))
    gate, lock = threading.Event(), threading.Lock()
    counts = {"active": 0, "peak": 0}
    class Adapter:
        def run(self, message, *, emit, cancel_event):
            with lock:
                counts["active"] += 1
                counts["peak"] = max(counts["peak"], counts["active"])
            gate.wait(2)
            with lock:
                counts["active"] -= 1
            return AgentRunResult()
        def stop(self):
            gate.set()
    try:
        tasks = [manager.start_agent(BackgroundTaskSpec(kind="agent", owner_session_id="s", description="t",
                 metadata={"task_group": "g"}), message="x", adapter=Adapter()) for _ in range(8)]
        deadline = time.monotonic() + 2
        while counts["peak"] < 5 and time.monotonic() < deadline:
            time.sleep(.01)
        assert counts["peak"] == 5
        gate.set()
        manager.gather([t.id for t in tasks], timeout=3)
        assert counts["peak"] == 5
    finally:
        gate.set()
        manager.close()
