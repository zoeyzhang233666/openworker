"""Keyless China options HTTP provider (Sina SSE ETF + CFFEX board).

Does not import AKShare. SSE exchange query.sse.com.cn is attempt-optional and
may be unavailable; contract discovery prefers Sina OP_UP/OP_DOWN lists.
Greeks are upstream-only (hq.sinajs.cn CON_SO_*); no local BS invent.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Union

from ..cache import CacheKey, MarketCache
from ..errors import InvalidSymbolError
from ..http import DISCLAIMER, USER_AGENT, HttpGet, default_http_get
from ..models import (
    STATUS_INVALID_REQUEST,
    STATUS_INVALID_SYMBOL,
    STATUS_OK,
    STATUS_PARTIAL,
    STATUS_SOURCE_UNAVAILABLE,
    STATUS_UNSUPPORTED,
    FeatureTable,
    MarketResult,
    OhlcBar,
    OhlcSeries,
    OptionGreeks,
    OptionQuote,
    SourceMeta,
)
from ..symbols import (
    normalize_option_contract,
    resolve_option_underlying,
)

Clock = Callable[[], datetime]
OptionResult = Union[FeatureTable, OptionQuote, OptionGreeks, OhlcSeries, MarketResult]

ACTIONS = frozenset(
    {"contracts", "quote", "daily", "minute", "greeks", "exchange_stats"}
)
ALLOWED_RANGES = frozenset({"1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"})
RANGE_BARS = {
    "1mo": 22,
    "3mo": 66,
    "6mo": 132,
    "1y": 244,
    "2y": 488,
    "5y": 1023,
    "max": 1023,
}

SINA_HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://stock.finance.sina.com.cn/option/quotes.html",
    "Accept": "*/*",
}
HQ_HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://stock.finance.sina.com.cn/",
    "Accept": "*/*",
}

_CON_OP_RE = re.compile(r"CON_OP_(\d+)")


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def _decode_text(body: bytes) -> str:
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


def _parse_jsonish(text: str) -> Any:
    stripped = text.strip()
    # Strip sina redirect prefix
    if stripped.startswith("/*"):
        end = stripped.find("*/")
        if end >= 0:
            stripped = stripped[end + 2 :].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("(")
        end = stripped.rfind(")")
        if start < 0 or end <= start:
            raise
        return json.loads(stripped[start + 1 : end])


def _hq_fields(text: str) -> list[str]:
    start = text.find('"')
    end = text.rfind('"')
    if start < 0 or end <= start:
        return []
    return text[start + 1 : end].split(",")


def _normalize_expiry(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 6:
        return digits[:6]
    if len(digits) == 4:
        return digits
    return raw.strip()


class PublicCNOptionProvider:
    name = "cn_option_public"

    def __init__(
        self,
        *,
        http_get: Optional[HttpGet] = None,
        cache: Optional[MarketCache] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._http_get = http_get or default_http_get
        self._cache = cache
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now_iso(self) -> str:
        return self._clock().isoformat()

    def _source(self, provider: str, upstream: str, *, cached: bool = False) -> SourceMeta:
        return SourceMeta(
            provider=provider,
            upstream=upstream,
            cached=cached,
            fetched_at=self._now_iso(),
            attempt=1,
            source_version="1",
        )

    def _get(self, url: str, headers: Optional[dict[str, str]] = None) -> tuple[int, bytes]:
        return self._http_get(url, headers or SINA_HEADERS)

    def _cache_get(self, key: CacheKey) -> Optional[dict[str, Any]]:
        if self._cache is None:
            return None
        hit = self._cache.get(key)
        if hit is None or not hit.fresh:
            return None
        payload = hit.payload
        return payload if isinstance(payload, dict) else None

    def _cache_put(self, key: CacheKey, payload: dict[str, Any], *, dataset_kind: str) -> None:
        if self._cache is None:
            return
        self._cache.put(key, payload, dataset_kind=dataset_kind)

    def option_market(
        self,
        *,
        action: str,
        underlying: str = "",
        contract: str = "",
        expiry: str = "",
        option_type: str = "",
        range: str = "3mo",
    ) -> OptionResult:
        act = (action or "").strip().lower()
        if act not in ACTIONS:
            return MarketResult(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_option", "stock.finance.sina.com.cn"),
                error=f"action 须为其一：{', '.join(sorted(ACTIONS))}",
                warnings=[DISCLAIMER],
            )
        if act == "contracts":
            return self._contracts(underlying=underlying, expiry=expiry, option_type=option_type)
        if act == "quote":
            return self._quote(contract)
        if act == "daily":
            return self._daily(contract, chart_range=range)
        if act == "minute":
            return self._minute(contract)
        if act == "greeks":
            return self._greeks(contract)
        return self._exchange_stats(underlying=underlying)

    def _contracts(
        self,
        *,
        underlying: str,
        expiry: str,
        option_type: str,
    ) -> FeatureTable:
        try:
            u = resolve_option_underlying(underlying or "510050")
        except InvalidSymbolError as exc:
            return FeatureTable(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_option", "hq.sinajs.cn"),
                dataset="option_contracts",
                error=str(exc),
            )
        if u.exchange == "CFFEX":
            return self._cffex_contracts(u, expiry=expiry, option_type=option_type)
        return self._sse_contracts(u, expiry=expiry, option_type=option_type)

    def _sse_months(self, cate: str) -> list[str]:
        url = (
            "https://stock.finance.sina.com.cn/futures/api/openapi.php/"
            "StockOptionService.getStockName?"
            + urllib.parse.urlencode({"exchange": "null", "cate": cate})
        )
        try:
            status, body = self._get(url, SINA_HEADERS)
        except Exception:
            return []
        if status != 200:
            return []
        try:
            payload = _parse_jsonish(_decode_text(body))
            months = payload["result"]["data"]["contractMonth"]
        except Exception:
            return []
        out: list[str] = []
        seen: set[str] = set()
        for item in months:
            digits = "".join(str(item).split("-"))
            if len(digits) >= 6 and digits not in seen:
                seen.add(digits)
                out.append(digits)
        return out

    def _sse_contracts(
        self,
        u,
        *,
        expiry: str,
        option_type: str,
    ) -> FeatureTable:
        months = self._sse_months(u.sina_cate)
        want = _normalize_expiry(expiry)
        if want and len(want) == 6:
            month_list = [want]
        elif want and len(want) == 4 and months:
            month_list = [m for m in months if m.endswith(want)] or [months[0]]
        elif months:
            # Prefer next listed month after the first duplicate current month.
            month_list = [months[1] if len(months) > 1 else months[0]]
        else:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "StockOptionService.getStockName"),
                dataset="option_contracts",
                symbol=u.code,
                error="无法获取期权到期月列表",
                warnings=[DISCLAIMER],
            )
        ot = (option_type or "").strip().lower()
        sides: list[tuple[str, str]] = []
        if ot in {"", "all", "both"}:
            sides = [("call", "OP_UP"), ("put", "OP_DOWN")]
        elif ot in {"call", "c", "看涨", "认购"}:
            sides = [("call", "OP_UP")]
        elif ot in {"put", "p", "看跌", "认沽"}:
            sides = [("put", "OP_DOWN")]
        else:
            return FeatureTable(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_option", "hq.sinajs.cn"),
                dataset="option_contracts",
                error="option_type 须为 call / put / all",
                warnings=[DISCLAIMER],
            )
        rows: list[dict[str, Any]] = []
        for month in month_list:
            yyymm = month[-4:]
            for opt_type, prefix in sides:
                url = f"https://hq.sinajs.cn/list={prefix}_{u.code}{yyymm}"
                try:
                    status, body = self._get(url, HQ_HEADERS)
                except Exception as exc:
                    return FeatureTable(
                        status=STATUS_SOURCE_UNAVAILABLE,
                        source=self._source("sina_option", "hq.sinajs.cn"),
                        dataset="option_contracts",
                        symbol=u.code,
                        error=str(exc),
                        warnings=[DISCLAIMER],
                    )
                if status != 200:
                    continue
                text = _decode_text(body)
                for code in _CON_OP_RE.findall(text):
                    rows.append(
                        {
                            "contract": code,
                            "underlying": u.code,
                            "exchange": u.exchange,
                            "option_type": opt_type,
                            "expiry": month,
                            "strike": None,
                        }
                    )
        if not rows:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "hq.sinajs.cn"),
                dataset="option_contracts",
                symbol=u.code,
                error="未找到期权合约",
                warnings=[DISCLAIMER],
            )
        return FeatureTable(
            status=STATUS_OK,
            source=self._source("sina_option", "hq.sinajs.cn"),
            warnings=[DISCLAIMER],
            dataset="option_contracts",
            symbol=u.code,
            rows=rows,
        )

    def _cffex_contracts(self, u, *, expiry: str, option_type: str) -> FeatureTable:
        product = u.cffex_product or u.code.lower()
        pinzhong = (expiry or "").strip() or f"{product}2509"
        if pinzhong.isdigit():
            pinzhong = f"{product}{pinzhong[-4:]}"
        url = (
            "https://stock.finance.sina.com.cn/futures/api/openapi.php/OptionService.getOptionData?"
            + urllib.parse.urlencode(
                {
                    "type": "futures",
                    "product": product,
                    "exchange": "cffex",
                    "pinzhong": pinzhong,
                }
            )
        )
        try:
            status, body = self._get(url, SINA_HEADERS)
        except Exception as exc:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "OptionService.getOptionData"),
                dataset="option_contracts",
                symbol=u.code,
                error=str(exc),
                warnings=[DISCLAIMER],
            )
        if status != 200:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "OptionService.getOptionData"),
                dataset="option_contracts",
                symbol=u.code,
                error=f"HTTP {status}",
                warnings=[DISCLAIMER],
            )
        try:
            payload = _parse_jsonish(_decode_text(body))
            data = payload["result"]["data"]
        except Exception:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "OptionService.getOptionData"),
                dataset="option_contracts",
                symbol=u.code,
                error="中金所期权盘口无法解析",
                warnings=[DISCLAIMER],
            )
        ot = (option_type or "").strip().lower()
        rows: list[dict[str, Any]] = []
        if ot in {"", "all", "both", "call", "c", "看涨", "认购"}:
            for item in data.get("up") or []:
                if not isinstance(item, (list, tuple)) or len(item) < 9:
                    continue
                rows.append(
                    {
                        "contract": str(item[8]),
                        "underlying": u.code,
                        "exchange": "CFFEX",
                        "option_type": "call",
                        "expiry": pinzhong,
                        "strike": _num(item[7]),
                        "last": _num(item[2]),
                        "bid1": _num(item[1]),
                        "ask1": _num(item[3]),
                        "open_interest": _num(item[5]),
                    }
                )
        if ot in {"", "all", "both", "put", "p", "看跌", "认沽"}:
            for item in data.get("down") or []:
                if not isinstance(item, (list, tuple)) or len(item) < 9:
                    continue
                rows.append(
                    {
                        "contract": str(item[8]),
                        "underlying": u.code,
                        "exchange": "CFFEX",
                        "option_type": "put",
                        "expiry": pinzhong,
                        "strike": _num(item[7]),
                        "last": _num(item[2]),
                        "bid1": _num(item[1]),
                        "ask1": _num(item[3]),
                        "open_interest": _num(item[5]),
                    }
                )
        if not rows:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "OptionService.getOptionData"),
                dataset="option_contracts",
                symbol=u.code,
                error="中金所期权合约为空",
                warnings=[DISCLAIMER],
            )
        return FeatureTable(
            status=STATUS_OK,
            source=self._source("sina_option", "OptionService.getOptionData"),
            warnings=[DISCLAIMER],
            dataset="option_contracts",
            symbol=u.code,
            rows=rows,
        )

    def _quote(self, contract: str) -> OptionQuote:
        try:
            code = normalize_option_contract(contract)
        except InvalidSymbolError as exc:
            return OptionQuote(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_option", "hq.sinajs.cn"),
                error=str(exc),
            )
        if not code.isdigit():
            return OptionQuote(
                status=STATUS_UNSUPPORTED,
                source=self._source("sina_option", "hq.sinajs.cn"),
                symbol=code,
                error="当前仅支持上交所数字合约代码的报价；中金所请用 contracts 盘口",
                warnings=[DISCLAIMER],
            )
        key = CacheKey(domain="option", symbol=code, dataset="quote")
        cached = self._cache_get(key)
        if cached:
            cached["source"]["cached"] = True
            return _option_quote_from_dict(cached)
        url = f"https://hq.sinajs.cn/list=CON_OP_{code}"
        try:
            status, body = self._get(url, HQ_HEADERS)
        except Exception as exc:
            return OptionQuote(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "hq.sinajs.cn"),
                symbol=code,
                error=str(exc),
                warnings=[DISCLAIMER],
            )
        if status != 200:
            return OptionQuote(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "hq.sinajs.cn"),
                symbol=code,
                error=f"HTTP {status}",
                warnings=[DISCLAIMER],
            )
        fields = _hq_fields(_decode_text(body))
        if not fields or all(not f for f in fields):
            return OptionQuote(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "hq.sinajs.cn"),
                symbol=code,
                error="期权报价为空（可能已到期）",
                warnings=[DISCLAIMER],
            )
        opt_type = None
        if len(fields) > 45 and fields[45] in {"C", "P"}:
            opt_type = "call" if fields[45] == "C" else "put"
        elif len(fields) > 37:
            name = fields[37]
            if "购" in name or "认购" in name:
                opt_type = "call"
            elif "沽" in name or "认沽" in name:
                opt_type = "put"
        quote = OptionQuote(
            status=STATUS_OK,
            source=self._source("sina_option", "hq.sinajs.cn"),
            as_of=fields[32] if len(fields) > 32 else None,
            warnings=[DISCLAIMER],
            symbol=code,
            name=fields[37] if len(fields) > 37 else None,
            underlying=fields[36] if len(fields) > 36 else None,
            exchange="SSE",
            option_type=opt_type,
            strike=_num(fields[7]) if len(fields) > 7 else None,
            expiry=fields[46] if len(fields) > 46 else None,
            last=_num(fields[2]) if len(fields) > 2 else None,
            open=_num(fields[9]) if len(fields) > 9 else None,
            high=_num(fields[39]) if len(fields) > 39 else None,
            low=_num(fields[40]) if len(fields) > 40 else None,
            prev_close=_num(fields[8]) if len(fields) > 8 else None,
            change_pct=_num(fields[6]) if len(fields) > 6 else None,
            volume=_num(fields[41]) if len(fields) > 41 else None,
            amount=_num(fields[42]) if len(fields) > 42 else None,
            open_interest=_num(fields[5]) if len(fields) > 5 else None,
            bid1=_num(fields[1]) if len(fields) > 1 else None,
            bid1_size=_num(fields[0]) if len(fields) > 0 else None,
            ask1=_num(fields[3]) if len(fields) > 3 else None,
            ask1_size=_num(fields[4]) if len(fields) > 4 else None,
        )
        self._cache_put(key, quote.to_dict(), dataset_kind="quote")
        return quote

    def _greeks(self, contract: str) -> OptionGreeks:
        try:
            code = normalize_option_contract(contract)
        except InvalidSymbolError as exc:
            return OptionGreeks(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_option", "hq.sinajs.cn"),
                error=str(exc),
                greeks_source="upstream",
            )
        if not code.isdigit():
            return OptionGreeks(
                status=STATUS_UNSUPPORTED,
                source=self._source("sina_option", "hq.sinajs.cn"),
                symbol=code,
                error="当前仅支持上交所数字合约 Greeks（上游 CON_SO_*）",
                warnings=[DISCLAIMER],
                greeks_source="upstream",
            )
        url = f"https://hq.sinajs.cn/list=CON_SO_{code}"
        try:
            status, body = self._get(url, HQ_HEADERS)
        except Exception as exc:
            return OptionGreeks(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "hq.sinajs.cn"),
                symbol=code,
                error=str(exc),
                warnings=[DISCLAIMER],
                greeks_source="upstream",
            )
        if status != 200:
            return OptionGreeks(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "hq.sinajs.cn"),
                symbol=code,
                error=f"HTTP {status}",
                warnings=[DISCLAIMER],
                greeks_source="upstream",
            )
        fields = _hq_fields(_decode_text(body))
        # AKShare maps: name = [0]; values = [0]+[4:] => volume at index 4 of raw
        if len(fields) < 14 or not fields[0]:
            return OptionGreeks(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "hq.sinajs.cn"),
                symbol=code,
                error="Greeks 为空",
                warnings=[DISCLAIMER],
                greeks_source="upstream",
            )
        return OptionGreeks(
            status=STATUS_OK,
            source=self._source("sina_option", "hq.sinajs.cn"),
            warnings=[DISCLAIMER, "greeks_source=upstream；未做本地 Black-Scholes 推算"],
            symbol=code,
            name=fields[0],
            volume=_num(fields[4]),
            delta=_num(fields[5]),
            gamma=_num(fields[6]),
            theta=_num(fields[7]),
            vega=_num(fields[8]),
            implied_vol=_num(fields[9]),
            trade_code=fields[12] if len(fields) > 12 else None,
            strike=_num(fields[13]) if len(fields) > 13 else None,
            last=_num(fields[14]) if len(fields) > 14 else None,
            theoretical=_num(fields[15]) if len(fields) > 15 else None,
            greeks_source="upstream",
        )

    def _daily(self, contract: str, *, chart_range: str) -> OhlcSeries:
        rng = (chart_range or "3mo").strip().lower()
        if rng not in ALLOWED_RANGES:
            return OhlcSeries(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_option", "StockOptionDaylineService"),
                error=f"range 须为其一：{', '.join(sorted(ALLOWED_RANGES))}",
                warnings=[DISCLAIMER],
            )
        try:
            code = normalize_option_contract(contract)
        except InvalidSymbolError as exc:
            return OhlcSeries(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_option", "StockOptionDaylineService"),
                error=str(exc),
            )
        if not code.isdigit():
            return OhlcSeries(
                status=STATUS_UNSUPPORTED,
                source=self._source("sina_option", "StockOptionDaylineService"),
                symbol=code,
                error="当前仅支持上交所数字合约日线",
                warnings=[DISCLAIMER],
            )
        key = CacheKey(
            domain="option",
            symbol=code,
            dataset="daily",
            interval="1d",
            source_version=f"sina-option:{rng}",
        )
        cached = self._cache_get(key)
        if cached:
            return OhlcSeries.from_dict(cached, cached=True)
        url = (
            "https://stock.finance.sina.com.cn/futures/api/jsonp_v2.php/"
            "/StockOptionDaylineService.getSymbolInfo?"
            + urllib.parse.urlencode({"symbol": f"CON_OP_{code}"})
        )
        try:
            status, body = self._get(url, SINA_HEADERS)
        except Exception as exc:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "StockOptionDaylineService"),
                symbol=code,
                error=str(exc),
                warnings=[DISCLAIMER],
            )
        if status != 200:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "StockOptionDaylineService"),
                symbol=code,
                error=f"HTTP {status}",
                warnings=[DISCLAIMER],
            )
        try:
            rows = _parse_jsonish(_decode_text(body))
        except Exception:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "StockOptionDaylineService"),
                symbol=code,
                error="期权日线无法解析",
                warnings=[DISCLAIMER],
            )
        if not isinstance(rows, list):
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "StockOptionDaylineService"),
                symbol=code,
                error="期权日线响应不是列表",
                warnings=[DISCLAIMER],
            )
        labels: list[str] = []
        ohlc: list[OhlcBar] = []
        volume: list[Optional[float]] = []
        for row in rows:
            if isinstance(row, dict):
                day = str(row.get("d") or row.get("date") or "")[:10]
                o, h, low, c = _num(row.get("o")), _num(row.get("h")), _num(row.get("l")), _num(
                    row.get("c")
                )
                vol = _num(row.get("v") or row.get("volume"))
            elif isinstance(row, (list, tuple)) and len(row) >= 5:
                day = str(row[0])[:10]
                o, h, low, c = _num(row[1]), _num(row[2]), _num(row[3]), _num(row[4])
                vol = _num(row[5]) if len(row) > 5 else None
            else:
                continue
            if not day or None in (o, h, low, c):
                continue
            assert o is not None and h is not None and low is not None and c is not None
            labels.append(day)
            ohlc.append(OhlcBar(o=o, h=h, l=low, c=c))
            volume.append(vol)
        if len(ohlc) < 2:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "StockOptionDaylineService"),
                symbol=code,
                error="可用 OHLC 点数不足（需要 ≥2）",
                warnings=[DISCLAIMER],
            )
        n = RANGE_BARS.get(rng, len(labels))
        if len(labels) > n:
            labels, ohlc, volume = labels[-n:], ohlc[-n:], volume[-n:]
        series = OhlcSeries(
            status=STATUS_OK,
            source=self._source("sina_option", "StockOptionDaylineService"),
            as_of=labels[-1],
            warnings=[DISCLAIMER],
            labels=labels,
            ohlc=ohlc,
            volume=volume,
            adjustment="none",
            symbol=code,
            interval="1d",
            actual_range=rng,
        )
        self._cache_put(key, series.to_dict(), dataset_kind="daily")
        return series

    def _minute(self, contract: str) -> OhlcSeries:
        try:
            code = normalize_option_contract(contract)
        except InvalidSymbolError as exc:
            return OhlcSeries(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_option", "getOptionMinline"),
                error=str(exc),
            )
        if not code.isdigit():
            return OhlcSeries(
                status=STATUS_UNSUPPORTED,
                source=self._source("sina_option", "getOptionMinline"),
                symbol=code,
                error="当前仅支持上交所数字合约分钟线",
                warnings=[DISCLAIMER],
            )
        key = CacheKey(domain="option", symbol=code, dataset="minute", interval="1m")
        cached = self._cache_get(key)
        if cached:
            return OhlcSeries.from_dict(cached, cached=True)
        url = (
            "https://stock.finance.sina.com.cn/futures/api/openapi.php/"
            "StockOptionDaylineService.getOptionMinline?"
            + urllib.parse.urlencode({"symbol": f"CON_OP_{code}"})
        )
        try:
            status, body = self._get(url, SINA_HEADERS)
        except Exception as exc:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "getOptionMinline"),
                symbol=code,
                error=str(exc),
                warnings=[DISCLAIMER],
            )
        if status != 200:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "getOptionMinline"),
                symbol=code,
                error=f"HTTP {status}",
                warnings=[DISCLAIMER],
            )
        try:
            payload = _parse_jsonish(_decode_text(body))
            rows = payload["result"]["data"]
        except Exception:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "getOptionMinline"),
                symbol=code,
                error="期权分钟线无法解析",
                warnings=[DISCLAIMER],
            )
        if not isinstance(rows, list) or not rows:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "getOptionMinline"),
                symbol=code,
                error="期权分钟线为空（仅当日）",
                warnings=[DISCLAIMER, "分钟线仅当前交易日"],
            )
        labels: list[str] = []
        ohlc: list[OhlcBar] = []
        volume: list[Optional[float]] = []
        day_prefix = ""
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("d"):
                day_prefix = str(row.get("d"))
            t = str(row.get("i") or "")
            px = _num(row.get("p") or row.get("a"))
            if not t or px is None:
                continue
            label = f"{day_prefix} {t}".strip() if day_prefix else t
            labels.append(label)
            ohlc.append(OhlcBar(o=px, h=px, l=px, c=px))
            volume.append(_num(row.get("v")))
        if len(ohlc) < 2:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_option", "getOptionMinline"),
                symbol=code,
                error="可用分钟点数不足（需要 ≥2）",
                warnings=[DISCLAIMER],
            )
        series = OhlcSeries(
            status=STATUS_OK,
            source=self._source("sina_option", "getOptionMinline"),
            as_of=labels[-1],
            warnings=[DISCLAIMER, "分钟线仅当前交易日；点价序列归一为 OHLC"],
            labels=labels,
            ohlc=ohlc,
            volume=volume,
            adjustment="none",
            symbol=code,
            interval="1m",
            actual_range="session",
        )
        self._cache_put(key, series.to_dict(), dataset_kind="minute")
        return series

    def _exchange_stats(self, *, underlying: str) -> FeatureTable:
        # Run 0: option_daily_stats_sse schema broken; SSE query also timed out live.
        return FeatureTable(
            status=STATUS_SOURCE_UNAVAILABLE,
            source=self._source("sse_option_stats", "query.sse.com.cn"),
            dataset="option_exchange_stats",
            symbol=underlying or None,
            error=(
                "上交所期权每日统计在 Run 0 验证失败（字段映射错误），"
                "且 query.sse.com.cn 本机探测超时；未发明替代源"
            ),
            warnings=[DISCLAIMER],
        )


def _option_quote_from_dict(raw: dict[str, Any]) -> OptionQuote:
    src = raw.get("source") or {}
    return OptionQuote(
        status=str(raw.get("status") or STATUS_OK),
        source=SourceMeta(
            provider=str(src.get("provider") or "sina_option"),
            upstream=str(src.get("upstream") or ""),
            cached=bool(src.get("cached")),
            fetched_at=src.get("fetched_at"),
            attempt=int(src.get("attempt") or 1),
            source_version=src.get("source_version"),
        ),
        as_of=raw.get("as_of"),
        warnings=list(raw.get("warnings") or []),
        error=raw.get("error"),
        symbol=raw.get("symbol"),
        name=raw.get("name"),
        underlying=raw.get("underlying"),
        exchange=raw.get("exchange"),
        option_type=raw.get("option_type"),
        strike=_num(raw.get("strike")),
        expiry=raw.get("expiry"),
        last=_num(raw.get("last")),
        open=_num(raw.get("open")),
        high=_num(raw.get("high")),
        low=_num(raw.get("low")),
        prev_close=_num(raw.get("prev_close")),
        change_pct=_num(raw.get("change_pct")),
        volume=_num(raw.get("volume")),
        amount=_num(raw.get("amount")),
        open_interest=_num(raw.get("open_interest")),
        bid1=_num(raw.get("bid1")),
        bid1_size=_num(raw.get("bid1_size")),
        ask1=_num(raw.get("ask1")),
        ask1_size=_num(raw.get("ask1_size")),
        greeks_source=raw.get("greeks_source"),
    )
