import asyncio
import json
from pathlib import Path

from coworker import build_info
from coworker.events import EventType
from coworker.providers import AssistantTurn, ToolCall
from coworker.context_budget import estimate
from tests.test_compaction_engine import CompactingProvider, long_history, make_engine, collect
from tests.test_tool_discovery import registry
from tests.test_runtime_resume import engine


def test_compaction_reaches_target_and_does_not_immediately_repeat(tmp_path):
    provider = CompactingProvider([AssistantTurn(text="完成") for _ in range(2)])
    e = make_engine(tmp_path, provider, messages=long_history(turns=20, bulk=3000), cap=6000)
    collect(e, "继续处理")
    diag = e.compaction_state.diagnostics
    assert diag["target_met"] and diag["after_tokens"] <= diag["target_tokens"]
    collect(e, "谢谢")
    assert len(provider.summary_calls) == 1
    transcript = Path(e.compaction_state.transcript_path).read_text(encoding="utf-8")
    assert "request 0" in transcript


def test_fixed_prompt_pressure_stops_once_with_budget_diagnostics(tmp_path):
    history = long_history()
    history[0]["content"] = "固定提示" * 4000
    provider = CompactingProvider([AssistantTurn(text="must not run")])
    e = make_engine(tmp_path, provider, messages=history, cap=3000)
    events = collect(e)
    assert events[-1].type == EventType.ERROR
    assert events[-1].data["error_type"] == "ContextBudgetExceeded"
    assert provider.main_calls == 0
    assert len(provider.summary_calls) == 1


def test_400_tools_real_outbound_discovery_then_cold_tool_execution(tmp_path):
    turns = [
        AssistantTurn(tool_calls=[ToolCall("s", "search_tools", {"query": "mcp_rare_399"})]),
        AssistantTurn(tool_calls=[ToolCall("l", "load_tools", {"names": ["mcp_rare_399"]})]),
        AssistantTurn(tool_calls=[ToolCall("r", "mcp_rare_399", {})]),
        AssistantTurn(text="done", finish_reason="stop"),
    ]
    e, _ = engine(tmp_path, turns)
    e.registry = registry()
    sent = []
    complete = e.provider.complete
    def record(**kwargs):
        sent.append(kwargs["tools"])
        return complete(**kwargs)
    e.provider.complete = record
    async def run():
        return [event async for event in e.run("使用冷门工具")]
    events = asyncio.run(run())
    assert len(sent[0]) == 2
    assert "mcp_rare_399" in {s["function"]["name"] for s in sent[2]}
    assert all(estimate(tools) <= 12000 for tools in sent)
    assert any(ev.type == EventType.TOOL_FINISHED and ev.data.get("name") == "mcp_rare_399" and ev.data.get("status") == "ok" for ev in events)
    assert events[-1].data["status"] == "completed"
    restored, _ = engine(tmp_path, [], messages=e.messages)
    restored.registry = registry()
    assert "mcp_rare_399" in {schema["function"]["name"] for schema in restored._provider_tools()}


def test_packaged_build_identity_reads_build_time_stamp(monkeypatch, tmp_path):
    identity = {"runtime_revision": "test", "source_commit": "abc", "source_dirty": False}
    (tmp_path / "build-info.json").write_text(json.dumps(identity), encoding="utf-8")
    monkeypatch.setattr(build_info.sys, "frozen", True, raising=False)
    monkeypatch.setattr(build_info.sys, "_MEIPASS", str(tmp_path), raising=False)
    build_info.build_identity.cache_clear()
    try:
        assert build_info.build_identity() == identity
    finally:
        build_info.build_identity.cache_clear()
