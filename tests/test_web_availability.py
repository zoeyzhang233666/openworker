"""Web is a basic capability, even with hundreds of MCP tools and no skills."""

import asyncio

import pytest

from coworker.agent import build_engine
from coworker.agents import get_agent
from coworker.context_budget import estimate
from coworker.events import EventType
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient, ToolCall
from coworker.tool_policy import TurnToolPolicy
from coworker.web import make_web_search_tool
from tests.test_tool_discovery import registry
from tests.test_web_search import FakeProvider


class WebTask(ProviderClient):
    def __init__(self):
        self.requests = []

    def capabilities(self, model):
        return ModelCapabilities()

    def complete(self, **kwargs):
        self.requests.append(kwargs)
        if len(self.requests) == 1:
            return AssistantTurn(tool_calls=[ToolCall("search", "web_search", {"query": "公开资料"})])
        return AssistantTurn(text="已核对公开来源。", finish_reason="stop")


@pytest.mark.parametrize("agent", ["cowork", "chat", "code"])
def test_first_request_can_search_without_a_skill_in_large_registry(tmp_path, agent):
    model, search = WebTask(), FakeProvider()
    engine = build_engine(agent=get_agent(agent), workspace=tmp_path, provider=model)
    for name in registry().names():
        def tool():
            return "ok"
        tool.__name__ = name
        engine.registry.register(tool)
    engine.registry.register(make_web_search_tool(provider=search))

    async def run():
        return [event async for event in engine.run("MCP 数据不全，请联网核对公开资料")]

    events = asyncio.run(run())
    names = {s["function"]["name"] for s in model.requests[0]["tools"]}
    assert {"web_search", "web_fetch"} <= names
    assert not any(name.startswith("mcp_rare") for name in names)
    assert estimate(model.requests[0]["tools"]) <= 12000
    assert search.calls == [("公开资料", 5)]
    executed = [ev.data["name"] for ev in events if ev.type == EventType.TOOL_FINISHED]
    assert executed == ["web_search"]
    assert events[-1].data["status"] == "completed"


@pytest.mark.parametrize("policy,blocked", [
    (TurnToolPolicy(no_external_network=True), {"web_search", "web_fetch"}),
    (TurnToolPolicy(no_search=True), {"web_search"}),
    (TurnToolPolicy(no_tools=True), {"web_search", "web_fetch"}),
])
def test_basic_web_tools_still_respect_user_policy(tmp_path, policy, blocked):
    engine = build_engine(agent=get_agent("cowork"), workspace=tmp_path, provider=WebTask())
    from coworker.tool_discovery import ToolDiscovery
    discovery = ToolDiscovery(engine.registry, lambda: policy, lambda: 12000)
    assert not blocked & {s["function"]["name"] for s in discovery.schemas()}
    assert not blocked & {r["name"] for r in discovery.search("web")["tools"]}
    assert set(discovery.load(list(blocked))["rejected"]) == blocked


def test_generic_prompt_does_not_forbid_web_when_mcp_is_incomplete(tmp_path):
    engine = build_engine(agent=get_agent("cowork"), workspace=tmp_path, provider=WebTask())
    prompt = engine.messages[0]["content"]
    assert "不依赖 Skill" in prompt
    assert "禁止用网页" not in prompt
    assert "禁止用 Yahoo 或 web_search 补同一行情" not in prompt
