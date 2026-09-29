"""Offline reproductions of the MCP-discovery/document/truncation failure path."""
import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from coworker.agent import build_engine, _LONG_TASK_GUIDANCE
from coworker.agents import get_agent
from coworker.events import EventType
from coworker.fast_answer import AnswerTextFilter, FastWebBudget
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient, StreamChunk, ToolCall
from coworker.task_budget import TaskBudgetStore
from coworker.tool_discovery import ToolDiscovery
from coworker.tool_policy import TurnToolPolicy
from tests.test_engine import _collect
from tests.test_runtime_resume import engine, call
from tests.test_tool_discovery import registry


MCP = "mcp__chemical__get_price_trend"


def add_mcp(reg, fn=None):
    def spot(product: str, limit: int = 1):
        return fn(product, limit) if fn else {"price": 1000, "unit": "元/吨", "date": "2026-09-29", "source": "离线模拟"}
    spot.__name__ = MCP
    reg.register(spot, schema={"type": "function", "function": {
        "name": MCP, "description": "查询化工产品的现货价格数据，支持按品名取最新报价。",
        "parameters": {"type": "object", "properties": {"product": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["product"]}}})


def test_chinese_multiword_discovery_and_first_schema_with_large_catalog():
    reg = registry()
    add_mcp(reg)
    discovery = ToolDiscovery(reg, lambda: TurnToolPolicy(), lambda: 2500)
    assert discovery.search("甲醇 价格 行情")["tools"][0]["name"] == MCP
    assert discovery.prime_mcp("甲醇现在什么价") == [MCP]
    assert MCP in {s["function"]["name"] for s in discovery.schemas()}
    reg.retain(set(reg.names()) - {MCP})
    assert not discovery.prime_mcp("甲醇现在什么价")
    assert MCP not in {s["function"]["name"] for s in discovery.schemas()}
    add_mcp(reg)
    assert discovery.prime_mcp("甲醇现货价格") == [MCP]
    denied = ToolDiscovery(reg, lambda: TurnToolPolicy(no_external_network=True), lambda: 2500)
    assert not denied.prime_mcp("甲醇现货价格")


@pytest.mark.parametrize("available,fails,expected", [(True, False, [MCP]), (False, False, ["web_search"]), (True, True, [MCP, "web_search"])])
def test_fast_first_request_mcp_or_minimal_web_fallback(tmp_path, available, fails, expected):
    class SelectionProbe(ProviderClient):
        def __init__(self):
            self.requests = []
        def capabilities(self, model):
            return ModelCapabilities()
        def complete(self, **kwargs):
            self.requests.append(kwargs)
            names = {s["function"]["name"] for s in kwargs["tools"] or []}
            if len(self.requests) == 1:
                name = MCP if MCP in names else "web_search"
                args = {"product": "甲醇", "limit": 1} if name == MCP else {"query": "甲醇 现货 最新 价格 区域 日期"}
                return AssistantTurn(tool_calls=[ToolCall("q", name, args)], finish_reason="tool_calls")
            if available and fails and len(self.requests) == 2:
                return AssistantTurn(tool_calls=[ToolCall("fallback", "web_search", {"query": "甲醇现货 最新 报价"})], finish_reason="tool_calls")
            return AssistantTurn(text="离线模拟报价 1000 元/吨，日期 2026-09-29。", finish_reason="stop")
    provider = SelectionProbe()
    e = build_engine(agent=get_agent("cowork"), workspace=tmp_path, provider=provider)
    e.research_depth = "fast"
    e.compaction_settings = lambda: {"enabled": False}
    for spec in registry()._tools.values():
        e.registry.register(spec.func, schema=spec.schema)
    executed = []
    if available:
        def spot(product, limit):
            executed.append(MCP)
            assert (product, limit) == ("甲醇", 1)
            return {"error": "暂不可用"} if fails else {"price": 1000, "source": "离线模拟"}
        add_mcp(e.registry, spot)
    def web_search(query: str):
        executed.append("web_search")
        return {"results": [{"content": "模拟最新价格 1000 元/吨", "url": "https://example.test/price"}]}
    e.registry.register(web_search)
    events = _collect(e, "查甲醇现货现在什么价，直接告诉我")
    assert executed == expected
    assert events[-1].data["status"] == "completed"
    prompt = next(m["content"] for m in provider.requests[0]["messages"] if m["role"] == "system")
    assert _LONG_TASK_GUIDANCE not in prompt
    assert "必须先用 todo_write" not in prompt
    assert "普通问题直接用简洁自然语言回答" in prompt
    assert "用户本轮明确要求文件/操作时照办并验证" in prompt
    assert ("本轮已提供可直接调用的 MCP 参数定义" if available else "当前没有已注册且符合本轮策略的 MCP 工具") in prompt
    # Canonical history and deep mode retain the original role, including its rules.
    assert _LONG_TASK_GUIDANCE in e.messages[0]["content"]


@pytest.mark.parametrize("late", [False, True])
def test_length_automatically_delivers_short_answer_without_repeating_tools(tmp_path, late):
    turns = ([call(i) for i in range(5)] if late else [call(0)]) + [
        AssistantTurn(text="未完成的报告正文", reasoning="长思考", finish_reason="length"),
        AssistantTurn(text="已核验的简短结果与来源。", finish_reason="stop"),
    ]
    e, executed = engine(tmp_path, turns)
    e.task_budget = TaskBudgetStore(tmp_path / "budget.db").create("s", research_depth="fast")
    requests = []
    complete = e.provider.complete
    def probe(**kwargs):
        requests.append(kwargs)
        return complete(**kwargs)
    e.provider.complete = probe
    events = _collect(e, "查当前价格")
    assert events[-1].data["status"] == "completed"
    assert executed == (list(range(5)) if late else [0])
    assert requests[-1]["tools"] is None
    assert "未完成的报告正文" not in str(requests[-1]["messages"])
    assert not any(ev.data.get("status") in {"truncated", "budget_paused"} for ev in events)
    assert e.task_budget.snapshot()["used"] == (7 if late else 3)


def test_recovery_is_bounded_and_cannot_claim_success(tmp_path):
    e, _ = engine(tmp_path, [AssistantTurn(text="仍不完整", finish_reason="length") for _ in range(2)])
    e.research_depth = "fast"
    events = _collect(e, "回答")
    assert events[-1].type == EventType.ERROR
    assert events[-1].data["error_type"] == "FastAnswerIncomplete"
    assert e.provider.calls == 2
    assert "手动" not in events[-1].data["error"]


def test_split_dsml_is_hidden_and_recovered_on_final_round(tmp_path):
    class ProtocolProvider(ProviderClient):
        calls = 0
        def capabilities(self, model):
            return ModelCapabilities()
        def complete(self, **kwargs):
            raise AssertionError("stream expected")
        def stream(self, **kwargs):
            self.calls += 1
            text = "资料已取得。<｜｜DSML｜｜ calls><invoke name=write_file>秘密脚本" if self.calls == 1 else "甲醇现货的模拟报价为 1000 元/吨。"
            for char in text:
                yield StreamChunk(text_delta=char)
            yield StreamChunk(turn=AssistantTurn(text=text, finish_reason="stop"))
    e, executed = engine(tmp_path, [])
    e.provider = ProtocolProvider()
    e.task_budget = TaskBudgetStore(tmp_path / "budget.db").create("s", research_depth="fast")
    for _ in range(5):
        e.task_budget.settle(e.task_budget.acquire(), success=True)
    events = _collect(e, "价格")
    visible = "".join(ev.data.get("text", "") for ev in events if ev.type in {EventType.ASSISTANT_DELTA, EventType.ASSISTANT_MESSAGE})
    assert "DSML" not in visible and "秘密脚本" not in visible
    assert "1000" in visible and not executed
    assert events[-1].data["status"] == "completed"


def test_web_call_limit_is_atomic_and_respects_saved_counts():
    budget, runtime = FastWebBudget(), {}
    with ThreadPoolExecutor(8) as pool:
        assert sum(pool.map(lambda _: budget.acquire(runtime, "web_search"), range(20))) == 2
    assert runtime["fast_synthesize"]
    assert not FastWebBudget().acquire(runtime, "web_search")
    assert budget.acquire(runtime, MCP)


def test_fast_web_attempts_stop_and_synthesize_without_extra_model_rounds(tmp_path):
    calls = []
    def web_search(query: str):
        calls.append(query)
        return {"result": "已核验的资料"}
    e, _ = engine(tmp_path, [AssistantTurn(tool_calls=[ToolCall(str(i), "web_search", {"query": str(i)}) for i in range(4)]),
                           AssistantTurn(text="已有证据的答案。", finish_reason="stop")])
    e.registry.register(web_search)
    e.research_depth = "fast"
    assert _collect(e, "联网查资料")[-1].data["status"] == "completed"
    assert len(calls) == 2 and e.provider.calls == 2


def test_old_fast_budget_gets_one_recovery_slot_once(tmp_path):
    store = TaskBudgetStore(tmp_path / "budget.db")
    handle = store.create("s", size=6, reserve=1)
    data = store._read(handle.group)
    data["research_depth"] = "fast"
    data["used"] = 6
    store._save(handle.group, data)
    for _ in range(2):
        restored = store.bind(handle.group, "s", "s", parent=True)
        assert restored.snapshot()["remaining"] == 1
        assert restored.snapshot()["used"] == 6
