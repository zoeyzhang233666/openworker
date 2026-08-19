"""Deterministic market-scope resolution and Tool selection (D-166).

The module deliberately separates *what is being priced* from *which market the
user means*.  Product aliases never override an explicit spot/futures qualifier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .cn_market.symbols import CNFuturesSymbol, find_futures_mentions
from .tools.registry import ToolDescriptor


class MarketIntentKind(str, Enum):
    NON_MARKET = "non_market"
    CHEMICAL_SPOT = "chemical_spot"
    CN_FUTURES = "cn_futures"
    GLOBAL_FUTURES = "global_futures"
    LISTED_SECURITY = "listed_security"
    CLARIFY = "clarify"


class MarketScope(str, Enum):
    CHEMICAL_SPOT = "chemical_spot"
    CN_FUTURES = "cn_futures"
    WTI_FUTURES = "wti_futures"
    BRENT_FUTURES = "brent_futures"
    GLOBAL_FUTURES = "global_futures"
    CN_STOCK = "cn_stock"
    CN_OPTION = "cn_option"


@dataclass(frozen=True)
class MarketIntent:
    kind: MarketIntentKind
    product: str | None = None
    scope: MarketScope | None = None
    reason: str = ""

    @property
    def is_market(self) -> bool:
        return self.kind is not MarketIntentKind.NON_MARKET


@dataclass(frozen=True)
class MarketScopeTools:
    scope: MarketScope
    tool_names: tuple[str, ...]


@dataclass(frozen=True)
class MarketClarificationOption:
    label: str
    description: str
    scope: MarketScope


@dataclass(frozen=True)
class MarketToolSelection:
    intent: MarketIntent
    allowed_tool_names: tuple[str, ...] | None
    scope_tools: tuple[MarketScopeTools, ...] = ()
    blocked_tool_names: tuple[str, ...] = ()
    clarification_options: tuple[MarketClarificationOption, ...] = ()
    capability_available: bool = True
    web_is_supplemental: bool = False

    @classmethod
    def non_market(cls) -> "MarketToolSelection":
        return cls(
            intent=MarketIntent(MarketIntentKind.NON_MARKET),
            allowed_tool_names=None,
        )

    @property
    def needs_clarification(self) -> bool:
        return self.intent.kind is MarketIntentKind.CLARIFY

    def tools_for_scope(self, scope: MarketScope | None) -> tuple[str, ...]:
        if scope is None:
            return ()
        for item in self.scope_tools:
            if item.scope is scope:
                return item.tool_names
        return ()

    def scope_from_answer(self, answer: object) -> MarketScope | None:
        if isinstance(answer, dict):
            answer = next(iter(answer.values()), "")
        if isinstance(answer, (list, tuple)):
            answer = answer[0] if answer else ""
        text = str(answer or "").strip().lower()
        if not text:
            return None
        for option in self.clarification_options:
            if text == option.label.lower():
                return option.scope
        if "现货" in text or "spot" in text:
            return MarketScope.CHEMICAL_SPOT
        if "wti" in text:
            return MarketScope.WTI_FUTURES
        if "布伦特" in text or "brent" in text:
            return MarketScope.BRENT_FUTURES
        if "上海" in text and "原油" in text:
            return MarketScope.CN_FUTURES
        if "国内" in text and "期货" in text:
            return MarketScope.CN_FUTURES
        if text in {"期货", "futures", "future"}:
            scopes = {item.scope for item in self.scope_tools}
            if scopes == {MarketScope.CHEMICAL_SPOT, MarketScope.CN_FUTURES}:
                return MarketScope.CN_FUTURES
        return None

    def guard_tool(
        self, tool_name: str, resolved_scope: MarketScope | None
    ) -> tuple[bool, str] | None:
        """Return None when this selection does not govern the Tool."""

        controlled = set(self.blocked_tool_names)
        for item in self.scope_tools:
            controlled.update(item.tool_names)
        if _is_dynamic_market_mcp(tool_name):
            controlled.add(tool_name)
        if tool_name not in controlled:
            return None

        scope = resolved_scope or self.intent.scope
        if self.needs_clarification and scope is None:
            return False, "行情市场口径尚未确认；请先询问用户，再查询价格"
        allowed = set(self.tools_for_scope(scope))
        if tool_name in allowed:
            return True, "market scope matched"
        return False, "该工具与用户选择的现货/期货市场口径不一致"


_PRICE_RE = re.compile(
    r"(价格|报价|均价|价差|走势|行情|k线|蜡烛|ohlc|price|quote|trend|market)",
    re.I,
)
_SPOT_RE = re.compile(r"(现货|spot(?:\s+price)?|cash\s+price)", re.I)
_FUTURES_RE = re.compile(
    r"(期货|合约|主力|连续|交割|futures?|contract|continuous)", re.I
)
_DRIVER_RE = re.compile(
    r"(原因|驱动|新闻|事件|为什么|影响因素|news|driver|catalyst|why)", re.I
)
_CN_STOCK_RE = re.compile(
    r"(A\s*股|上证|深证|创业板|科创板|沪市|深市|北向|南向|龙虎榜|两融|"
    r"茅台|财务三张|三张表|年报|季报|A-?share|\b\d{6}(?:\.(?:SH|SZ|SS|BJ))?\b)",
    re.I,
)
_CN_OPTION_RE = re.compile(r"(期权|50ETF|300ETF|500ETF|科创50ETF|股指期权)", re.I)
_GLOBAL_RE = re.compile(
    r"(yahoo|美股|港股|恒生|nasdaq|nyse|\baapl\b|\btsla\b|黄金期货|\bgc=f\b)",
    re.I,
)
_WTI_RE = re.compile(r"(\bwti\b|\bcl=f\b|西德州|纽约原油)", re.I)
_BRENT_RE = re.compile(r"(\bbrent\b|\bbz=f\b|布伦特)", re.I)
_CLEAR_FINANCIAL_SPOT_RE = re.compile(
    r"(现货黄金|现货白银|\bxau\b|\bxag\b|比特币|\bbtc\b|外汇)", re.I
)

_CN_STOCK_TOOLS = (
    "lookup_cn_stock_quote",
    "lookup_cn_stock_ohlc",
    "lookup_cn_stock_minute",
    "lookup_cn_stock_financials",
    "lookup_cn_stock_feature",
)
_CN_FUTURES_BASE = ("lookup_cn_futures_quote", "lookup_cn_futures_ohlc")
_CN_FUTURES_EXTRA = (
    "lookup_cn_futures_minute",
    "lookup_cn_futures_l1",
    "calculate_cn_futures_margin",
)
_CN_OPTION_TOOLS = ("lookup_cn_option_market",)
_YAHOO_TOOLS = ("lookup_yahoo_ohlc",)
_WEB_TOOLS = ("web_search", "web_fetch")


def _unique_available(names: Iterable[str], available: set[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(name for name in names if name in available))


def _normalized_capability(value: str) -> str:
    return re.sub(r"[-.\s]+", "_", str(value or "").strip().lower())


def _mcp_parts(name: str) -> tuple[str, str] | None:
    if not name.startswith("mcp__") or "__" not in name[5:]:
        return None
    server, remote = name[5:].rsplit("__", 1)
    return server, remote


def _is_dynamic_market_mcp(name: str) -> bool:
    parts = _mcp_parts(name)
    return bool(
        parts
        and re.search(r"(price|quote|trend|ohlc|market)", parts[1], re.I)
    )


def _chemical_spot_tools(tools: tuple[ToolDescriptor, ...]) -> tuple[str, ...]:
    selected: list[str] = []
    for tool in tools:
        parts = _mcp_parts(tool.name)
        if parts is None or parts[1].lower() != "get_price_trend":
            continue
        server_ok = _normalized_capability(parts[0]) == "chem_data_hub"
        capability_ok = any(
            _normalized_capability(item) == "chem_data_hub"
            for item in tool.capabilities
        )
        if tool.category.lower() == "mcp" and (capability_ok or server_ok):
            selected.append(tool.name)
        elif not tool.category and server_ok:
            # Name-only descriptors are used by pure router tests.
            selected.append(tool.name)
    return tuple(dict.fromkeys(selected))


def _cn_futures_tools(text: str, available: set[str]) -> tuple[str, ...]:
    wanted = list(_CN_FUTURES_BASE)
    if re.search(r"(分时|分钟|\b(?:1|5|15|30|60)m\b|intraday|minute)", text, re.I):
        wanted.append("lookup_cn_futures_minute")
    if re.search(r"(盘口|l1|买一|卖一|market depth)", text, re.I):
        wanted.append("lookup_cn_futures_l1")
    if re.search(r"(保证金|margin)", text, re.I):
        wanted.append("calculate_cn_futures_margin")
    return _unique_available(wanted, available)


def _all_market_data_names(
    available: set[str], spot_tools: tuple[str, ...]
) -> tuple[str, ...]:
    return _unique_available(
        (
            *spot_tools,
            *_CN_STOCK_TOOLS,
            *_CN_FUTURES_BASE,
            *_CN_FUTURES_EXTRA,
            *_CN_OPTION_TOOLS,
            *_YAHOO_TOOLS,
            *_WEB_TOOLS,
        ),
        available,
    )


def _product_name(mentions: tuple[CNFuturesSymbol, ...]) -> str | None:
    return mentions[0].name if len(mentions) == 1 else None


def _has_cn_contract_code(
    text: str, mentions: tuple[CNFuturesSymbol, ...]
) -> bool:
    for mention in mentions:
        product = re.escape(mention.product)
        exchange = re.escape(mention.exchange)
        if re.search(rf"\b{product}(?:\d{{1,4}}|\.{exchange})\b", text, re.I):
            return True
    return False


def _clarification(
    *,
    product: str | None,
    scopes: tuple[MarketScopeTools, ...],
    options: tuple[MarketClarificationOption, ...],
    available: set[str],
    spot_tools: tuple[str, ...],
    supplemental_web: tuple[str, ...],
) -> MarketToolSelection:
    allowed = _unique_available(
        (
            "ask_user",
            *(name for item in scopes for name in item.tool_names),
            *supplemental_web,
        ),
        available,
    )
    blocked = tuple(
        name
        for name in _all_market_data_names(available, spot_tools)
        if name not in supplemental_web
    )
    return MarketToolSelection(
        intent=MarketIntent(
            MarketIntentKind.CLARIFY,
            product=product,
            reason="market scope is ambiguous",
        ),
        allowed_tool_names=allowed,
        scope_tools=scopes,
        blocked_tool_names=blocked,
        clarification_options=options,
        capability_available=any(item.tool_names for item in scopes),
        web_is_supplemental=bool(supplemental_web),
    )


def resolve_market_tools(
    text: str, tools: Iterable[ToolDescriptor]
) -> MarketToolSelection:
    """Resolve market scope and return the exact Provider-visible Tool set."""

    raw = str(text or "").strip()
    descriptors = tuple(tools)
    available = {tool.name for tool in descriptors}
    spot_tools = _chemical_spot_tools(descriptors)
    mentions = find_futures_mentions(raw)
    contract_code = _has_cn_contract_code(raw, mentions)
    qualified_futures = bool(
        _FUTURES_RE.search(raw)
        and (
            mentions
            or _WTI_RE.search(raw)
            or _BRENT_RE.search(raw)
            or _GLOBAL_RE.search(raw)
        )
    )
    price_like = bool(
        _PRICE_RE.search(raw)
        or _SPOT_RE.search(raw)
        or contract_code
        or qualified_futures
    )
    supplemental_web = (
        _unique_available(_WEB_TOOLS, available) if _DRIVER_RE.search(raw) else ()
    )

    if not price_like and not _CN_STOCK_RE.search(raw) and not _CN_OPTION_RE.search(raw):
        return MarketToolSelection.non_market()

    if _CN_OPTION_RE.search(raw):
        selected = _unique_available(_CN_OPTION_TOOLS, available)
        return _resolved_selection(
            MarketIntent(MarketIntentKind.LISTED_SECURITY, scope=MarketScope.CN_OPTION),
            MarketScope.CN_OPTION,
            selected,
            available,
            spot_tools,
            supplemental_web,
        )

    if _CN_STOCK_RE.search(raw):
        selected = _unique_available(_CN_STOCK_TOOLS, available)
        return _resolved_selection(
            MarketIntent(MarketIntentKind.LISTED_SECURITY, scope=MarketScope.CN_STOCK),
            MarketScope.CN_STOCK,
            selected,
            available,
            spot_tools,
            supplemental_web,
        )

    if _SPOT_RE.search(raw) and not _CLEAR_FINANCIAL_SPOT_RE.search(raw):
        return _resolved_selection(
            MarketIntent(
                MarketIntentKind.CHEMICAL_SPOT,
                product=_product_name(mentions),
                scope=MarketScope.CHEMICAL_SPOT,
                reason="explicit spot qualifier",
            ),
            MarketScope.CHEMICAL_SPOT,
            spot_tools,
            available,
            spot_tools,
            supplemental_web,
        )

    wti = bool(_WTI_RE.search(raw))
    brent = bool(_BRENT_RE.search(raw))
    if wti or brent:
        scope = MarketScope.WTI_FUTURES if wti and not brent else MarketScope.BRENT_FUTURES
        if wti and brent:
            scope = MarketScope.GLOBAL_FUTURES
        selected = _unique_available(_YAHOO_TOOLS, available)
        return _resolved_selection(
            MarketIntent(
                MarketIntentKind.GLOBAL_FUTURES,
                product=(
                    "WTI"
                    if scope is MarketScope.WTI_FUTURES
                    else "Brent" if scope is MarketScope.BRENT_FUTURES else None
                ),
                scope=scope,
                reason="explicit global futures marker",
            ),
            scope,
            selected,
            available,
            spot_tools,
            supplemental_web,
        )

    if _GLOBAL_RE.search(raw):
        selected = _unique_available(_YAHOO_TOOLS, available)
        return _resolved_selection(
            MarketIntent(MarketIntentKind.GLOBAL_FUTURES, scope=MarketScope.GLOBAL_FUTURES),
            MarketScope.GLOBAL_FUTURES,
            selected,
            available,
            spot_tools,
            supplemental_web,
        )

    explicit_futures = bool(_FUTURES_RE.search(raw) or contract_code)
    if explicit_futures and mentions:
        crude_only = len(mentions) == 1 and mentions[0].product == "SC"
        domestic_marker = bool(re.search(r"(国内|中国|上海|上期|INE|SC\d|SC\.)", raw, re.I))
        if crude_only and not domestic_marker:
            yahoo = _unique_available(_YAHOO_TOOLS, available)
            cn = _cn_futures_tools(raw, available)
            scopes = (
                MarketScopeTools(MarketScope.CN_FUTURES, cn),
                MarketScopeTools(MarketScope.WTI_FUTURES, yahoo),
                MarketScopeTools(MarketScope.BRENT_FUTURES, yahoo),
            )
            return _clarification(
                product=mentions[0].name,
                scopes=scopes,
                options=(
                    MarketClarificationOption("上海原油期货", "人民币计价的 INE 原油期货", MarketScope.CN_FUTURES),
                    MarketClarificationOption("WTI期货", "纽约市场 WTI 原油期货", MarketScope.WTI_FUTURES),
                    MarketClarificationOption("布伦特期货", "布伦特原油期货", MarketScope.BRENT_FUTURES),
                ),
                available=available,
                spot_tools=spot_tools,
                supplemental_web=supplemental_web,
            )
        selected = _cn_futures_tools(raw, available)
        return _resolved_selection(
            MarketIntent(
                MarketIntentKind.CN_FUTURES,
                product=_product_name(mentions),
                scope=MarketScope.CN_FUTURES,
                reason="explicit CN futures product/contract",
            ),
            MarketScope.CN_FUTURES,
            selected,
            available,
            spot_tools,
            supplemental_web,
        )

    if mentions and price_like:
        cn = _cn_futures_tools(raw, available)
        product = _product_name(mentions)
        scopes: list[MarketScopeTools] = [
            MarketScopeTools(MarketScope.CHEMICAL_SPOT, spot_tools),
            MarketScopeTools(MarketScope.CN_FUTURES, cn),
        ]
        options: list[MarketClarificationOption] = [
            MarketClarificationOption(
                "化工现货",
                "按地区读取 chem-data-hub 现货序列",
                MarketScope.CHEMICAL_SPOT,
            ),
            MarketClarificationOption("国内期货", "读取交易所合约/主力日线", MarketScope.CN_FUTURES),
        ]
        if len(mentions) == 1 and mentions[0].product == "SC":
            yahoo = _unique_available(_YAHOO_TOOLS, available)
            scopes.extend(
                [
                    MarketScopeTools(MarketScope.WTI_FUTURES, yahoo),
                    MarketScopeTools(MarketScope.BRENT_FUTURES, yahoo),
                ]
            )
            options = [
                MarketClarificationOption(
                    "原油现货",
                    "读取 chem-data-hub 原油现货序列",
                    MarketScope.CHEMICAL_SPOT,
                ),
                MarketClarificationOption("上海原油期货", "人民币计价的 INE 原油期货", MarketScope.CN_FUTURES),
                MarketClarificationOption("WTI期货", "纽约市场 WTI 原油期货", MarketScope.WTI_FUTURES),
                MarketClarificationOption("布伦特期货", "布伦特原油期货", MarketScope.BRENT_FUTURES),
            ]
        return _clarification(
            product=product,
            scopes=tuple(scopes),
            options=tuple(options),
            available=available,
            spot_tools=spot_tools,
            supplemental_web=supplemental_web,
        )

    if explicit_futures:
        selected = _unique_available(_YAHOO_TOOLS, available)
        return _resolved_selection(
            MarketIntent(MarketIntentKind.GLOBAL_FUTURES, scope=MarketScope.GLOBAL_FUTURES),
            MarketScope.GLOBAL_FUTURES,
            selected,
            available,
            spot_tools,
            supplemental_web,
        )

    return MarketToolSelection.non_market()


def _resolved_selection(
    intent: MarketIntent,
    scope: MarketScope,
    primary_tools: tuple[str, ...],
    available: set[str],
    spot_tools: tuple[str, ...],
    supplemental_web: tuple[str, ...],
) -> MarketToolSelection:
    allowed = _unique_available((*primary_tools, *supplemental_web), available)
    competitors = _all_market_data_names(available, spot_tools)
    blocked = tuple(name for name in competitors if name not in allowed)
    return MarketToolSelection(
        intent=intent,
        allowed_tool_names=allowed,
        scope_tools=(MarketScopeTools(scope, primary_tools),),
        blocked_tool_names=blocked,
        capability_available=bool(primary_tools),
        web_is_supplemental=bool(supplemental_web),
    )


def render_market_turn_context(selection: MarketToolSelection) -> str:
    """Compact per-turn instruction; contains no user/provider data."""

    if not selection.intent.is_market:
        return ""
    if selection.needs_clarification:
        options = [
            {
                "label": item.label,
                "description": item.description,
                "recommended": index == 0,
            }
            for index, item in enumerate(selection.clarification_options)
        ]
        return (
            "<market-scope-policy>\n"
            "This request has more than one valid market scope. Before calling any price "
            "tool, call `ask_user` once with header `行情口径`, allow_text=false, and these "
            f"options: {options!r}. After the answer, use only the matching market Tool. "
            "WTI maps to Yahoo symbol CL=F; Brent maps to BZ=F. If the selected scope "
            "has no projected data Tool, report that source as unavailable in Chinese. "
            "Never use Web as the price source.\n"
            "</market-scope-policy>"
        )
    if selection.intent.kind is MarketIntentKind.CHEMICAL_SPOT:
        availability = (
            "Call the projected chem-data-hub `get_price_trend` Tool."
            if selection.capability_available
            else "chem-data-hub `get_price_trend` is not available; report unavailable in Chinese."
        )
        return (
            "<market-scope-policy>\n"
            "The user explicitly requested CHEMICAL SPOT prices. Spot outranks product aliases. "
            f"{availability} Do not call CN futures, Yahoo, or Web to substitute a price. "
            "If the Tool returns no rows, say there is no spot data.\n"
            "</market-scope-policy>"
        )
    symbol_rule = ""
    if selection.intent.scope is MarketScope.WTI_FUTURES:
        symbol_rule = " Use Yahoo symbol CL=F."
    elif selection.intent.scope is MarketScope.BRENT_FUTURES:
        symbol_rule = " Use Yahoo symbol BZ=F."
    return (
        "<market-scope-policy>\n"
        "Use only the projected Tool for the selected futures/securities market."
        f"{symbol_rule} Do not use Web "
        "as the price source; Web is supplemental only when the user explicitly requested "
        "news or drivers.\n"
        "</market-scope-policy>"
    )
