"""Yahoo Finance chart endpoint — unofficial OHLC (no API key).

Best-effort only: not licensed market data; not investment advice.
Respects CHEMCLAW_HTTP_PROXY / HTTPS_PROXY / HTTP_PROXY / ALL_PROXY.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

PROVIDER_ID = "yahoo_chart_unofficial"
PROVIDER_VERSION = "1.0.0"
_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
_TIMEOUT = 30.0
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9.^_=/-]{1,32}$")
_ALLOWED_RANGE = frozenset({"1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"})
_ALLOWED_INTERVAL = frozenset({"1d", "1wk", "1mo"})
_DISCLAIMER = (
    "Unofficial Yahoo Finance chart endpoint; not licensed market data; "
    "not investment advice. Treat values as untrusted."
)

HttpGet = Callable[..., tuple[int, bytes]]


@dataclass
class YahooOhlcResult:
    status: str  # ok | error
    symbol: Optional[str] = None
    interval: Optional[str] = None
    range: Optional[str] = None
    labels: list[str] = field(default_factory=list)
    ohlc: list[dict[str, float]] = field(default_factory=list)
    volume: list[Optional[float]] = field(default_factory=list)
    currency: Optional[str] = None
    instrument_type: Optional[str] = None
    short_name: Optional[str] = None
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def chart_spec(self) -> Optional[dict[str, Any]]:
        """Deterministic ChartSpec for GUI short-ref resolve (no LLM hand-copy)."""
        if self.status != "ok" or not self.labels or not self.ohlc:
            return None
        if len(self.labels) != len(self.ohlc):
            return None
        title = self.symbol or "OHLC"
        if self.short_name and self.symbol:
            title = f"{self.short_name} ({self.symbol})"
        elif self.short_name:
            title = self.short_name
        spec: dict[str, Any] = {
            "version": 1,
            "type": "candlestick",
            "title": title,
            "labels": list(self.labels),
            "ohlc": [dict(x) for x in self.ohlc],
        }
        if self.currency:
            spec["yLabel"] = str(self.currency)
        return spec

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "symbol": self.symbol,
            "interval": self.interval,
            "range": self.range,
            "labels": list(self.labels),
            "ohlc": [dict(x) for x in self.ohlc],
            "volume": list(self.volume),
            "currency": self.currency,
            "instrument_type": self.instrument_type,
            "short_name": self.short_name,
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
            "chart_spec": self.chart_spec(),
        }


class YahooOhlcProvider(ABC):
    name: str = "base"

    @abstractmethod
    def lookup(
        self,
        *,
        symbol: str,
        chart_range: str = "3mo",
        interval: str = "1d",
    ) -> YahooOhlcResult: ...


def _proxy_url() -> Optional[str]:
    for key in (
        "CHEMCLAW_HTTP_PROXY",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "ALL_PROXY",
        "https_proxy",
        "http_proxy",
        "all_proxy",
    ):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return None


def _default_http_get(
    url: str, headers: Optional[dict[str, str]] = None
) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers=headers
        or {
            "User-Agent": _UA,
            "Accept": "application/json,text/plain,*/*",
        },
        method="GET",
    )
    proxy = _proxy_url()
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
        open_fn = opener.open
    else:
        open_fn = urllib.request.urlopen
    try:
        with open_fn(req, timeout=_TIMEOUT) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp is not None else b""
        return int(exc.code), raw


def _ts_label(ts: int) -> str:
    dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


class YahooChartProvider(YahooOhlcProvider):
    name = PROVIDER_ID

    def __init__(self, *, http_get: Optional[HttpGet] = None) -> None:
        self._http_get = http_get or _default_http_get

    def _source(self) -> dict[str, Any]:
        return {
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
            "url": "https://finance.yahoo.com/",
        }

    def lookup(
        self,
        *,
        symbol: str,
        chart_range: str = "3mo",
        interval: str = "1d",
    ) -> YahooOhlcResult:
        sym = (symbol or "").strip()
        rng = (chart_range or "3mo").strip().lower()
        iv = (interval or "1d").strip().lower()
        warnings = [_DISCLAIMER]

        if not sym or not _SYMBOL_RE.fullmatch(sym):
            return YahooOhlcResult(
                status="error",
                source=self._source(),
                warnings=warnings,
                error="symbol 无效（例：CL=F、BZ=F、AAPL）",
            )
        if rng not in _ALLOWED_RANGE:
            return YahooOhlcResult(
                status="error",
                symbol=sym,
                source=self._source(),
                warnings=warnings,
                error=f"range 须为其一：{', '.join(sorted(_ALLOWED_RANGE))}",
            )
        if iv not in _ALLOWED_INTERVAL:
            return YahooOhlcResult(
                status="error",
                symbol=sym,
                source=self._source(),
                warnings=warnings,
                error=f"interval 须为其一：{', '.join(sorted(_ALLOWED_INTERVAL))}",
            )

        q = urllib.parse.urlencode({"interval": iv, "range": rng})
        url = f"{_CHART_BASE}{urllib.parse.quote(sym, safe='')}?{q}"
        try:
            status, body = self._http_get(
                url,
                {
                    "User-Agent": _UA,
                    "Accept": "application/json",
                },
            )
        except Exception as exc:
            return YahooOhlcResult(
                status="error",
                symbol=sym,
                interval=iv,
                range=rng,
                source=self._source(),
                warnings=warnings,
                error=f"Yahoo chart 请求失败: {exc}",
            )

        if status != 200:
            return YahooOhlcResult(
                status="error",
                symbol=sym,
                interval=iv,
                range=rng,
                source=self._source(),
                warnings=warnings,
                error=f"Yahoo chart HTTP {status}",
            )

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return YahooOhlcResult(
                status="error",
                symbol=sym,
                interval=iv,
                range=rng,
                source=self._source(),
                warnings=warnings,
                error="Yahoo chart 响应不是合法 JSON",
            )

        return self._parse_payload(
            payload, symbol=sym, interval=iv, chart_range=rng, warnings=warnings
        )

    def _parse_payload(
        self,
        payload: Any,
        *,
        symbol: str,
        interval: str,
        chart_range: str,
        warnings: list[str],
    ) -> YahooOhlcResult:
        try:
            result = (payload or {}).get("chart", {}).get("result")
            if not result or not isinstance(result, list) or not result[0]:
                err = (payload or {}).get("chart", {}).get("error")
                msg = None
                if isinstance(err, dict):
                    msg = err.get("description") or err.get("code")
                return YahooOhlcResult(
                    status="error",
                    symbol=symbol,
                    interval=interval,
                    range=chart_range,
                    source=self._source(),
                    warnings=warnings,
                    error=str(msg or "Yahoo chart 无 result"),
                )
            block = result[0]
            meta = block.get("meta") if isinstance(block.get("meta"), dict) else {}
            timestamps = block.get("timestamp") or []
            indicators = block.get("indicators") or {}
            quotes = indicators.get("quote") or []
            if not quotes or not isinstance(quotes[0], dict):
                return YahooOhlcResult(
                    status="error",
                    symbol=symbol,
                    interval=interval,
                    range=chart_range,
                    source=self._source(),
                    warnings=warnings,
                    error="Yahoo chart 无 quote OHLC",
                )
            q0 = quotes[0]
            opens = q0.get("open") or []
            highs = q0.get("high") or []
            lows = q0.get("low") or []
            closes = q0.get("close") or []
            volumes = q0.get("volume") or []

            labels: list[str] = []
            ohlc: list[dict[str, float]] = []
            vol_out: list[Optional[float]] = []
            n = min(len(timestamps), len(opens), len(highs), len(lows), len(closes))
            for i in range(n):
                o, h, l, c = opens[i], highs[i], lows[i], closes[i]
                if o is None or h is None or l is None or c is None:
                    continue
                try:
                    fo, fh, fl, fc = float(o), float(h), float(l), float(c)
                except (TypeError, ValueError):
                    continue
                if not all(map(_finite, (fo, fh, fl, fc))):
                    continue
                labels.append(_ts_label(int(timestamps[i])))
                ohlc.append({"o": fo, "h": fh, "l": fl, "c": fc})
                v = volumes[i] if i < len(volumes) else None
                if v is None:
                    vol_out.append(None)
                else:
                    try:
                        fv = float(v)
                        vol_out.append(fv if _finite(fv) else None)
                    except (TypeError, ValueError):
                        vol_out.append(None)

            if len(ohlc) < 2:
                return YahooOhlcResult(
                    status="error",
                    symbol=symbol,
                    interval=interval,
                    range=chart_range,
                    source=self._source(),
                    warnings=warnings,
                    error="可用 OHLC 点数不足（需要 ≥2）",
                )

            return YahooOhlcResult(
                status="ok",
                symbol=str(meta.get("symbol") or symbol),
                interval=interval,
                range=chart_range,
                labels=labels,
                ohlc=ohlc,
                volume=vol_out,
                currency=meta.get("currency"),
                instrument_type=meta.get("instrumentType"),
                short_name=meta.get("shortName") or meta.get("longName"),
                source=self._source(),
                warnings=warnings,
            )
        except Exception as exc:
            return YahooOhlcResult(
                status="error",
                symbol=symbol,
                interval=interval,
                range=chart_range,
                source=self._source(),
                warnings=warnings,
                error=f"解析 Yahoo chart 失败: {exc}",
            )


def _finite(x: float) -> bool:
    return x == x and x not in (float("inf"), float("-inf"))
