from __future__ import annotations

from coworker.market_intent import (
    MarketIntentKind,
    MarketScope,
    resolve_market_tools,
    render_market_turn_context,
)
from coworker.tools.registry import ToolDescriptor


SPOT = "mcp__chem-data-hub__get_price_trend"
SPOT_UNDERSCORE = "mcp__chem_data_hub__get_price_trend"


def _tools(*, spot_name: str = SPOT, include_spot: bool = True):
    descriptors = [
        ToolDescriptor("ask_user"),
        ToolDescriptor("web_search"),
        ToolDescriptor("web_fetch"),
        ToolDescriptor("lookup_cn_futures_quote"),
        ToolDescriptor("lookup_cn_futures_ohlc"),
        ToolDescriptor("lookup_cn_futures_minute"),
        ToolDescriptor("lookup_cn_futures_l1"),
        ToolDescriptor("calculate_cn_futures_margin"),
        ToolDescriptor("lookup_yahoo_ohlc"),
        ToolDescriptor("mcp__unrelated__get_price_trend", "mcp", ("unrelated",)),
    ]
    if include_spot:
        descriptors.append(
            ToolDescriptor(spot_name, "mcp", (spot_name.split("__")[1],))
        )
    return descriptors


def test_explicit_crude_and_methanol_spot_only_select_chem_data_hub():
    for query in ("查原油的现货价格", "查甲醇的现货价格"):
        selection = resolve_market_tools(query, _tools())
        assert selection.intent.kind is MarketIntentKind.CHEMICAL_SPOT
        assert selection.intent.scope is MarketScope.CHEMICAL_SPOT
        assert selection.allowed_tool_names == (SPOT,)
        assert "web_search" not in selection.allowed_tool_names
        assert "lookup_cn_futures_ohlc" not in selection.allowed_tool_names
        assert "lookup_yahoo_ohlc" not in selection.allowed_tool_names


def test_spot_mcp_server_name_normalizes_hyphen_and_underscore():
    selection = resolve_market_tools(
        "查甲醇现货价格", _tools(spot_name=SPOT_UNDERSCORE)
    )
    assert selection.allowed_tool_names == (SPOT_UNDERSCORE,)


def test_dynamic_mcp_requires_matching_server_or_capability_metadata():
    selection = resolve_market_tools("查甲醇现货价格", _tools(include_spot=False))
    assert selection.intent.kind is MarketIntentKind.CHEMICAL_SPOT
    assert selection.allowed_tool_names == ()
    assert selection.capability_available is False
    context = render_market_turn_context(selection)
    assert "not available; report unavailable in Chinese" in context
    assert "Do not call CN futures, Yahoo, or Web" in context


def test_explicit_cn_futures_and_contract_code_use_minimal_cn_pack():
    for query in ("查甲醇期货价格", "MA2509 价格"):
        selection = resolve_market_tools(query, _tools())
        assert selection.intent.kind is MarketIntentKind.CN_FUTURES
        assert selection.allowed_tool_names == (
            "lookup_cn_futures_quote",
            "lookup_cn_futures_ohlc",
        )
        assert SPOT not in selection.allowed_tool_names
        assert "lookup_cn_futures_minute" not in selection.allowed_tool_names
        assert "lookup_yahoo_ohlc" not in selection.allowed_tool_names


def test_cn_futures_extra_tools_require_corresponding_intent():
    selection = resolve_market_tools(
        "查 MA2509 分钟行情、盘口和保证金", _tools()
    )
    assert set(selection.allowed_tool_names or ()) == {
        "lookup_cn_futures_quote",
        "lookup_cn_futures_ohlc",
        "lookup_cn_futures_minute",
        "lookup_cn_futures_l1",
        "calculate_cn_futures_margin",
    }


def test_wti_and_brent_futures_only_use_yahoo():
    for query in ("查 WTI 原油期货", "BZ=F 最近一年走势"):
        selection = resolve_market_tools(query, _tools())
        assert selection.intent.kind is MarketIntentKind.GLOBAL_FUTURES
        assert selection.allowed_tool_names == ("lookup_yahoo_ohlc",)
    assert "CL=F" in render_market_turn_context(
        resolve_market_tools("查 WTI 原油期货", _tools())
    )


def test_generic_futures_concept_is_not_misclassified_as_a_price_lookup():
    selection = resolve_market_tools("深度研究期货制度的基本概念", _tools())
    assert selection.intent.kind is MarketIntentKind.NON_MARKET


def test_bare_methanol_requires_clarification_and_guards_market_calls():
    selection = resolve_market_tools("查甲醇价格", _tools())
    assert selection.intent.kind is MarketIntentKind.CLARIFY
    assert [option.label for option in selection.clarification_options] == [
        "化工现货",
        "国内期货",
    ]
    assert "ask_user" in (selection.allowed_tool_names or ())
    assert selection.guard_tool("lookup_cn_futures_ohlc", None) == (
        False,
        "行情市场口径尚未确认；请先询问用户，再查询价格",
    )
    assert selection.scope_from_answer("化工现货") is MarketScope.CHEMICAL_SPOT
    assert selection.scope_from_answer({"行情口径": "国内期货"}) is MarketScope.CN_FUTURES
    assert selection.guard_tool(
        SPOT, MarketScope.CHEMICAL_SPOT
    ) == (True, "market scope matched")
    assert selection.guard_tool(
        "lookup_cn_futures_ohlc", MarketScope.CHEMICAL_SPOT
    )[0] is False
    assert selection.guard_tool(
        "mcp__unrelated__get_price_trend", MarketScope.CHEMICAL_SPOT
    )[0] is False


def test_bare_crude_offers_four_market_scopes():
    selection = resolve_market_tools("查原油价格", _tools())
    assert [option.label for option in selection.clarification_options] == [
        "原油现货",
        "上海原油期货",
        "WTI期货",
        "布伦特期货",
    ]


def test_web_is_supplemental_only_when_drivers_are_explicitly_requested():
    plain = resolve_market_tools("查甲醇现货价格", _tools())
    drivers = resolve_market_tools("查甲醇现货价格并分析驱动因素", _tools())
    assert plain.allowed_tool_names == (SPOT,)
    assert drivers.allowed_tool_names == (SPOT, "web_search", "web_fetch")
    assert drivers.web_is_supplemental is True


def test_market_prompt_policy_preserves_explicit_spot_and_no_substitute_rule():
    selection = resolve_market_tools("查甲醇现货价格", _tools())
    context = render_market_turn_context(selection)
    assert "CHEMICAL SPOT" in context
    assert "get_price_trend" in context
    assert "Do not call CN futures, Yahoo, or Web to substitute" in context

    from coworker.agent import _INLINE_CHART_GUIDANCE

    assert "甲醇期货" in _INLINE_CHART_GUIDANCE
    assert "甲醇, 液化气, MA/PG" not in _INLINE_CHART_GUIDANCE
