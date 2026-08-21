"""D-175: cohort completion wiring smoke tests."""

from __future__ import annotations

import asyncio
import threading
import time
from types import SimpleNamespace

from coworker.background_tasks.models import BackgroundTaskChange, BackgroundTaskRecord
from coworker.selfwake import WakeStore
from coworker.server.manager import SessionManager
from coworker.subagents.cohort import (
    DelegationCohortTracker,
    format_cohort_synthesis_message,
)


def _record(**kwargs) -> BackgroundTaskRecord:
    data = dict(
        id="agent-1",
        kind="agent",
        status="running",
        owner_session_id="sess-1",
        description="branch",
        workspace="",
        profile_id="research",
        child_session_id="__subagent__x",
        parent_task_id=None,
        parent_trace_id="trace-1",
        model=None,
        created_at=1.0,
        updated_at=1.0,
        started_at=1.0,
        finished_at=None,
        run_count=1,
        output_size=0,
        exit_code=None,
        error=None,
        metadata={},
    )
    data.update(kwargs)
    return BackgroundTaskRecord(**data)


def _start_loop() -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    loop = asyncio.new_event_loop()

    def _run() -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    deadline = time.time() + 2
    while not loop.is_running() and time.time() < deadline:
        time.sleep(0.01)
    assert loop.is_running()
    return loop, thread


def _stop_loop(loop: asyncio.AbstractEventLoop) -> None:
    loop.call_soon_threadsafe(loop.stop)
    time.sleep(0.05)
    loop.close()


def test_format_message_mentions_short_gather():
    tracker = DelegationCohortTracker()
    tracker.register("s", "a1", parent_trace_id="t", profile_id="research")
    tracker.register("s", "a2", parent_trace_id="t")
    tracker.on_terminal("a1", status="completed")
    ready = tracker.on_terminal("a2", status="cancelled")
    assert ready is not None
    msg = format_cohort_synthesis_message(ready)
    assert "子智能体汇合通知" in msg
    assert "background_task_gather" in msg
    assert "cancelled" in msg


def test_session_manager_handler_delivers_once(tmp_path):
    delivered: list[tuple] = []
    resumed = {"n": 0}
    loop, _thread = _start_loop()

    async def broadcast_session(session_id, payload):
        return None

    async def resume_due_wakes():
        resumed["n"] += 1
        return 0

    async def deliver_to_session(session_id, message, *, source=None):
        delivered.append((session_id, message, source))

    mgr = SimpleNamespace(
        wakes=WakeStore(tmp_path / "wakes.json"),
        delegation_cohorts=DelegationCohortTracker(tmp_path / "cohorts.json"),
        _background_task_event_loop=loop,
        broadcast_session=broadcast_session,
        resume_due_wakes=resume_due_wakes,
        deliver_to_session=deliver_to_session,
        _background_task_dict=lambda record: record.model_dump(),
    )
    mgr.delegation_cohorts.register(
        "sess-1", "agent-1", parent_trace_id="trace-1", profile_id="research"
    )
    mgr.delegation_cohorts.register(
        "sess-1", "agent-2", parent_trace_id="trace-1", profile_id="research"
    )

    handler = SessionManager._on_background_task_change
    handler(
        mgr,
        BackgroundTaskChange(
            change="status",
            task=_record(id="agent-1", status="completed", finished_at=2.0),
        ),
    )
    time.sleep(0.1)
    assert delivered == []

    handler(
        mgr,
        BackgroundTaskChange(
            change="status",
            task=_record(
                id="agent-2",
                status="failed",
                error="boom",
                finished_at=3.0,
            ),
        ),
    )
    deadline = time.time() + 2
    while not delivered and time.time() < deadline:
        time.sleep(0.02)
    assert len(delivered) == 1
    session_id, message, source = delivered[0]
    assert session_id == "sess-1"
    assert "子智能体汇合通知" in message
    assert source["kind"] == "subagent_cohort_complete"
    assert set(source["task_ids"]) == {"agent-1", "agent-2"}
    assert resumed["n"] >= 1

    handler(
        mgr,
        BackgroundTaskChange(
            change="status",
            task=_record(id="agent-2", status="failed", error="boom"),
        ),
    )
    time.sleep(0.1)
    assert len(delivered) == 1
    _stop_loop(loop)


def test_complete_job_marks_wake_due(tmp_path):
    wakes = WakeStore(tmp_path / "wakes.json")
    wake = wakes.add_completion("sess-1", "agent-9", note="wait")
    marked = wakes.complete_job("agent-9")
    assert any(w.id == wake.id and w.state == "due" for w in marked)
