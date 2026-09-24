import asyncio
from copy import deepcopy

from coworker.engine import TurnEngine
from coworker.events import EventType
from coworker.permissions import PermissionEngine
from coworker.providers import AssistantTurn, StreamChunk, ToolCall
from coworker.tools import ToolRegistry
from tests.test_engine import ScriptedProvider, _collect


def engine(tmp_path, turns, limit=150, messages=None):
    registry = ToolRegistry()
    executed = []
    def record(value: int):
        executed.append(value)
        return {"value": value}
    registry.register(record)
    e = TurnEngine(provider=ScriptedProvider(turns), registry=registry,
                   permissions=PermissionEngine(workspace_root=tmp_path),
                   model="test", max_iterations=limit, messages=messages)
    e.compaction_settings = lambda: {"enabled": False}
    return e, executed


def call(i):
    return AssistantTurn(tool_calls=[ToolCall(id=f"id{i}", name="record", arguments={"value": i})], finish_reason="tool_calls")


def test_long_task_segments_automatically_without_repeating_tools(tmp_path):
    e, executed = engine(tmp_path, [call(i) for i in range(55)] + [AssistantTurn(text="done", finish_reason="stop")])
    snapshots = []
    e.checkpoint_sink = lambda: snapshots.append(deepcopy(e.messages))
    events = _collect(e, "long task")
    assert executed == list(range(55))
    assert events[-1].data["status"] == "completed"
    assert any(ev.type == EventType.CHECKPOINT and ev.data["iterations"] == 50 for ev in events)
    assert snapshots


def test_budget_pause_restores_and_continues_without_repeating_write(tmp_path):
    e, executed = engine(tmp_path, [call(1), call(2)], limit=2)
    events = _collect(e, "complete work")
    assert events[-1].data["status"] == "budget_paused"
    assert executed == [1, 2]
    restored, written = engine(tmp_path, [AssistantTurn(text="done", finish_reason="stop")], limit=2, messages=deepcopy(e.messages))
    async def resume():
        return [ev async for ev in restored.resume()]
    assert asyncio.run(resume())[-1].data["status"] == "completed"
    assert written == []
    assert restored._runtime["model_calls"] == 3


def test_unknown_inflight_operation_is_not_reexecuted(tmp_path):
    e, executed = engine(tmp_path, [call(1)])
    saved = []
    def checkpoint():
        saved.append(deepcopy(e.messages))
        if e._runtime["inflight"]:
            raise OSError("disk unavailable")
    e.checkpoint_sink = checkpoint
    try:
        _collect(e, "write once")
    except OSError:
        pass
    assert executed == []
    restored, written = engine(tmp_path, [AssistantTurn(text="please reconcile", finish_reason="stop")], messages=saved[-1])
    async def resume():
        return [ev async for ev in restored.resume()]
    events = asyncio.run(resume())
    assert written == []
    assert any(ev.data.get("reason") == "execution_state_unknown" for ev in events)


def test_length_truncation_continues_then_pauses_and_never_executes_partial_tool(tmp_path):
    turns = [AssistantTurn(text="partial", finish_reason="length", tool_calls=call(i).tool_calls) for i in range(3)]
    e, executed = engine(tmp_path, turns)
    events = _collect(e, "long output")
    assert executed == []
    assert events[-1].data["status"] == "truncated"
    assert sum(ev.type == EventType.CONTINUATION for ev in events) == 2


def test_partial_transport_continues_with_preserved_text(tmp_path):
    class Partial(ScriptedProvider):
        def stream(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                yield StreamChunk(text_delta="first part")
                raise ConnectionError("connection reset")
            yield StreamChunk(turn=AssistantTurn(text="second part", finish_reason="stop"))
    e, _ = engine(tmp_path, [])
    e.provider = Partial([])
    events = _collect(e, "finish")
    assert events[-1].data["status"] == "completed"
    assert e._runtime["iterations"] == 1 and e._runtime["recovery_retries"] == 1
    assert any(m.get("content") == "first part" for m in e.messages)


def test_malformed_tool_args_are_rejected_before_execution(tmp_path):
    malformed = AssistantTurn(tool_calls=[ToolCall("x", "record", {"_raw": '{"value":'})])
    e, executed = engine(tmp_path, [malformed, AssistantTurn(text="done")])
    events = _collect(e, "write")
    assert not executed
    assert any(ev.data.get("reason") == "incomplete_tool_arguments" for ev in events)


def test_no_progress_pauses_with_specific_reason(tmp_path):
    e, executed = engine(tmp_path, [call(1) for _ in range(4)])
    events = _collect(e, "task")
    assert events[-1].data["status"] == "blocked"
    assert "相同结果" in events[-1].data["text"]
