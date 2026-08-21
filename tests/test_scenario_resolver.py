from __future__ import annotations

from coworker.capabilities import CapabilityResolver
from coworker.scenarios import ScenarioResolver
from coworker.tools.registry import ToolDescriptor


def _tools(*names: str) -> tuple[ToolDescriptor, ...]:
    out = []
    for name in names:
        if name.startswith("mcp__"):
            out.append(ToolDescriptor(name=name, category="mcp", capabilities=("chem-data-hub",)))
        else:
            out.append(ToolDescriptor(name=name))
    return tuple(out)


def test_explicit_scenario_is_authoritative_and_invalid_is_not_silent() -> None:
    resolver = ScenarioResolver()
    explicit = resolver.resolve("hello", explicit_scenario_id="chemical_identity")
    invalid = resolver.resolve("hello", explicit_scenario_id="does-not-exist")
    assert explicit.status == "matched"
    assert explicit.source == "explicit"
    assert explicit.confidence == 1.0
    assert invalid.status == "invalid"


def test_five_core_routes_and_market_ambiguity() -> None:
    tools = _tools(
        "mcp__chem-data-hub__get_price_trend",
        "lookup_cn_futures_quote",
        "lookup_cn_futures_ohlc",
        "lookup_chemical_identity",
        "lookup_legal_entity",
        "web_search",
        "web_fetch",
        "ask_user",
    )
    resolver = ScenarioResolver()
    assert resolver.resolve("甲醇期货现在多少钱", tools=tools).scenario_id == "cn_futures_market"
    assert resolver.resolve("甲醇现货多少钱", tools=tools).scenario_id == "chemical_spot_price"
    ambiguous = resolver.resolve("甲醇最近走势", tools=tools)
    assert ambiguous.status == "ambiguous"
    assert {item.scenario_id for item in ambiguous.candidates} == {
        "chemical_spot_price",
        "cn_futures_market",
    }
    assert resolver.resolve("查询 CAS 67-56-1", tools=tools).scenario_id == "chemical_identity"
    research = resolver.resolve("帮我深度研究万华化学未来半年 MDI", tools=tools)
    assert research.scenario_id == "chemical_company_research"


def test_deep_research_outranks_cn_futures_quote_scenario() -> None:
    tools = _tools(
        "mcp__chem-data-hub__get_price_trend",
        "lookup_cn_futures_quote",
        "lookup_cn_futures_ohlc",
        "web_search",
        "web_fetch",
        "ask_user",
    )
    resolver = ScenarioResolver()
    # Pure quote stays on the D-166 futures adapter (no Subagent).
    assert resolver.resolve("上海原油期货", tools=tools).scenario_id == "cn_futures_market"
    assert resolver.resolve("甲醇期货现在多少钱", tools=tools).scenario_id == "cn_futures_market"
    # Research wording outranks the quote scenario so allow_subagent can apply.
    deep = resolver.resolve("上海原油期货深度研究", tools=tools)
    assert deep.status == "matched"
    assert deep.scenario_id == "chemical_market_research"
    weekly = resolver.resolve("写一份上海原油期货周报", tools=tools)
    assert weekly.scenario_id == "chemical_market_research"
    # D-184: 产业链/上下游套利研究 outranks dual-scope quote adapters.
    for query in (
        "研究沥青期货产业链上下游套利怎么做",
        "研究甲醇期货产业链上下游套利怎么做",
    ):
        arb = resolver.resolve(query, tools=tools)
        assert arb.status == "matched", query
        assert arb.scenario_id == "chemical_market_research", query


def test_capability_resolution_uses_exact_market_provider_without_web_fallback() -> None:
    tools = _tools(
        "mcp__chem-data-hub__get_price_trend",
        "lookup_cn_futures_quote",
        "lookup_cn_futures_ohlc",
        "web_search",
        "web_fetch",
        "ask_user",
    )
    scenarios = ScenarioResolver()
    capabilities = CapabilityResolver()

    futures = capabilities.resolve(
        scenarios.resolve("甲醇期货现在多少钱", tools=tools),
        text="甲醇期货现在多少钱",
        tools=tools,
    )
    assert futures.required_ready is True
    assert futures.selected_tool_names == ("lookup_cn_futures_quote",)

    spot = capabilities.resolve(
        scenarios.resolve("甲醇现货多少钱", tools=tools),
        text="甲醇现货多少钱",
        tools=tools,
    )
    assert spot.selected_tool_names == ("mcp__chem-data-hub__get_price_trend",)

    ambiguous = capabilities.resolve(
        scenarios.resolve("甲醇最近走势", tools=tools),
        text="甲醇最近走势",
        tools=tools,
    )
    assert ambiguous.selected_tool_names == ("ask_user",)


def test_required_provider_down_reports_unavailable_without_substitution() -> None:
    tools = _tools("web_search", "web_fetch")
    scenario = ScenarioResolver().resolve("甲醇现货多少钱", tools=tools)
    plan = CapabilityResolver().resolve(scenario, text="甲醇现货多少钱", tools=tools)
    assert plan.required_ready is False
    assert plan.selected_tool_names == ()
    assert plan.resolutions[0].status == "unavailable"
    assert plan.fallback == ("report_unavailable",)


def test_configured_but_disconnected_mcp_is_distinct_from_unavailable() -> None:
    tools = _tools("web_search")
    scenario = ScenarioResolver().resolve("甲醇现货多少钱", tools=tools)
    plan = CapabilityResolver().resolve(
        scenario,
        text="甲醇现货多少钱",
        tools=tools,
        configured_tool_names=("mcp__chem-data-hub",),
    )
    assert plan.required_ready is False
    assert plan.resolutions[0].status == "configured"
    assert plan.resolutions[0].provider_id == "chem-data-hub"
