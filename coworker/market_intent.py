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
    CN_SPOT_FUTURES = "cn_spot_futures"
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
            if self.intent.kind is MarketIntentKind.CN_SPOT_FUTURES:
                return tuple(
                    dict.fromkeys(
                        name for item in self.scope_tools for name in item.tool_names
                    )
                )
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
_BASIS_RE = re.compile(
    r"(期现|基差|\bbasis\b|cash[\s-]?and[\s-]?carry|spot[\s/-]?futures)",
    re.I,
)
_ARB_RE = re.compile(r"(套利|arb(?:itrage)?)", re.I)
_UPSTREAM_DOWNSTREAM_RE = re.compile(r"(上下游|产业链)", re.I)
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


def _chem_web_tools(available: set[str]) -> tuple[str, ...]:
    """D-181: chemical spot/CN futures/dual always allow ordered Web fallback."""
    return _unique_available(_WEB_TOOLS, available)


def _driver_web_tools(raw: str, available: set[str]) -> tuple[str, ...]:
    """Non-chem markets: Web only when news/drivers are explicit (D-166 legacy)."""
    if not _DRIVER_RE.search(raw):
        return ()
    return _unique_available(_WEB_TOOLS, available)


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
    """Return whether a dynamic MCP can itself supply a price-bearing value.

    ``market`` alone is deliberately not a signal: tools such as
    ``list_market_news_live`` provide supporting evidence, not a spot/futures
    quote, and must not be rejected by the price-scope guard.
    """
    parts = _mcp_parts(name)
    return bool(
        parts
        and re.search(r"(?:price|prices|quote|quotes|trend|ohlc)", parts[1], re.I)
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


def _wants_spot_futures_dual(
    text: str,
    *,
    mentions: tuple[CNFuturesSymbol, ...],
    contract_code: bool,
) -> bool:
    """True when the user explicitly asked to compare chemical spot with CN futures."""

    if not mentions and not contract_code:
        return False
    has_spot = bool(_SPOT_RE.search(text))
    has_futures = bool(_FUTURES_RE.search(text) or contract_code)
    if has_spot and has_futures:
        return True
    if _BASIS_RE.search(text):
        return True
    if has_futures and _ARB_RE.search(text):
        return True
    if has_futures and _UPSTREAM_DOWNSTREAM_RE.search(text) and _PRICE_RE.search(text):
        return True
    if has_futures and _UPSTREAM_DOWNSTREAM_RE.search(text) and _ARB_RE.search(text):
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
        or (
            mentions
            and (
                _BASIS_RE.search(raw)
                or (
                    _ARB_RE.search(raw)
                    and (_FUTURES_RE.search(raw) or contract_code)
                )
                or (
                    _UPSTREAM_DOWNSTREAM_RE.search(raw)
                    and (_FUTURES_RE.search(raw) or contract_code)
                )
            )
        )
    )
    supplemental_web = _driver_web_tools(raw, available)
    chem_web = _chem_web_tools(available)

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

    if _wants_spot_futures_dual(
        raw, mentions=mentions, contract_code=contract_code
    ) and not _CLEAR_FINANCIAL_SPOT_RE.search(raw):
        # Domestic chem spot + CN futures in one turn (basis / arb / explicit both).
        # Must outrank exclusive spot-only and futures-only branches.
        return _resolved_dual_selection(
            product=_product_name(mentions),
            spot_tools=spot_tools,
            cn_tools=_cn_futures_tools(raw, available),
            available=available,
            supplemental_web=chem_web,
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
            chem_web,
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
                supplemental_web=chem_web,
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
            chem_web,
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
            supplemental_web=chem_web,
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


def _resolved_dual_selection(
    *,
    product: str | None,
    spot_tools: tuple[str, ...],
    cn_tools: tuple[str, ...],
    available: set[str],
    supplemental_web: tuple[str, ...],
) -> MarketToolSelection:
    primary = _unique_available((*spot_tools, *cn_tools), available)
    allowed = _unique_available((*primary, *supplemental_web), available)
    competitors = _all_market_data_names(available, spot_tools)
    blocked = tuple(name for name in competitors if name not in allowed)
    return MarketToolSelection(
        intent=MarketIntent(
            MarketIntentKind.CN_SPOT_FUTURES,
            product=product,
            scope=None,
            reason="explicit spot-futures basis or arbitrage",
        ),
        allowed_tool_names=allowed,
        scope_tools=(
            MarketScopeTools(MarketScope.CHEMICAL_SPOT, spot_tools),
            MarketScopeTools(MarketScope.CN_FUTURES, cn_tools),
        ),
        blocked_tool_names=blocked,
        capability_available=bool(primary),
        web_is_supplemental=bool(supplemental_web),
    )


def render_market_turn_context(selection: MarketToolSelection) -> str:
    """Compact per-turn instruction; contains no user/provider data."""

    if not selection.intent.is_market:
        return ""
    web_fallback = (
        "若已投影的结构化工具缺失或无行，可作为最后手段用 `web_search`/`web_fetch` 查价或做研究；"
        "须注明 URL 与时间；禁止把网页数字说成 chem-data-hub 或交易所官方数据。"
    )
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
            "本请求存在多种有效行情口径。在调用任何价格工具之前，先调用一次 `ask_user`，"
            "header 为 `行情口径`，allow_text=false，选项如下："
            f"{options!r}。用户回答后，只使用对应口径的行情工具。"
            "WTI 对应 Yahoo 符号 CL=F；Brent 对应 BZ=F。"
            f"{web_fallback}"
            "不要用网页给用户尚未选定的口径编造价格。\n"
            "</market-scope-policy>"
        )
    if selection.intent.kind is MarketIntentKind.CHEMICAL_SPOT:
        availability = (
            "请先调用已投影的 chem-data-hub `get_price_trend` 工具。"
            if selection.capability_available
            else "chem-data-hub `get_price_trend` 当前不可用。"
        )
        return (
            "<market-scope-policy>\n"
            "用户明确要求化工现货价。现货口径优先于产品别名。"
            f"{availability} 禁止用国内期货或 Yahoo 替代现货价。"
            f"{web_fallback}\n"
            "</market-scope-policy>"
        )
    if selection.intent.kind is MarketIntentKind.CN_SPOT_FUTURES:
        spot_ok = any(
            item.scope is MarketScope.CHEMICAL_SPOT and item.tool_names
            for item in selection.scope_tools
        )
        futures_ok = any(
            item.scope is MarketScope.CN_FUTURES and item.tool_names
            for item in selection.scope_tools
        )
        return (
            "<market-scope-policy>\n"
            "用户同时需要化工现货与国内期货（基差 / 套利 / 期现对照）。"
            "同一回合在两者均已投影时，用 chem-data-hub `get_price_trend` 取现货，"
            "用 `lookup_cn_futures_*` 取期货。"
            f"现货工具可用={spot_ok}；国内期货工具可用={futures_ok}。"
            "每个数字须标注市场来源。禁止用期货代替现货，也禁止用现货代替期货。"
            "禁止用 Yahoo 作为这对国内期现的价格源。"
            f"{web_fallback}"
            "若只有一侧结构化源缺失，网页最多补缺该侧——不可用已有结构化价去编造另一侧。\n"
            "</market-scope-policy>"
        )
    if selection.intent.kind is MarketIntentKind.CN_FUTURES:
        return (
            "<market-scope-policy>\n"
            "用户要求国内期货。请先调用已投影的 `lookup_cn_futures_*` 工具。"
            "禁止用 chem-data-hub 现货或 Yahoo 替代国内期货价。"
            f"{web_fallback}\n"
            "</market-scope-policy>"
        )
    symbol_rule = ""
    if selection.intent.scope is MarketScope.WTI_FUTURES:
        symbol_rule = " 使用 Yahoo 符号 CL=F。"
    elif selection.intent.scope is MarketScope.BRENT_FUTURES:
        symbol_rule = " 使用 Yahoo 符号 BZ=F。"
    return (
        "<market-scope-policy>\n"
        "仅使用已投影的工具查询所选期货/证券行情。"
        f"{symbol_rule} 不要把网页当作价格源；仅当用户明确要新闻或驱动因素时，"
        "网页才可作为补充。\n"
        "</market-scope-policy>"
    )


# -- D-179 parent → child market selection inheritance -------------------------

_MARKET_SELECTION_META_KEY = "market_selection_json"


def snapshot_market_selection_metadata(
    selection: MarketToolSelection | None,
) -> dict[str, str]:
    """Serialize a live parent selection into BackgroundTask metadata (str→str)."""
    import json

    if selection is None or not selection.intent.is_market:
        return {}
    payload = {
        "kind": selection.intent.kind.value,
        "product": selection.intent.product,
        "scope": selection.intent.scope.value if selection.intent.scope else None,
        "reason": selection.intent.reason,
        "allowed": list(selection.allowed_tool_names or ()),
        "blocked": list(selection.blocked_tool_names),
        "scope_tools": [
            {"scope": item.scope.value, "tools": list(item.tool_names)}
            for item in selection.scope_tools
        ],
        "clarification_options": [
            {
                "label": item.label,
                "description": item.description,
                "scope": item.scope.value,
            }
            for item in selection.clarification_options
        ],
        "capability_available": selection.capability_available,
        "web_is_supplemental": selection.web_is_supplemental,
    }
    return {_MARKET_SELECTION_META_KEY: json.dumps(payload, ensure_ascii=False)}


def restore_market_selection_from_metadata(
    metadata: dict[str, str] | None,
) -> MarketToolSelection | None:
    """Rebuild MarketToolSelection from task metadata; None if absent/invalid."""
    import json

    if not metadata:
        return None
    raw = metadata.get(_MARKET_SELECTION_META_KEY)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        kind = MarketIntentKind(str(payload.get("kind") or ""))
        scope_raw = payload.get("scope")
        scope = MarketScope(scope_raw) if scope_raw else None
        intent = MarketIntent(
            kind=kind,
            product=payload.get("product") if isinstance(payload.get("product"), str) else None,
            scope=scope,
            reason=str(payload.get("reason") or ""),
        )
        scope_tools = tuple(
            MarketScopeTools(
                MarketScope(str(item["scope"])),
                tuple(str(name) for name in (item.get("tools") or [])),
            )
            for item in (payload.get("scope_tools") or [])
            if isinstance(item, dict) and item.get("scope")
        )
        clarification = tuple(
            MarketClarificationOption(
                label=str(item.get("label") or ""),
                description=str(item.get("description") or ""),
                scope=MarketScope(str(item["scope"])),
            )
            for item in (payload.get("clarification_options") or [])
            if isinstance(item, dict) and item.get("scope")
        )
        allowed_raw = payload.get("allowed")
        allowed = tuple(str(name) for name in allowed_raw) if isinstance(allowed_raw, list) else None
        blocked = tuple(str(name) for name in (payload.get("blocked") or []))
        return MarketToolSelection(
            intent=intent,
            allowed_tool_names=allowed,
            scope_tools=scope_tools,
            blocked_tool_names=blocked,
            clarification_options=clarification,
            capability_available=bool(payload.get("capability_available", True)),
            web_is_supplemental=bool(payload.get("web_is_supplemental", False)),
        )
    except (TypeError, ValueError, KeyError):
        return None


def merge_inherited_market_selection(
    inherited: MarketToolSelection | None,
    planned: MarketToolSelection | None,
) -> MarketToolSelection | None:
    """Prefer parent scope; allow child to narrow ⊆ inherited; never widen or flip.

    Clarify / non-market planned selections fall back to inherited when the parent
    already resolved a market intent (D-179).
    """
    if inherited is None or not inherited.intent.is_market:
        return planned
    if planned is None or not planned.intent.is_market or planned.needs_clarification:
        return inherited
    inherited_allowed = set(inherited.allowed_tool_names or ())
    planned_allowed = set(planned.allowed_tool_names or ())
    # Empty planned allowlist means "unrestricted within selection" — keep inherited.
    if not planned_allowed:
        return inherited
    if planned_allowed <= inherited_allowed:
        return planned
    return inherited


def current_market_selection_from_engine(engine: object) -> MarketToolSelection | None:
    """Read the live or last TurnPlan market selection from a TurnEngine-like object."""
    plan = getattr(engine, "_active_turn_plan", None) or getattr(
        engine, "_last_turn_plan", None
    )
    if plan is None:
        return None
    selection = getattr(plan, "market_selection", None)
    if selection is None or not getattr(selection.intent, "is_market", False):
        return None
    return selection
