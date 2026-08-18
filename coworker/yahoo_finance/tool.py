"""The `lookup_yahoo_ohlc` tool — unofficial Yahoo chart OHLC (no API key)."""

from __future__ import annotations

from typing import Any, Callable, Optional

import aisuite as ai

from .providers import YahooChartProvider, YahooOhlcProvider

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_yahoo_ohlc",
        "description": (
            "Fetch OHLC bars for global stocks/futures via the unofficial Yahoo "
            "Finance chart endpoint (no API key). Default is daily (interval=1d, "
            "range=3mo). Use 1wk/1mo only when the user explicitly asks for weekly "
            "or monthly bars. There is no yearly interval — if they ask 年线, use "
            "1mo with enough range and say it is monthly. "
            "Examples: CL=F (WTI), BZ=F (Brent), AAPL, GC=F. "
            "Use lookup_cn_stock_* / lookup_cn_futures_* / lookup_cn_option_market for "
            "mainland China A-shares (A股, 茅台, 600519), China futures (甲醇, 液化气), "
            "and China listed options — do not use Yahoo for those when CN tools exist. "
            "Prefer this tool over shell/curl for global futures/stock OHLC. "
            "Best-effort only — not licensed market data; not investment advice. "
            "For chemical spot prices use chem-data-hub MCP instead. "
            "When plotting, emit one ```chart short-ref per symbol "
            '(e.g. {"version":1,"type":"candlestick","from_tool":"lookup_yahoo_ohlc","symbol":"CL=F"}); '
            "do not hand-copy labels/ohlc — the UI resolves chart_spec from this tool result."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Yahoo symbol, e.g. CL=F, BZ=F, AAPL.",
                },
                "range": {
                    "type": "string",
                    "description": "Lookback: 1mo, 3mo (default), 6mo, 1y, 2y, 5y, ytd, max.",
                },
                "interval": {
                    "type": "string",
                    "description": (
                        "Bar size: 1d (default when unspecified), 1wk, or 1mo. "
                        "Use 1wk/1mo only if the user asked for weekly/monthly."
                    ),
                },
            },
            "required": ["symbol"],
        },
    },
}


def make_lookup_yahoo_ohlc_tool(
    *,
    provider: Optional[YahooOhlcProvider] = None,
) -> Callable[..., Any]:
    def lookup_yahoo_ohlc(
        symbol: str,
        range: str = "3mo",
        interval: str = "1d",
    ) -> dict[str, Any]:
        p: YahooOhlcProvider = provider or YahooChartProvider()
        try:
            result = p.lookup(symbol=symbol, chart_range=range, interval=interval)
        except Exception as exc:
            return {
                "status": "error",
                "symbol": symbol,
                "interval": interval,
                "range": range,
                "labels": [],
                "ohlc": [],
                "volume": [],
                "currency": None,
                "instrument_type": None,
                "short_name": None,
                "source": {
                    "provider_id": getattr(p, "name", "yahoo_chart_unofficial"),
                    "provider_version": "1.0.0",
                },
                "warnings": [],
                "error": f"Yahoo OHLC lookup failed: {exc}",
                "chart_spec": None,
            }
        return result.to_dict()

    lookup_yahoo_ohlc.__name__ = "lookup_yahoo_ohlc"
    lookup_yahoo_ohlc.__doc__ = _SCHEMA["function"]["description"]
    lookup_yahoo_ohlc.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="lookup_yahoo_ohlc",
        category="web",
        risk_level="low",
        capabilities=["search", "fetch"],
        requires_approval=False,
    )
    lookup_yahoo_ohlc.__coworker_schema__ = _SCHEMA
    return lookup_yahoo_ohlc
