"""Keyless domestic futures HTTP provider (Sina daily/minute/L1).

Does not import AKShare. Does not use futures_zh_spot (schema-broken in Run 0).
Sina MA0/RB0 continuous is labelled upstream_sina_continuous, never as local
dominant_by_open_interest.
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from ..cache import CacheKey, MarketCache
from ..errors import InvalidSymbolError
from ..futures.continuous import select_dominant_contract
from ..futures.margin import CONTRACT_MULTIPLIER, calculate_theoretical_margin
from ..http import DISCLAIMER, USER_AGENT, HttpGet, default_http_get
from ..models import (
    STATUS_INVALID_REQUEST,
    STATUS_INVALID_SYMBOL,
    STATUS_OK,
    STATUS_PARTIAL,
    STATUS_SOURCE_UNAVAILABLE,
    FuturesQuote,
    MarginEstimate,
    OhlcBar,
    OhlcSeries,
    SourceMeta,
)
from ..symbols import CNFuturesSymbol, resolve_futures

Clock = Callable[[], datetime]

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
MINUTE_TYPE = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60"}
SERIES_METHODS = frozenset({"auto", "contract", "main", "main_continuous"})
L1_URL = (
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQFuturesData"
)
DAILY_URL = (
    "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_x=/"
    "InnerFuturesNewService.getDailyKLine"
)
MINUTE_URL = (
    "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/=/"
    "InnerFuturesNewService.getFewMinLine"
)
SINA_HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://finance.sina.com.cn/",
    "Accept": "*/*",
}


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
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("(")
        end = stripped.rfind(")")
        if start < 0 or end <= start:
            raise
        return json.loads(stripped[start + 1 : end])


def _row_ohlc(
    row: Any,
) -> Optional[tuple[str, OhlcBar, Optional[float], Optional[float], Optional[float]]]:
    if isinstance(row, dict):
        day = str(row.get("date") or row.get("d") or row.get("datetime") or row.get("day") or "")
        o = _num(row.get("open") or row.get("o"))
        h = _num(row.get("high") or row.get("h"))
        low = _num(row.get("low") or row.get("l"))
        c = _num(row.get("close") or row.get("c"))
        volume = _num(row.get("volume") or row.get("v"))
        hold = _num(row.get("hold") or row.get("hld") or row.get("open_interest"))
        settle = _num(row.get("settle") or row.get("s") or row.get("settlement"))
    elif isinstance(row, (list, tuple)) and len(row) >= 6:
        day = str(row[0] or "")
        o, h, low, c = _num(row[1]), _num(row[2]), _num(row[3]), _num(row[4])
        volume = _num(row[5])
        hold = _num(row[6]) if len(row) > 6 else None
        settle = _num(row[7]) if len(row) > 7 else None
    else:
        return None
    if not day or None in (o, h, low, c):
        return None
    assert o is not None and h is not None and low is not None and c is not None
    return day, OhlcBar(o=o, h=h, l=low, c=c), volume, hold, settle


def _slice_range(
    labels: list[str],
    ohlc: list[OhlcBar],
    volume: list[Optional[float]],
    open_interest: list[Optional[float]],
    settlement: list[Optional[float]],
    dominant: list[Optional[str]],
    chart_range: str,
    *,
    as_of: datetime,
) -> tuple[
    list[str],
    list[OhlcBar],
    list[Optional[float]],
    list[Optional[float]],
    list[Optional[float]],
    list[Optional[str]],
    str,
]:
    if chart_range == "ytd":
        start = f"{as_of.year:04d}-01-01"
        keep = [i for i, lab in enumerate(labels) if lab >= start]
        if not keep:
            return labels, ohlc, volume, open_interest, settlement, dominant, chart_range
        return (
            [labels[i] for i in keep],
            [ohlc[i] for i in keep],
            [volume[i] for i in keep],
            [open_interest[i] for i in keep],
            [settlement[i] for i in keep],
            [dominant[i] for i in keep],
            chart_range,
        )
    n = RANGE_BARS.get(chart_range, len(labels))
    if len(labels) <= n:
        return labels, ohlc, volume, open_interest, settlement, dominant, chart_range
    return (
        labels[-n:],
        ohlc[-n:],
        volume[-n:],
        open_interest[-n:],
        settlement[-n:],
        dominant[-n:],
        chart_range,
    )


class PublicCNFuturesProvider:
    name = "cn_futures_public"

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

    def _get(self, url: str) -> tuple[int, bytes]:
        return self._http_get(url, SINA_HEADERS)

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

    def _unavailable_quote(self, symbol: Optional[str], error: str) -> FuturesQuote:
        return FuturesQuote(
            status=STATUS_SOURCE_UNAVAILABLE,
            source=self._source("sina_futures_realtime", "getHQFuturesData"),
            symbol=symbol,
            error=error,
            warnings=[DISCLAIMER],
            market_depth="L1",
        )

    def _fetch_l1_rows(self, node: str) -> tuple[Optional[list[dict[str, Any]]], Optional[str]]:
        q = urllib.parse.urlencode(
            {"page": "1", "sort": "position", "asc": "0", "node": node, "base": "futures"}
        )
        url = L1_URL + "?" + q
        try:
            status, body = self._get(url)
        except Exception as exc:
            return None, str(exc)
        if status != 200:
            return None, f"HTTP {status}"
        try:
            payload = _parse_jsonish(_decode_text(body))
        except Exception:
            return None, "新浪期货 L1 无法解析"
        if payload is None:
            return None, "新浪期货 L1 为空"
        if not isinstance(payload, list):
            return None, "新浪期货 L1 不是列表"
        rows = [row for row in payload if isinstance(row, dict)]
        return rows, None

    def _resolve(self, query: str) -> CNFuturesSymbol | FuturesQuote:
        try:
            return resolve_futures(query)
        except InvalidSymbolError as exc:
            return FuturesQuote(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_futures_realtime", "getHQFuturesData"),
                error=str(exc),
                market_depth="L1",
            )

    def _pick_row(
        self,
        resolved: CNFuturesSymbol,
        rows: list[dict[str, Any]],
    ) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        if resolved.contract:
            want = resolved.contract.upper()
            for row in rows:
                if str(row.get("symbol") or "").strip().upper() == want:
                    return row, "contract"
            return None, "contract"
        row = select_dominant_contract(rows)
        return row, "dominant_by_open_interest"

    def _quote_from_row(
        self,
        resolved: CNFuturesSymbol,
        row: dict[str, Any],
        *,
        series_method: str,
    ) -> FuturesQuote:
        try:
            contract_sym = resolve_futures(str(row.get("symbol") or ""))
        except InvalidSymbolError:
            contract_sym = resolved
        last = _num(row.get("trade") or row.get("close"))
        prev = _num(row.get("presettlement") or row.get("preclose") or row.get("prevsettlement"))
        change = None
        change_pct = None
        if last is not None and prev not in (None, 0):
            change = last - prev
            change_pct = change / prev * 100.0
        quote = FuturesQuote(
            status=STATUS_OK,
            source=self._source("sina_futures_realtime", "getHQFuturesData"),
            as_of=str(row.get("ticktime") or row.get("time") or "") or None,
            warnings=[DISCLAIMER],
            symbol=contract_sym.canonical,
            name=str(row.get("name") or contract_sym.name),
            product=contract_sym.product,
            exchange=contract_sym.exchange,
            last=last,
            open=_num(row.get("open")),
            high=_num(row.get("high")),
            low=_num(row.get("low")),
            prev_settle=prev,
            settle=_num(row.get("settlement")),
            change=change,
            change_pct=change_pct,
            volume=_num(row.get("volume")),
            open_interest=_num(row.get("position") or row.get("open_interest")),
            bid1=_num(row.get("bidprice1") or row.get("bid")),
            bid1_size=_num(row.get("bidvol1")),
            ask1=_num(row.get("askprice1") or row.get("ask")),
            ask1_size=_num(row.get("askvol1")),
            market_depth="L1",
            series_method=series_method,
            contract_multiplier=CONTRACT_MULTIPLIER.get(contract_sym.product),
        )
        return quote

    def futures_quote(self, query: str) -> FuturesQuote:
        resolved = self._resolve(query)
        if isinstance(resolved, FuturesQuote):
            return resolved
        key = CacheKey(
            domain="futures",
            symbol=resolved.canonical,
            dataset="quote",
            source_version=resolved.sina_node,
        )
        cached = self._cache_get(key)
        if cached:
            cached["source"]["cached"] = True
            return _quote_from_dict(cached)
        rows, err = self._fetch_l1_rows(resolved.sina_node)
        if err or rows is None:
            return self._unavailable_quote(resolved.canonical, err or "L1 不可用")
        row, method = self._pick_row(resolved, rows)
        if row is None:
            return self._unavailable_quote(resolved.canonical, "未找到可交易合约")
        quote = self._quote_from_row(resolved, row, series_method=method or "contract")
        self._cache_put(key, quote.to_dict(), dataset_kind="quote")
        return quote

    def futures_l1(self, query: str) -> FuturesQuote:
        return self.futures_quote(query)

    def futures_daily(
        self,
        query: str,
        *,
        chart_range: str = "3mo",
        series: str = "auto",
    ) -> OhlcSeries:
        rng = (chart_range or "3mo").strip().lower()
        if rng not in ALLOWED_RANGES:
            return OhlcSeries(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_futures_daily", "getDailyKLine"),
                error=f"range 须为其一：{', '.join(sorted(ALLOWED_RANGES))}",
                warnings=[DISCLAIMER],
            )
        method = (series or "auto").strip().lower()
        if method not in SERIES_METHODS:
            return OhlcSeries(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_futures_daily", "getDailyKLine"),
                error="series 须为 auto / contract / main / main_continuous",
                warnings=[DISCLAIMER],
            )
        try:
            resolved = resolve_futures(query)
        except InvalidSymbolError as exc:
            return OhlcSeries(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_futures_daily", "getDailyKLine"),
                error=str(exc),
            )
        if method == "auto":
            method = "contract" if resolved.contract else "main"
        if method == "contract" and not resolved.contract:
            return OhlcSeries(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_futures_daily", "getDailyKLine"),
                error="series=contract 需要具体合约代码，例如 MA2509",
                warnings=[DISCLAIMER],
                symbol=resolved.canonical,
            )
        kline_code, series_method, dominant, extra_warnings = self._series_target(resolved, method)
        if kline_code is None:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_futures_daily", "getDailyKLine"),
                error=extra_warnings[-1] if extra_warnings else "无法确定合约",
                warnings=[DISCLAIMER],
                symbol=resolved.canonical,
                series_method=series_method,
            )
        key = CacheKey(
            domain="futures",
            symbol=f"{kline_code}.{resolved.exchange}",
            dataset="daily",
            interval="1d",
            adjustment="none",
            source_version=f"{series_method}:{rng}",
        )
        cached = self._cache_get(key)
        if cached:
            return OhlcSeries.from_dict(cached, cached=True)
        warnings = [DISCLAIMER, "期货日线按未复权（adjustment=none）返回"] + extra_warnings
        series_out = self._fetch_kline(
            kline_code,
            resolved,
            interval="1d",
            chart_range=rng,
            series_method=series_method,
            dominant=dominant,
            warnings=warnings,
            daily=True,
        )
        if series_out.status in {STATUS_OK, STATUS_PARTIAL}:
            self._cache_put(key, series_out.to_dict(), dataset_kind="daily")
        return series_out

    def futures_minute(self, query: str, *, interval: str = "5m", series: str = "auto") -> OhlcSeries:
        iv = (interval or "5m").strip().lower()
        if iv not in MINUTE_TYPE:
            return OhlcSeries(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_futures_minute", "getFewMinLine"),
                error=f"interval 须为其一：{', '.join(sorted(MINUTE_TYPE))}",
                warnings=[DISCLAIMER],
            )
        method = (series or "auto").strip().lower()
        if method not in SERIES_METHODS:
            return OhlcSeries(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_futures_minute", "getFewMinLine"),
                error="series 须为 auto / contract / main / main_continuous",
                warnings=[DISCLAIMER],
            )
        try:
            resolved = resolve_futures(query)
        except InvalidSymbolError as exc:
            return OhlcSeries(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_futures_minute", "getFewMinLine"),
                error=str(exc),
            )
        if method == "auto":
            method = "contract" if resolved.contract else "main"
        kline_code, series_method, dominant, extra_warnings = self._series_target(resolved, method)
        if kline_code is None:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_futures_minute", "getFewMinLine"),
                error="无法确定分钟线合约",
                warnings=[DISCLAIMER],
                symbol=resolved.canonical,
            )
        key = CacheKey(
            domain="futures",
            symbol=f"{kline_code}.{resolved.exchange}",
            dataset="minute",
            interval=iv,
            source_version=series_method,
        )
        cached = self._cache_get(key)
        if cached:
            return OhlcSeries.from_dict(cached, cached=True)
        warnings = [DISCLAIMER, "分钟线历史深度受上游限制"] + extra_warnings
        series_out = self._fetch_kline(
            kline_code,
            resolved,
            interval=iv,
            chart_range="session",
            series_method=series_method,
            dominant=dominant,
            warnings=warnings,
            daily=False,
            minute_type=MINUTE_TYPE[iv],
        )
        if series_out.status in {STATUS_OK, STATUS_PARTIAL}:
            self._cache_put(key, series_out.to_dict(), dataset_kind="minute")
        return series_out

    def _series_target(
        self, resolved: CNFuturesSymbol, method: str
    ) -> tuple[Optional[str], str, Optional[str], list[str]]:
        if method == "main_continuous":
            return (
                resolved.sina_continuous,
                "upstream_sina_continuous",
                None,
                ["新浪连续代码（如 MA0）是上游连续，不是本地按持仓量拼接的主力连续"],
            )
        if method == "contract":
            return resolved.sina_kline, "contract", resolved.contract, []
        # main = current dominant contract's own history (not spliced)
        rows, err = self._fetch_l1_rows(resolved.sina_node)
        if err or rows is None:
            return None, "dominant_by_open_interest", None, [err or "L1 不可用"]
        if resolved.contract:
            row = None
            want = resolved.contract.upper()
            for item in rows:
                if str(item.get("symbol") or "").strip().upper() == want:
                    row = item
                    break
            if row is None:
                return None, "contract", resolved.contract, ["指定合约不在当前 L1 列表"]
            try:
                picked = resolve_futures(str(row.get("symbol")))
            except InvalidSymbolError:
                picked = resolved
            return picked.sina_kline, "contract", picked.contract, []
        row = select_dominant_contract(rows)
        if row is None:
            return None, "dominant_by_open_interest", None, ["无有效主力合约"]
        try:
            picked = resolve_futures(str(row.get("symbol")))
        except InvalidSymbolError:
            return None, "dominant_by_open_interest", None, ["主力合约代码无法解析"]
        return (
            picked.sina_kline,
            "dominant_by_open_interest",
            picked.contract,
            ["主力连续一期基线：当前主力合约自身日线，未做换月拼接（roll_count=0）"],
        )

    def _fetch_kline(
        self,
        kline_code: str,
        resolved: CNFuturesSymbol,
        *,
        interval: str,
        chart_range: str,
        series_method: str,
        dominant: Optional[str],
        warnings: list[str],
        daily: bool,
        minute_type: str = "5",
    ) -> OhlcSeries:
        if daily:
            q = urllib.parse.urlencode({"symbol": kline_code, "type": "2021_4_12"})
            url = DAILY_URL + "?" + q
            upstream = "getDailyKLine"
            provider = "sina_futures_daily"
        else:
            q = urllib.parse.urlencode({"symbol": kline_code, "type": minute_type})
            url = MINUTE_URL + "?" + q
            upstream = "getFewMinLine"
            provider = "sina_futures_minute"
        display = f"{kline_code.upper() if resolved.exchange == 'CZCE' else kline_code}.{resolved.exchange}"
        if series_method == "dominant_by_open_interest" and dominant:
            display = f"{dominant}.{resolved.exchange}"
        elif series_method == "contract" and resolved.contract:
            display = resolved.canonical
        try:
            status, body = self._get(url)
        except Exception as exc:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source(provider, upstream),
                symbol=display,
                error=str(exc),
                warnings=warnings,
                series_method=series_method,
            )
        if status != 200:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source(provider, upstream),
                symbol=display,
                error=f"HTTP {status}",
                warnings=warnings,
                series_method=series_method,
            )
        try:
            rows = _parse_jsonish(_decode_text(body))
        except Exception:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source(provider, upstream),
                symbol=display,
                error="期货 K 线 JSONP 无法解析",
                warnings=warnings,
                series_method=series_method,
            )
        if not isinstance(rows, list):
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source(provider, upstream),
                symbol=display,
                error="期货 K 线响应不是列表",
                warnings=warnings,
                series_method=series_method,
            )
        labels: list[str] = []
        ohlc: list[OhlcBar] = []
        volume: list[Optional[float]] = []
        open_interest: list[Optional[float]] = []
        settlement: list[Optional[float]] = []
        skipped = 0
        for row in rows:
            parsed = _row_ohlc(row)
            if parsed is None:
                skipped += 1
                continue
            day, bar, vol, hold, settle = parsed
            labels.append(day[:19] if not daily else day[:10])
            ohlc.append(bar)
            volume.append(vol)
            open_interest.append(hold)
            settlement.append(settle)
        if len(ohlc) < 2:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source(provider, upstream),
                symbol=display,
                error="可用 OHLC 点数不足（需要 ≥2）",
                warnings=warnings + ([f"跳过 {skipped} 根空 OHLC"] if skipped else []),
                series_method=series_method,
            )
        dominant_list: list[Optional[str]] = [dominant] * len(labels)
        actual = chart_range
        if daily and chart_range in ALLOWED_RANGES:
            labels, ohlc, volume, open_interest, settlement, dominant_list, actual = _slice_range(
                labels,
                ohlc,
                volume,
                open_interest,
                settlement,
                dominant_list,
                chart_range,
                as_of=self._clock(),
            )
        status_out = STATUS_PARTIAL if skipped else STATUS_OK
        if skipped:
            warnings = warnings + [f"有 {skipped} 根 OHLC 为空已跳过"]
        roll_count = 0 if series_method == "dominant_by_open_interest" else None
        return OhlcSeries(
            status=status_out,
            source=self._source(provider, upstream),
            as_of=labels[-1] if labels else None,
            warnings=warnings,
            labels=labels,
            ohlc=ohlc,
            volume=volume,
            open_interest=open_interest,
            settlement=settlement,
            dominant_contract=dominant_list,
            adjustment="none",
            symbol=display,
            interval=interval,
            actual_range=actual,
            series_method=series_method,
            roll_count=roll_count,
            name=resolved.name,
            aliases=list(resolved.aliases),
        )

    def futures_margin(
        self,
        query: str,
        *,
        lots: Any,
        price: Any = None,
        multiplier: Any = None,
        margin_rate: Any = None,
    ) -> MarginEstimate:
        try:
            resolved = resolve_futures(query)
        except InvalidSymbolError as exc:
            return MarginEstimate(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("local_formula", "none"),
                error=str(exc),
                estimate_kind="theoretical",
            )
        if multiplier is None:
            multiplier = CONTRACT_MULTIPLIER.get(resolved.product)
        if price is None:
            quote = self.futures_quote(query)
            if quote.status == STATUS_OK:
                price = quote.last
        return calculate_theoretical_margin(
            price=price,
            multiplier=multiplier,
            margin_rate=margin_rate,
            lots=lots,
            symbol=resolved.canonical,
        )


def _quote_from_dict(raw: dict[str, Any]) -> FuturesQuote:
    src = raw.get("source") or {}
    return FuturesQuote(
        status=str(raw.get("status") or STATUS_OK),
        source=SourceMeta(
            provider=str(src.get("provider") or "sina_futures_realtime"),
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
        product=raw.get("product"),
        exchange=raw.get("exchange"),
        last=_num(raw.get("last")),
        open=_num(raw.get("open")),
        high=_num(raw.get("high")),
        low=_num(raw.get("low")),
        prev_settle=_num(raw.get("prev_settle")),
        settle=_num(raw.get("settle")),
        change=_num(raw.get("change")),
        change_pct=_num(raw.get("change_pct")),
        volume=_num(raw.get("volume")),
        open_interest=_num(raw.get("open_interest")),
        bid1=_num(raw.get("bid1")),
        bid1_size=_num(raw.get("bid1_size")),
        ask1=_num(raw.get("ask1")),
        ask1_size=_num(raw.get("ask1_size")),
        market_depth=str(raw.get("market_depth") or "L1"),
        series_method=raw.get("series_method"),
        contract_multiplier=_num(raw.get("contract_multiplier")),
    )
