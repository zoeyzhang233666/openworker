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
            "Fetch daily (or weekly/monthly) OHLC bars for a stock or futures symbol via "
            "the unofficial Yahoo Finance chart endpoint (no API key). "
            "Examples: CL=F (WTI), BZ=F (Brent), AAPL, GC=F. "
            "Prefer this tool over shell/curl for futures/stock OHLC. "
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
                    "description": "Bar size: 1d (default), 1wk, or 1mo.",
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
