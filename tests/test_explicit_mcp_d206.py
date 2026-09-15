from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from coworker.channels.delivery import CHANNEL_DENIED_TOOLS
from coworker.config import Config
from coworker.execution_profile import RequestRoute
from coworker.market_intent import resolve_market_tools
from coworker.mcp.config import MCPServerDef
from coworker.mcp_intent import mentions_mcp, referenced_mcp_tools
from coworker.mcp.tools import _mcp_timeout, build_callables
from coworker.tool_projection import project_provider_visible_schemas
from coworker.tools.registry import ToolDescriptor, ToolRegistry
from coworker.turn_planner import TurnPlanner

QUESTION = '搜索近期有关于化工方面的招投标、增产、停产、价格波动等的热点新闻。使用chem-biz-scope这个mcp针对里面的关键内容进行提取'
BIZ = ('mcp__chem-biz-scope__describe_table', 'mcp__chem-biz-scope__query_scope')
TOOLS = (*BIZ, 'mcp__chem-data-hub__get_price_trend', 'web_search', 'web_fetch', 'ask_user', *sorted(CHANNEL_DENIED_TOOLS))


def planner(names=TOOLS):
    return TurnPlanner(config=Config(), available_tool_names=lambda: names)


@pytest.mark.parametrize('text', ['这个mcp针对内容提取', '测试MCP能否使用', 'mcp工具', '用 MCP 查询'])
def test_chinese_adjacent_mcp(text):
    assert mentions_mcp(text)


@pytest.mark.parametrize('text', ['amcp', 'mcpx', 'mcp_tools'])
def test_identifier_substrings_are_not_mcp(text):
    assert not mentions_mcp(text)


@pytest.mark.parametrize('text', [QUESTION, '测试chem-biz-scope这个mcp能否正常使用', '用chem-biz-scope查企业', '用MCP查甲醇现货价格'])
def test_explicit_desktop_request_keeps_live_tools(text):
    plan = planner().plan(text)
    assert plan.decision.route is RequestRoute.AGENT
    assert plan.execution_profile.allowed_tool_names is None
    assert not plan.scenario_projection_applied
    assert set(BIZ) <= set(plan.preview().selected_tool_names)


def test_same_planner_test_then_news_preserves_tools():
    p = planner()
    for text in ['测试chem-biz-scope这个mcp能否正常使用', QUESTION]:
        assert p.plan(text).execution_profile.allowed_tool_names is None
    # The explicit MCP guard does not leak into later normal quote turns.
    assert p.plan('柠檬酸价格走势图').decision.route is RequestRoute.VERIFIED


def test_server_reference_is_exact_namespace():
    assert referenced_mcp_tools('用chem-biz-scope查询', TOOLS) == BIZ
    assert referenced_mcp_tools('用chem-biz-scope-extra查询', TOOLS) == ()


def test_configured_but_unconnected_server_does_not_invent_tools():
    p = TurnPlanner(config=Config(), available_tool_names=lambda: ('web_search',), configured_tool_names=lambda: ('mcp__chem-biz-scope',))
    plan = p.plan('用chem-biz-scope提取新闻')
    assert plan.execution_profile.allowed_tool_names is None
    assert tuple(p._available_tool_names()) == ('web_search',)


def test_explicit_channel_request_keeps_mcp_without_privileged_tools():
    plan = planner().plan(QUESTION, source={'connector': 'wecom', 'target': 'wecom:default:user', 'kind': 'dm'})
    allowed = set(plan.execution_profile.allowed_tool_names)
    assert set(BIZ) <= allowed
    assert not (CHANNEL_DENIED_TOOLS & allowed)
    assert plan.execution_profile.max_iterations <= 4


@pytest.mark.parametrize('suffix', ['，不要使用任何工具', '，不要联网'])
def test_explicit_mcp_still_obeys_tool_policy(suffix):
    plan = planner().plan(QUESTION + suffix)
    registry = ToolRegistry()
    for name in BIZ:
        def fn():
            return 'ok'
        fn.__name__ = name
        registry.register(fn)
    schemas = project_provider_visible_schemas(registry, tool_projection_enabled=True, profile=plan.execution_profile, tool_policy=plan.tool_policy)
    assert not schemas


def test_news_roundup_is_not_spot_quote():
    selection = resolve_market_tools(QUESTION, (ToolDescriptor(name=n) for n in TOOLS))
    assert not selection.intent.is_market


@pytest.mark.parametrize('text', ['柠檬酸价格走势图', '甲醇价格波动和停产新闻', '查询柠檬酸现货价格与增产停产新闻'])
def test_actual_market_requests_keep_market_guidance(text):
    selection = resolve_market_tools(text, (ToolDescriptor(name=n) for n in TOOLS))
    assert selection.intent.is_market


def test_slow_query_deadlines_and_override(monkeypatch):
    monkeypatch.delenv('CHEMCLAW_MCP_TOOL_TIMEOUT', raising=False)
    monkeypatch.delenv('COWORKER_MCP_TOOL_TIMEOUT', raising=False)
    for name in ('query_scope', 'count_scope', 'progress_snapshot'):
        assert _mcp_timeout(name) == 120
    assert _mcp_timeout('describe_table') == 30
    monkeypatch.setenv('CHEMCLAW_MCP_TOOL_TIMEOUT', '45')
    assert _mcp_timeout('query_scope') == 45


def wrapped(call, timeout):
    return build_callables(MCPServerDef(name='example', transport='http'), [SimpleNamespace(name='query_scope', inputSchema={}, description='read query')], call, asyncio.get_running_loop(), timeout=timeout)[0]


@pytest.mark.asyncio
async def test_client_timeout_is_descriptive_and_cancels_pending_call(monkeypatch):
    monkeypatch.delenv('CHEMCLAW_MCP_TOOL_TIMEOUT', raising=False)
    monkeypatch.delenv('COWORKER_MCP_TOOL_TIMEOUT', raising=False)
    cancelled = asyncio.Event()
    async def call(tool, args):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    result = await asyncio.to_thread(wrapped(call, .02))
    await asyncio.wait_for(cancelled.wait(), 1)
    assert result['timeout_source'] == 'client_wait'
    assert result['server'] == 'example'
    assert result['tool'] == 'query_scope'
    assert '0.02' in result['error']
    assert '不表示接口未注册' in result['error']


@pytest.mark.asyncio
async def test_transport_timeout_is_not_reported_as_client_deadline():
    async def call(tool, args):
        raise TimeoutError('upstream details')
    result = await asyncio.to_thread(wrapped(call, 1))
    assert result['timeout_source'] == 'transport_or_server'
    assert 'upstream details' not in result['error']


@pytest.mark.asyncio
async def test_success_and_approval_metadata_are_preserved():
    async def call(tool, args):
        return {'rows': [1]}
    fn = wrapped(call, 1)
    assert fn.__aisuite_tool_metadata__.requires_approval
    assert await asyncio.to_thread(fn) == {'rows': [1]}


def test_real_engine_outbound_schemas_keep_mcp_across_turns(tmp_path, monkeypatch):
    from coworker.agent import build_engine
    from coworker.agents import cowork_agent
    from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient

    class Provider(ProviderClient):
        def __init__(self):
            self.calls = []

        def capabilities(self, model):
            return ModelCapabilities(tools=True)

        def complete(self, **kwargs):
            self.calls.append(kwargs)
            return AssistantTurn(text='测试完成', finish_reason='stop')

    monkeypatch.setattr('coworker.agent.load_config', lambda *a, **k: Config())
    monkeypatch.setenv('COWORKER_STATE_DIR', str(tmp_path / 'state'))
    def query_scope():
        return {'rows': []}
    query_scope.__name__ = BIZ[1]
    provider = Provider()
    engine = build_engine(agent=cowork_agent(), workspace=tmp_path, provider=provider,
                          skill_dirs=[tmp_path / 'skills'], extra_tools=[query_scope])

    async def run():
        for text in ['测试chem-biz-scope这个mcp能否正常使用', QUESTION]:
            _ = [event async for event in engine.run(text)]
    asyncio.run(run())
    assert len(provider.calls) == 2
    for call in provider.calls:
        names = {schema['function']['name'] for schema in call['tools']}
        assert BIZ[1] in names
        assert 'web_search' in names
        assert '不把未测试计入成功' in call['messages'][0]['content']
