from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from coworker.events import Event, EventType
from coworker.scenarios import ScenarioResolver
from coworker.tracing import TurnTrace, TurnTraceRecorder, TurnTraceStore
from coworker.turn_planner import TurnPlanner
from coworker.config import Config


def _plan():
    tools = ("lookup_chemical_identity", "web_search", "ask_user")
    return TurnPlanner(
        config=Config(), available_tool_names=lambda: tools
    ).plan("查询 CAS 67-56-1")


def test_trace_aggregates_names_usage_and_outcomes_without_content() -> None:
    recorder = TurnTraceRecorder(
        session_id="s1", model="test:model", plan=_plan(), source_kind="background"
    )
    recorder.observe(Event(EventType.TOOL_PROPOSED, {"name": "lookup_chemical_identity", "arguments": {"query": "secret"}}))
    recorder.observe(Event(EventType.TOOL_FINISHED, {"name": "lookup_chemical_identity", "outcome": {"status": "success"}, "result_preview": "secret result"}))
    recorder.observe(Event(EventType.ASSISTANT_MESSAGE, {"text": "secret answer", "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}}))
    recorder.observe(Event(EventType.TURN_END, {"status": "completed"}))
    trace = recorder.finish()
    dumped = trace.model_dump_json()
    assert trace.tool_calls == 1
    assert trace.model_calls == 1
    assert trace.total_tokens == 15
    assert trace.outcome_counts == {"success": 1}
    assert "secret" not in dumped
    assert "arguments" not in dumped
    assert "result_preview" not in dumped


def test_trace_counts_general_subagent_tool_and_keeps_parent_link() -> None:
    recorder = TurnTraceRecorder(
        session_id="child",
        model="m",
        plan=None,
        source_kind="subagent",
        parent_trace_id="parent-trace",
    )
    recorder.observe(Event(EventType.TOOL_PROPOSED, {"name": "start_subagent"}))
    trace = recorder.finish()
    assert trace.parent_trace_id == "parent-trace"
    assert trace.subagent_calls == 1


def test_trace_keeps_cancelled_turn_interrupted() -> None:
    recorder = TurnTraceRecorder(session_id="s", model="m", plan=None)
    recorder.observe(Event(EventType.INTERRUPTED, {"reason": "cancelled"}))
    assert recorder.finish().status == "interrupted"


def test_trace_schema_rejects_message_content_fields() -> None:
    data = TurnTraceRecorder(session_id="s", model="m", plan=None).finish().model_dump()
    data["prompt"] = "must not persist"
    with pytest.raises(Exception):
        TurnTrace.model_validate(data)


def test_trace_store_lists_filters_and_prunes_rows(tmp_path) -> None:
    store = TurnTraceStore(tmp_path / "trace.db", retention_days=30, max_rows=2)
    base = TurnTraceRecorder(session_id="s1", model="m", plan=None).finish()
    old = base.model_copy(update={"trace_id": "old", "started_at": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()})
    one = base.model_copy(update={"trace_id": "one"})
    two = base.model_copy(update={"trace_id": "two", "session_id": "s2"})
    three = base.model_copy(update={"trace_id": "three"})
    for item in (old, one, two, three):
        store.append(item)
    assert store.get("old") is None
    assert len(store.list(limit=500)) == 2
    assert all(item.session_id == "s1" for item in store.list(session_id="s1"))
    assert store.get("three") is not None
    store.close()
