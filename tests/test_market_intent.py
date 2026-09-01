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
WEB = ("web_search", "web_fetch")


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


def _assert_chem_web_allowed(selection) -> None:
    allowed = set(selection.allowed_tool_names or ())
    assert "web_search" in allowed
    assert "web_fetch" in allowed
    assert selection.web_is_supplemental is True
    # Web is supplemental (not a primary scope tool) — market guard does not deny it.
    assert selection.guard_tool("web_search", selection.intent.scope) is None


def test_explicit_crude_and_methanol_spot_only_select_chem_data_hub():
    for query in ("查原油的现货价格", "查甲醇的现货价格"):
        selection = resolve_market_tools(query, _tools())
        assert selection.intent.kind is MarketIntentKind.CHEMICAL_SPOT
        assert selection.intent.scope is MarketScope.CHEMICAL_SPOT
        assert selection.allowed_tool_names == (SPOT, *WEB)
        assert "lookup_cn_futures_ohlc" not in selection.allowed_tool_names
        assert "lookup_yahoo_ohlc" not in selection.allowed_tool_names
        _assert_chem_web_allowed(selection)


def test_spot_mcp_server_name_normalizes_hyphen_and_underscore():
    selection = resolve_market_tools(
        "查甲醇现货价格", _tools(spot_name=SPOT_UNDERSCORE)
    )
    assert selection.allowed_tool_names == (SPOT_UNDERSCORE, *WEB)


def test_market_news_mcp_is_supplemental_not_price_scope_controlled():
    tools = _tools()
    tools.append(
        ToolDescriptor(
            "mcp__chem-data-hub__list_market_news_live",
            "mcp",
            ("chem_data_hub",),
        )
    )
    selection = resolve_market_tools("查询甲醇现货价格及相关新闻", tools)

    assert selection.intent.kind is MarketIntentKind.CHEMICAL_SPOT
    assert selection.guard_tool(
        "mcp__chem-data-hub__list_market_news_live", selection.intent.scope
    ) is None
    assert selection.guard_tool(SPOT, selection.intent.scope) == (
        True,
        "market scope matched",
    )


def test_legacy_scope_diagnostic_still_classifies_dynamic_price_mcp():
    tools = _tools()
    tools.append(ToolDescriptor("mcp__other-market__get_product_price", "mcp"))
    selection = resolve_market_tools("查询甲醇现货价格", tools)

    assert selection.guard_tool(
        "mcp__other-market__get_product_price", selection.intent.scope
    ) == (False, "该工具与用户选择的现货/期货市场口径不一致")


def test_dynamic_mcp_requires_matching_server_or_capability_metadata():
    selection = resolve_market_tools("查甲醇现货价格", _tools(include_spot=False))
    assert selection.intent.kind is MarketIntentKind.CHEMICAL_SPOT
    assert selection.allowed_tool_names == WEB
    assert selection.capability_available is False
    context = render_market_turn_context(selection)
    assert "当前不可用" in context
    assert "web_search" in context or "网页" in context
    assert "URL" in context


def test_explicit_cn_futures_and_contract_code_use_minimal_cn_pack():
    for query in ("查甲醇期货价格", "MA2509 价格"):
        selection = resolve_market_tools(query, _tools())
        assert selection.intent.kind is MarketIntentKind.CN_FUTURES
        assert selection.allowed_tool_names == (
            "lookup_cn_futures_quote",
            "lookup_cn_futures_ohlc",
            *WEB,
        )
        assert SPOT not in selection.allowed_tool_names
        assert "lookup_cn_futures_minute" not in selection.allowed_tool_names
        assert "lookup_yahoo_ohlc" not in selection.allowed_tool_names
        _assert_chem_web_allowed(selection)


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
        *WEB,
    }


def test_wti_and_brent_futures_only_use_yahoo():
    for query in ("查 WTI 原油期货", "BZ=F 最近一年走势"):
        selection = resolve_market_tools(query, _tools())
        assert selection.intent.kind is MarketIntentKind.GLOBAL_FUTURES
        assert selection.allowed_tool_names == ("lookup_yahoo_ohlc",)
        assert selection.web_is_supplemental is False
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
    assert set(WEB) <= set(selection.allowed_tool_names or ())
    assert selection.web_is_supplemental is True
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


def test_chem_web_always_supplemental_not_only_for_drivers():
    plain = resolve_market_tools("查甲醇现货价格", _tools())
    drivers = resolve_market_tools("查甲醇现货价格并分析驱动因素", _tools())
    assert plain.allowed_tool_names == (SPOT, *WEB)
    assert drivers.allowed_tool_names == (SPOT, *WEB)
    assert plain.web_is_supplemental is True
    assert drivers.web_is_supplemental is True


def test_market_prompt_policy_ordered_web_fallback_for_spot():
    selection = resolve_market_tools("查甲醇现货价格", _tools())
    context = render_market_turn_context(selection)
    assert "化工现货" in context
    assert "get_price_trend" in context
    assert "禁止用国内期货或 Yahoo 替代现货价" in context
    assert "最后手段" in context
    assert "URL" in context

    from coworker.agent import _INLINE_CHART_GUIDANCE

    assert "甲醇期货" in _INLINE_CHART_GUIDANCE
    assert "甲醇, 液化气, MA/PG" not in _INLINE_CHART_GUIDANCE


def test_basis_and_arb_dual_scope_allows_spot_cn_futures_and_web():
    for query in (
        "甲醇期货产业链上下游套利",
        "结合现货看甲醇期货基差",
        "对比甲醇现货和期货价格",
        "研究甲醇期货产业链上下游套利怎么做",
    ):
        selection = resolve_market_tools(query, _tools())
        assert selection.intent.kind is MarketIntentKind.CN_SPOT_FUTURES, query
        assert selection.intent.scope is None
        allowed = set(selection.allowed_tool_names or ())
        assert SPOT in allowed, query
        assert "lookup_cn_futures_quote" in allowed, query
        assert "lookup_cn_futures_ohlc" in allowed, query
        assert "lookup_yahoo_ohlc" not in allowed, query
        assert "web_search" in allowed, query
        assert "web_fetch" in allowed, query
        assert selection.web_is_supplemental is True, query
        assert selection.guard_tool(SPOT, None) == (True, "market scope matched")
        assert selection.guard_tool("lookup_cn_futures_ohlc", None) == (
            True,
            "market scope matched",
        )
        assert selection.guard_tool("lookup_yahoo_ohlc", None)[0] is False
        # Web is not a primary scope tool — not blocked by market guard.
        assert selection.guard_tool("web_search", None) is None
    context = render_market_turn_context(
        resolve_market_tools("结合现货看甲醇期货基差", _tools())
    )
    assert "现货" in context and "期货" in context
    assert "禁止用期货代替现货" in context
    assert "web_search" in context or "网页" in context
    assert "URL" in context


def test_regional_spot_arb_without_futures_stays_spot_only():
    selection = resolve_market_tools("对比甲醇华东与华北现货套利窗口", _tools())
    assert selection.intent.kind is MarketIntentKind.CHEMICAL_SPOT
    assert selection.allowed_tool_names == (SPOT, *WEB)
    assert "lookup_cn_futures_ohlc" not in (selection.allowed_tool_names or ())


def test_a_share_still_blocks_web_without_drivers():
    selection = resolve_market_tools("分析今天 A 股市场", _tools())
    assert selection.intent.kind is MarketIntentKind.LISTED_SECURITY
    assert "web_search" not in (selection.allowed_tool_names or ())
    assert selection.web_is_supplemental is False


def test_market_selection_snapshot_roundtrip_and_merge_inheritance():
    from coworker.market_intent import (
        merge_inherited_market_selection,
        restore_market_selection_from_metadata,
        snapshot_market_selection_metadata,
    )

    dual = resolve_market_tools("研究甲醇期货产业链上下游套利怎么做", _tools())
    assert dual.intent.kind is MarketIntentKind.CN_SPOT_FUTURES
    assert dual.web_is_supplemental is True
    meta = snapshot_market_selection_metadata(dual)
    restored = restore_market_selection_from_metadata(meta)
    assert restored is not None
    assert restored.intent.kind is MarketIntentKind.CN_SPOT_FUTURES
    assert restored.web_is_supplemental is True
    assert restored.guard_tool(SPOT, None) == (True, "market scope matched")
    assert restored.guard_tool("lookup_cn_futures_ohlc", None) == (
        True,
        "market scope matched",
    )

    clarify = resolve_market_tools("查甲醇价格", _tools())
    assert clarify.needs_clarification
    assert merge_inherited_market_selection(dual, clarify) is dual

    futures_only = resolve_market_tools("甲醇期货现在多少钱", _tools())
    assert futures_only.intent.kind is MarketIntentKind.CN_FUTURES
    narrowed = merge_inherited_market_selection(dual, futures_only)
    assert narrowed is futures_only

    spot_only = resolve_market_tools("查甲醇现货价格", _tools())
    # Spot-only tools are ⊆ dual allowlist → child may narrow.
    assert merge_inherited_market_selection(dual, spot_only) is spot_only

    # Widening from futures-only parent to dual planned must keep parent.
    assert merge_inherited_market_selection(futures_only, dual) is futures_only
