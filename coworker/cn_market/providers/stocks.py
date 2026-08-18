"""Keyless A-share HTTP provider (Sina quote/K-line/financials, EM LHB/HSGT, SSE margin).

Does not import AKShare. Eastmoney spot/hist are not used (Run 0 unstable).
Sina compressed klc_kl.js is not used (needs V8); daily bars use the same
CN_MarketDataService JSONP as minutes.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Callable, Optional

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
    FinancialBundle,
    FinancialStatement,
    OhlcBar,
    OhlcSeries,
    REPORT_KIND_AUDITED,
    REPORT_KIND_EXPRESS,
    REPORT_KIND_FORECAST,
    STATEMENT_BALANCE_SHEET,
    STATEMENT_CASH_FLOW,
    STATEMENT_FORECAST,
    STATEMENT_EXPRESS,
    STATEMENT_INCOME,
    SourceMeta,
    StockQuote,
)
from ..source_policy import policy_for
from ..symbols import resolve_stock

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
MINUTE_SCALE = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60"}
STATEMENT_SOURCE = {
    STATEMENT_BALANCE_SHEET: "fzb",
    STATEMENT_INCOME: "lrb",
    STATEMENT_CASH_FLOW: "llb",
}
FEATURE_SUPPORTED = frozenset(
    {
        "lhb_list",
        "lhb_detail",
        "margin_summary",
        "northbound_history",
        "northbound_holdings",
        "performance_forecast",
        "performance_express",
        "financial_indicators",
    }
)

_HQ_RE = re.compile(r'hq_str_[a-z]{2}\d{6}="([^"]*)"')


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


def _parse_jsonp(text: str) -> Any:
    start = text.find("(")
    end = text.rfind(")")
    if start < 0 or end <= start:
        raise ValueError("not jsonp")
    return json.loads(text[start + 1 : end])


def _slice_range(
    labels: list[str],
    ohlc: list[OhlcBar],
    volume: list[Optional[float]],
    amount: list[Optional[float]],
    chart_range: str,
    *,
    as_of: datetime,
) -> tuple[list[str], list[OhlcBar], list[Optional[float]], list[Optional[float]], str]:
    if chart_range == "ytd":
        start = f"{as_of.year:04d}-01-01"
        keep = [i for i, lab in enumerate(labels) if lab >= start]
        if not keep:
            return labels, ohlc, volume, amount, chart_range
        idx = keep
        return (
            [labels[i] for i in idx],
            [ohlc[i] for i in idx],
            [volume[i] if i < len(volume) else None for i in idx],
            [amount[i] if i < len(amount) else None for i in idx],
            chart_range,
        )
    n = RANGE_BARS.get(chart_range, len(labels))
    if len(labels) <= n:
        return labels, ohlc, volume, amount, chart_range
    return labels[-n:], ohlc[-n:], volume[-n:], amount[-n:] if amount else [], chart_range


class PublicCNStockProvider:
    name = "cn_stock_public"

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
            source_version="1",
        )

    def _get(self, url: str, headers: Optional[dict[str, str]] = None) -> tuple[int, bytes]:
        return self._http_get(url, headers)

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

    def stock_quote(self, query: str) -> StockQuote:
        try:
            symbol = resolve_stock(query)
        except InvalidSymbolError as exc:
            return StockQuote(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_hq", "hq.sinajs.cn"),
                error=str(exc),
            )
        key = CacheKey(domain="stock", symbol=symbol.canonical, dataset="quote")
        cached = self._cache_get(key)
        if cached:
            cached["source"]["cached"] = True
            return _quote_from_dict(cached)
        url = "https://hq.sinajs.cn/list=" + urllib.parse.quote(symbol.sina_code)
        try:
            status, body = self._get(
                url,
                {
                    "User-Agent": USER_AGENT,
                    "Referer": "https://finance.sina.com.cn/",
                    "Accept": "*/*",
                },
            )
        except Exception as exc:
            return StockQuote(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_hq", "hq.sinajs.cn"),
                symbol=symbol.canonical,
                error=str(exc),
                warnings=[DISCLAIMER],
            )
        if status != 200:
            return StockQuote(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_hq", "hq.sinajs.cn"),
                symbol=symbol.canonical,
                error=f"HTTP {status}",
                warnings=[DISCLAIMER],
            )
        text = _decode_text(body)
        match = _HQ_RE.search(text)
        if not match:
            return StockQuote(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_hq", "hq.sinajs.cn"),
                symbol=symbol.canonical,
                error="新浪行情格式无法解析",
                warnings=[DISCLAIMER],
            )
        parts = match.group(1).split(",")
        if len(parts) < 10:
            return StockQuote(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_hq", "hq.sinajs.cn"),
                symbol=symbol.canonical,
                error="新浪行情字段不足",
                warnings=[DISCLAIMER],
            )
        open_px = _num(parts[1])
        prev = _num(parts[2])
        last = _num(parts[3])
        high = _num(parts[4])
        low = _num(parts[5])
        bid1 = _num(parts[6])
        ask1 = _num(parts[7])
        volume = _num(parts[8])
        amount = _num(parts[9])
        change = None
        change_pct = None
        if last is not None and prev not in (None, 0):
            change = last - prev
            change_pct = change / prev * 100.0
        as_of = None
        if len(parts) > 31:
            as_of = f"{parts[30]} {parts[31]}".strip()
        elif len(parts) > 30:
            as_of = parts[30]
        quote = StockQuote(
            status=STATUS_OK,
            source=self._source("sina_hq", "hq.sinajs.cn"),
            as_of=as_of,
            warnings=[DISCLAIMER],
            symbol=symbol.canonical,
            name=parts[0] or symbol.name,
            last=last,
            open=open_px,
            high=high,
            low=low,
            prev_close=prev,
            change=change,
            change_pct=change_pct,
            volume=volume,
            amount=amount,
            bid1=bid1,
            ask1=ask1,
        )
        self._cache_put(key, quote.to_dict(), dataset_kind="quote")
        return quote

    def stock_daily(
        self,
        query: str,
        *,
        chart_range: str = "3mo",
        adjustment: str = "qfq",
    ) -> OhlcSeries:
        adj = (adjustment or "none").strip().lower()
        if adj in {"", "nadj", "unadjusted"}:
            adj = "none"
        if adj not in {"none", "qfq", "hfq"}:
            return OhlcSeries(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_kline", "quotes.sina.cn"),
                error="adjustment 须为 none / qfq / hfq",
                warnings=[DISCLAIMER],
            )
        rng = (chart_range or "3mo").strip().lower()
        if rng not in ALLOWED_RANGES:
            return OhlcSeries(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_kline", "quotes.sina.cn"),
                error=f"range 须为其一：{', '.join(sorted(ALLOWED_RANGES))}",
                warnings=[DISCLAIMER],
            )
        try:
            symbol = resolve_stock(query)
        except InvalidSymbolError as exc:
            return OhlcSeries(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_kline", "quotes.sina.cn"),
                error=str(exc),
            )
        if adj != "none":
            # JSONP K-line is unadjusted; do not silently fake qfq/hfq without factor table.
            warnings = [
                DISCLAIMER,
                f"当前新浪 JSONP K 线仅提供未复权；已按 none 返回（请求曾为 {adj}）",
            ]
            adj = "none"
        else:
            warnings = [DISCLAIMER]
        key = CacheKey(
            domain="stock",
            symbol=symbol.canonical,
            dataset="daily",
            interval="1d",
            adjustment=adj,
            source_version=f"sina-kline:{rng}",
        )
        cached = self._cache_get(key)
        if cached:
            return OhlcSeries.from_dict(cached, cached=True)
        series = self._fetch_kline(
            symbol,
            scale="240",
            interval="1d",
            chart_range=rng,
            adjustment=adj,
            warnings=warnings,
        )
        if series.status == STATUS_OK:
            self._cache_put(key, series.to_dict(), dataset_kind="daily")
        return series

    def stock_minute(self, query: str, *, interval: str = "5m") -> OhlcSeries:
        iv = (interval or "5m").strip().lower()
        if iv not in MINUTE_SCALE:
            return OhlcSeries(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_kline", "quotes.sina.cn"),
                error=f"interval 须为其一：{', '.join(sorted(MINUTE_SCALE))}",
                warnings=[DISCLAIMER],
            )
        try:
            symbol = resolve_stock(query)
        except InvalidSymbolError as exc:
            return OhlcSeries(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_kline", "quotes.sina.cn"),
                error=str(exc),
            )
        key = CacheKey(
            domain="stock",
            symbol=symbol.canonical,
            dataset="minute",
            interval=iv,
            source_version="sina-kline",
        )
        cached = self._cache_get(key)
        if cached:
            return OhlcSeries.from_dict(cached, cached=True)
        series = self._fetch_kline(
            symbol,
            scale=MINUTE_SCALE[iv],
            interval=iv,
            chart_range="session",
            adjustment="none",
            warnings=[DISCLAIMER, "分钟线历史深度受上游 datalen 限制"],
        )
        if series.status in {STATUS_OK, STATUS_PARTIAL}:
            self._cache_put(key, series.to_dict(), dataset_kind="minute")
        return series

    def _fetch_kline(
        self,
        symbol,
        *,
        scale: str,
        interval: str,
        chart_range: str,
        adjustment: str,
        warnings: list[str],
    ) -> OhlcSeries:
        datalen = "1023" if scale == "240" else "480"
        q = urllib.parse.urlencode(
            {
                "symbol": symbol.sina_code,
                "scale": scale,
                "ma": "no",
                "datalen": datalen,
            }
        )
        url = (
            "https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketDataService.getKLineData?"
            + q
        )
        try:
            status, body = self._get(url, {"User-Agent": USER_AGENT, "Accept": "*/*"})
        except Exception as exc:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_kline", "quotes.sina.cn"),
                symbol=symbol.canonical,
                error=str(exc),
                warnings=warnings,
            )
        if status != 200:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_kline", "quotes.sina.cn"),
                symbol=symbol.canonical,
                error=f"HTTP {status}",
                warnings=warnings,
            )
        try:
            rows = _parse_jsonp(_decode_text(body))
        except Exception:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_kline", "quotes.sina.cn"),
                symbol=symbol.canonical,
                error="K 线 JSONP 无法解析",
                warnings=warnings,
            )
        if not isinstance(rows, list):
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_kline", "quotes.sina.cn"),
                symbol=symbol.canonical,
                error="K 线响应不是列表",
                warnings=warnings,
            )
        labels: list[str] = []
        ohlc: list[OhlcBar] = []
        volume: list[Optional[float]] = []
        amount: list[Optional[float]] = []
        nan_ohlc = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            day = str(row.get("day") or row.get("date") or "")
            o, h, l, c = _num(row.get("open")), _num(row.get("high")), _num(row.get("low")), _num(
                row.get("close")
            )
            if not day:
                continue
            if None in (o, h, l, c):
                nan_ohlc += 1
                continue
            labels.append(day[:19] if interval != "1d" else day[:10])
            ohlc.append(OhlcBar(o=o, h=h, l=l, c=c))
            volume.append(_num(row.get("volume")))
            amount.append(_num(row.get("amount")))
        if len(ohlc) < 2:
            return OhlcSeries(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_kline", "quotes.sina.cn"),
                symbol=symbol.canonical,
                error="可用 OHLC 点数不足（需要 ≥2）",
                warnings=warnings + ([f"跳过 {nan_ohlc} 根空 OHLC"] if nan_ohlc else []),
            )
        if chart_range in ALLOWED_RANGES:
            labels, ohlc, volume, amount, actual = _slice_range(
                labels, ohlc, volume, amount, chart_range, as_of=self._clock()
            )
        else:
            actual = chart_range
        status_out = STATUS_PARTIAL if nan_ohlc else STATUS_OK
        if nan_ohlc:
            warnings = warnings + [f"有 {nan_ohlc} 根分钟/日线 OHLC 为空已跳过"]
        return OhlcSeries(
            status=status_out,
            source=self._source("sina_kline", "quotes.sina.cn"),
            as_of=labels[-1],
            warnings=warnings,
            labels=labels,
            ohlc=ohlc,
            volume=volume,
            amount=amount,
            adjustment=adjustment,
            symbol=symbol.canonical,
            interval=interval,
            actual_range=actual,
            name=symbol.name,
        )

    def stock_financials(
        self,
        query: str,
        *,
        statement_type: str = STATEMENT_BALANCE_SHEET,
    ) -> FinancialBundle:
        kind = (statement_type or STATEMENT_BALANCE_SHEET).strip()
        if kind == "financial_indicators":
            return FinancialBundle(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("eastmoney_indicator", "data.eastmoney.com"),
                error="财务分析指标接口在 Run 0 验证失败，未接入",
                warnings=[DISCLAIMER],
                statement_type=kind,
            )
        if kind not in STATEMENT_SOURCE:
            return FinancialBundle(
                status=STATUS_INVALID_REQUEST,
                source=self._source("sina_report", "quotes.sina.cn"),
                error="statement_type 须为 balance_sheet / income_statement / cash_flow",
                statement_type=kind,
                warnings=[DISCLAIMER],
            )
        try:
            symbol = resolve_stock(query)
        except InvalidSymbolError as exc:
            return FinancialBundle(
                status=STATUS_INVALID_SYMBOL,
                source=self._source("sina_report", "quotes.sina.cn"),
                error=str(exc),
                statement_type=kind,
            )
        key = CacheKey(
            domain="stock",
            symbol=symbol.canonical,
            dataset=f"financials:{kind}",
            source_version="sina-report-2022",
        )
        cached = self._cache_get(key)
        if cached:
            return _bundle_from_dict(cached, cached=True)
        q = urllib.parse.urlencode(
            {
                "paperCode": symbol.sina_code,
                "source": STATEMENT_SOURCE[kind],
                "type": "0",
                "page": "1",
                "num": "8",
            }
        )
        url = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022?" + q
        try:
            status, body = self._get(url, {"User-Agent": USER_AGENT, "Accept": "application/json"})
        except Exception as exc:
            return FinancialBundle(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_report", "quotes.sina.cn"),
                symbol=symbol.canonical,
                statement_type=kind,
                error=str(exc),
                warnings=[DISCLAIMER],
            )
        if status != 200:
            return FinancialBundle(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_report", "quotes.sina.cn"),
                symbol=symbol.canonical,
                statement_type=kind,
                error=f"HTTP {status}",
                warnings=[DISCLAIMER],
            )
        try:
            payload = json.loads(_decode_text(body))
            data = (((payload or {}).get("result") or {}).get("data")) or {}
            dates = [str(x.get("date_value")) for x in (data.get("report_date") or []) if x]
            report_list = data.get("report_list") or {}
        except Exception:
            return FinancialBundle(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_report", "quotes.sina.cn"),
                symbol=symbol.canonical,
                statement_type=kind,
                error="财务报表 JSON 无法解析",
                warnings=[DISCLAIMER],
            )
        statements: list[FinancialStatement] = []
        for period in dates:
            block = report_list.get(period) or {}
            items = block.get("data") or []
            fields: dict[str, Any] = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("item_title") or "").strip()
                if not title:
                    continue
                fields[title] = _num(item.get("item_value"))
            audited = str(block.get("is_audit") or "") in {"1", "true", "True"}
            statements.append(
                FinancialStatement(
                    status=STATUS_OK,
                    source=self._source("sina_report", "quotes.sina.cn"),
                    as_of=str(block.get("publish_date") or period),
                    warnings=[DISCLAIMER],
                    symbol=symbol.canonical,
                    report_period=period,
                    publish_date=str(block.get("publish_date") or "") or None,
                    statement_type=kind,
                    report_kind=REPORT_KIND_AUDITED if audited else REPORT_KIND_EXPRESS,
                    currency=str(block.get("rCurrency") or "CNY"),
                    fields=fields,
                    raw_fields={
                        "data_source": block.get("data_source"),
                        "rType": block.get("rType"),
                    },
                )
            )
        if len(statements) < 1:
            return FinancialBundle(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sina_report", "quotes.sina.cn"),
                symbol=symbol.canonical,
                statement_type=kind,
                error="无报表期",
                warnings=[DISCLAIMER],
            )
        status_out = STATUS_OK if len(statements) >= 2 else STATUS_PARTIAL
        bundle = FinancialBundle(
            status=status_out,
            source=self._source("sina_report", "quotes.sina.cn"),
            as_of=statements[-1].report_period,
            warnings=[DISCLAIMER],
            symbol=symbol.canonical,
            statement_type=kind,
            statements=statements,
        )
        self._cache_put(key, bundle.to_dict(), dataset_kind="statement")
        return bundle

    def stock_feature(
        self,
        dataset: str,
        *,
        symbol: Optional[str] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> FeatureTable:
        name = (dataset or "").strip()
        if name not in FEATURE_SUPPORTED:
            return FeatureTable(
                status=STATUS_UNSUPPORTED,
                source=self._source("none", ""),
                dataset=name,
                error=f"dataset 未实现或 Run 0 未验证：{name}",
                warnings=[DISCLAIMER],
            )
        if name == "northbound_holdings":
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("eastmoney_hsgt", "datacenter-web.eastmoney.com"),
                dataset=name,
                error="北向持股排行在 Run 0 验证失败，未接入替代源",
                warnings=[DISCLAIMER],
            )
        if name == "financial_indicators":
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("eastmoney_indicator", "data.eastmoney.com"),
                dataset=name,
                error="财务分析指标接口在 Run 0 验证失败，未接入",
                warnings=[DISCLAIMER],
            )
        if name in {"lhb_list", "lhb_detail"}:
            return self._lhb(name, symbol=symbol, start_date=start_date, end_date=end_date)
        if name == "margin_summary":
            return self._margin(start_date=start_date, end_date=end_date)
        if name == "northbound_history":
            return self._hsgt()
        if name == "performance_forecast":
            return self._performance("forecast", start_date=end_date or start_date)
        if name == "performance_express":
            return self._performance("express", start_date=end_date or start_date)
        return FeatureTable(
            status=STATUS_UNSUPPORTED,
            source=self._source("none", ""),
            dataset=name,
            error="unhandled dataset",
        )

    def _lhb(
        self,
        dataset: str,
        *,
        symbol: Optional[str],
        start_date: str,
        end_date: str,
    ) -> FeatureTable:
        start = _iso_date(start_date or "20260801")
        end = _iso_date(end_date or start_date or "20260815")
        filt = f"(TRADE_DATE<='{end}')(TRADE_DATE>='{start}')"
        if symbol:
            try:
                resolved = resolve_stock(symbol)
                filt += f'(SECURITY_CODE="{resolved.code}")'
            except InvalidSymbolError as exc:
                return FeatureTable(
                    status=STATUS_INVALID_SYMBOL,
                    source=self._source("eastmoney_lhb", "datacenter-web.eastmoney.com"),
                    dataset=dataset,
                    error=str(exc),
                )
        q = urllib.parse.urlencode(
            {
                "sortColumns": "SECURITY_CODE,TRADE_DATE",
                "sortTypes": "1,-1",
                "pageSize": "200",
                "pageNumber": "1",
                "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
                "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,CLOSE_PRICE,CHANGE_RATE,"
                "BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,EXPLANATION",
                "source": "WEB",
                "client": "WEB",
                "filter": filt,
            }
        )
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get?" + q
        rows, err = self._em_rows(url)
        if err:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("eastmoney_lhb", "datacenter-web.eastmoney.com"),
                dataset=dataset,
                error=err,
                warnings=[DISCLAIMER],
            )
        out = []
        for raw in rows:
            out.append(
                {
                    "code": str(raw.get("SECURITY_CODE") or ""),
                    "name": raw.get("SECURITY_NAME_ABBR"),
                    "trade_date": str(raw.get("TRADE_DATE") or "")[:10],
                    "close": _num(raw.get("CLOSE_PRICE")),
                    "change_pct": _num(raw.get("CHANGE_RATE")),
                    "net_buy": _num(raw.get("BILLBOARD_NET_AMT")),
                    "buy": _num(raw.get("BILLBOARD_BUY_AMT")),
                    "sell": _num(raw.get("BILLBOARD_SELL_AMT")),
                    "reason": raw.get("EXPLANATION"),
                }
            )
        return FeatureTable(
            status=STATUS_OK,
            source=self._source("eastmoney_lhb", "datacenter-web.eastmoney.com"),
            warnings=[DISCLAIMER, "仅第一页，最多 200 条"],
            dataset=dataset,
            rows=out,
        )

    def _margin(self, *, start_date: str, end_date: str) -> FeatureTable:
        start = (start_date or "20260801").replace("-", "")
        end = (end_date or start or "20260815").replace("-", "")
        q = urllib.parse.urlencode(
            {
                "isPagination": "true",
                "beginDate": start,
                "endDate": end,
                "tabType": "",
                "stockCode": "",
                "pageHelp.pageSize": "50",
                "pageHelp.pageNo": "1",
                "pageHelp.beginPage": "1",
                "pageHelp.cacheSize": "1",
                "pageHelp.endPage": "1",
            }
        )
        url = "https://query.sse.com.cn/marketdata/tradedata/queryMargin.do?" + q
        try:
            status, body = self._get(
                url,
                {
                    "User-Agent": USER_AGENT,
                    "Referer": "https://www.sse.com.cn/",
                    "Accept": "application/json,text/plain,*/*",
                },
            )
        except Exception as exc:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sse_margin", "query.sse.com.cn"),
                dataset="margin_summary",
                error=str(exc),
                warnings=[DISCLAIMER],
            )
        if status != 200:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sse_margin", "query.sse.com.cn"),
                dataset="margin_summary",
                error=f"HTTP {status}",
                warnings=[DISCLAIMER],
            )
        try:
            payload = json.loads(_decode_text(body))
            raw_rows = payload.get("result") or []
        except Exception:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sse_margin", "query.sse.com.cn"),
                dataset="margin_summary",
                error="两融 JSON 无法解析",
                warnings=[DISCLAIMER],
            )
        out = []
        for raw in raw_rows:
            if not isinstance(raw, dict):
                continue
            out.append(
                {
                    "trade_date": str(
                        raw.get("opDate") or raw.get("creditTradeDate") or raw.get("rzrqjyrq") or ""
                    ),
                    "margin_balance": _num(raw.get("rzye") or raw.get("rzje")),
                    "margin_buy": _num(raw.get("rzmre")),
                    "short_volume": _num(raw.get("rqyl")),
                    "short_amount": _num(raw.get("rqylje")),
                    "short_sell": _num(raw.get("rqmcl")),
                    "margin_short_balance": _num(raw.get("rzrqye")),
                }
            )
        if not out:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("sse_margin", "query.sse.com.cn"),
                dataset="margin_summary",
                error="两融汇总为空（可能非交易日或上游改版）",
                warnings=[DISCLAIMER],
            )
        return FeatureTable(
            status=STATUS_OK,
            source=self._source("sse_margin", "query.sse.com.cn"),
            warnings=[DISCLAIMER, "上证市场汇总；深证明细未接入（Run 0 UNSTABLE）"],
            dataset="margin_summary",
            rows=out,
        )

    def _hsgt(self) -> FeatureTable:
        q = urllib.parse.urlencode(
            {
                "sortColumns": "TRADE_DATE",
                "sortTypes": "-1",
                "pageSize": "20",
                "pageNumber": "1",
                "reportName": "RPT_MUTUAL_DEAL_HISTORY",
                "columns": "ALL",
                "source": "WEB",
                "client": "WEB",
                "filter": '(MUTUAL_TYPE="005")',
            }
        )
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get?" + q
        rows, err = self._em_rows(url)
        if err:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("eastmoney_hsgt", "datacenter-web.eastmoney.com"),
                dataset="northbound_history",
                error=err,
                warnings=[DISCLAIMER],
            )
        out = []
        missing = 0
        for raw in rows:
            net = _num(raw.get("NET_DEAL_AMT"))
            if net is None:
                missing += 1
            out.append(
                {
                    "trade_date": str(raw.get("TRADE_DATE") or "")[:10],
                    "net_deal": net,
                    "buy": _num(raw.get("BUY_AMT")),
                    "sell": _num(raw.get("SELL_AMT")),
                    "inflow": _num(raw.get("FUND_INFLOW")),
                    "lead_stock": raw.get("LEAD_STOCKS_NAME"),
                    "lead_change_pct": _num(raw.get("LS_CHANGE_RATE")),
                    "hold_cap": _num(raw.get("HOLD_MARKET_CAP")),
                }
            )
        status = STATUS_PARTIAL if missing else STATUS_OK
        warnings = [DISCLAIMER, "北向历史金额字段可能为空，不得当作实时分钟资金流"]
        if missing:
            warnings.append(f"{missing} 行净买额为空")
        return FeatureTable(
            status=status,
            source=self._source("eastmoney_hsgt", "datacenter-web.eastmoney.com"),
            warnings=warnings,
            dataset="northbound_history",
            rows=out,
        )

    def _performance(self, kind: str, *, start_date: str) -> FeatureTable:
        report = "RPT_PUBLIC_OP_NEWPREDICT" if kind == "forecast" else "RPT_FCI_PERFORMANCEE"
        date = (start_date or "20250331").replace("-", "")
        if len(date) == 8:
            report_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        else:
            report_date = "2025-03-31"
        filt = f"(REPORT_DATE='{report_date}')"
        q = urllib.parse.urlencode(
            {
                "sortColumns": "NOTICE_DATE,SECURITY_CODE",
                "sortTypes": "-1,-1",
                "pageSize": "50",
                "pageNumber": "1",
                "reportName": report,
                "columns": "ALL",
                "filter": filt,
            }
        )
        host = (
            "https://datacenter.eastmoney.com/securities/api/data/v1/get?"
            if kind == "express"
            else "https://datacenter-web.eastmoney.com/api/data/v1/get?"
        )
        rows, err = self._em_rows(host + q)
        if err:
            return FeatureTable(
                status=STATUS_SOURCE_UNAVAILABLE,
                source=self._source("eastmoney_bbsj", "data.eastmoney.com"),
                dataset="performance_" + kind,
                error=err,
                warnings=[DISCLAIMER],
            )
        out = []
        for raw in rows:
            out.append(
                {
                    "code": str(raw.get("SECURITY_CODE") or ""),
                    "name": raw.get("SECURITY_NAME_ABBR"),
                    "notice_date": str(raw.get("NOTICE_DATE") or "")[:10],
                    "report_kind": REPORT_KIND_FORECAST if kind == "forecast" else REPORT_KIND_EXPRESS,
                    "metric": raw.get("PREDICT_FINANCE") or raw.get("BASIC_EPS"),
                }
            )
        return FeatureTable(
            status=STATUS_OK,
            source=self._source("eastmoney_bbsj", "data.eastmoney.com"),
            warnings=[DISCLAIMER, "仅第一页"],
            dataset="performance_" + kind,
            rows=out,
        )

    def _em_rows(self, url: str) -> tuple[list[dict[str, Any]], Optional[str]]:
        try:
            status, body = self._get(url, {"User-Agent": USER_AGENT, "Accept": "application/json"})
        except Exception as exc:
            return [], str(exc)
        if status != 200:
            return [], f"HTTP {status}"
        try:
            payload = json.loads(_decode_text(body))
            data = ((payload or {}).get("result") or {}).get("data") or []
            if not isinstance(data, list):
                return [], "result.data 不是列表"
            return [x for x in data if isinstance(x, dict)], None
        except Exception:
            return [], "JSON 无法解析"


def _iso_date(value: str) -> str:
    raw = (value or "").replace("-", "")
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return value


def _quote_from_dict(raw: dict[str, Any]) -> StockQuote:
    src = raw.get("source") or {}
    return StockQuote(
        status=str(raw.get("status") or STATUS_OK),
        source=SourceMeta(
            provider=str(src.get("provider") or "sina_hq"),
            upstream=str(src.get("upstream") or ""),
            cached=bool(src.get("cached")),
            fetched_at=src.get("fetched_at"),
        ),
        as_of=raw.get("as_of"),
        warnings=list(raw.get("warnings") or []),
        error=raw.get("error"),
        symbol=raw.get("symbol"),
        name=raw.get("name"),
        last=_num(raw.get("last")),
        open=_num(raw.get("open")),
        high=_num(raw.get("high")),
        low=_num(raw.get("low")),
        prev_close=_num(raw.get("prev_close")),
        change=_num(raw.get("change")),
        change_pct=_num(raw.get("change_pct")),
        volume=_num(raw.get("volume")),
        amount=_num(raw.get("amount")),
        bid1=_num(raw.get("bid1")),
        ask1=_num(raw.get("ask1")),
    )


def _bundle_from_dict(raw: dict[str, Any], *, cached: bool) -> FinancialBundle:
    src = raw.get("source") or {}
    statements = []
    for item in raw.get("statements") or []:
        statements.append(
            FinancialStatement(
                status=str(item.get("status") or STATUS_OK),
                source=SourceMeta(
                    provider=str((item.get("source") or {}).get("provider") or "sina_report"),
                    upstream=str((item.get("source") or {}).get("upstream") or ""),
                    cached=cached,
                    fetched_at=(item.get("source") or {}).get("fetched_at"),
                ),
                as_of=item.get("as_of"),
                warnings=list(item.get("warnings") or []),
                symbol=item.get("symbol"),
                report_period=item.get("report_period"),
                publish_date=item.get("publish_date"),
                statement_type=item.get("statement_type"),
                report_kind=item.get("report_kind"),
                currency=item.get("currency"),
                fields=dict(item.get("fields") or {}),
                raw_fields=dict(item.get("raw_fields") or {}),
            )
        )
    return FinancialBundle(
        status=str(raw.get("status") or STATUS_OK),
        source=SourceMeta(
            provider=str(src.get("provider") or "sina_report"),
            upstream=str(src.get("upstream") or ""),
            cached=cached,
            fetched_at=src.get("fetched_at"),
        ),
        warnings=list(raw.get("warnings") or []),
        symbol=raw.get("symbol"),
        statement_type=raw.get("statement_type"),
        statements=statements,
    )
