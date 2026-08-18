"""Structured A-share tools registered on the global Agent in Run 5."""

from __future__ import annotations

from typing import Any, Callable, Optional

import aisuite as ai

from ..providers.stocks import PublicCNStockProvider

_QUOTE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_cn_stock_quote",
        "description": (
            "Fetch a keyless A-share snapshot quote (Sina hq). "
            "Examples: 600519, 600519.SH, 贵州茅台. Not licensed market data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "A-share code or Chinese name."},
            },
            "required": ["symbol"],
        },
    },
}

_OHLC_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_cn_stock_ohlc",
        "description": (
            "Fetch A-share daily OHLC via Sina JSONP K-line (unadjusted). "
            "Default price chart is daily — do not switch to lookup_cn_stock_minute "
            "unless the user asked for 分时/分钟. "
            "Return includes chart_spec; do not hand-copy OHLC."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "range": {
                    "type": "string",
                    "description": "1mo, 3mo (default), 6mo, 1y, 2y, 5y, ytd, max.",
                },
                "adjustment": {
                    "type": "string",
                    "description": "none (supported), qfq/hfq currently fall back to none with a warning.",
                },
            },
            "required": ["symbol"],
        },
    },
}

_MINUTE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_cn_stock_minute",
        "description": (
            "Fetch A-share minute OHLC (1m/5m/15m/30m/60m) from Sina JSONP K-line. "
            "Call only when the user asked for 分时/分钟; default price charts use "
            "lookup_cn_stock_ohlc (daily)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "interval": {"type": "string", "description": "1m, 5m (default), 15m, 30m, 60m."},
            },
            "required": ["symbol"],
        },
    },
}


def _bind(fn: Callable[..., Any], name: str, schema: dict[str, Any], description: str):
    fn.__name__ = name
    fn.__doc__ = description
    fn.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name=name,
        category="web",
        risk_level="low",
        capabilities=["search", "fetch"],
        requires_approval=False,
    )
    fn.__coworker_schema__ = schema
    return fn


def make_lookup_cn_stock_quote_tool(
    *, provider: Optional[PublicCNStockProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNStockProvider()

    def lookup_cn_stock_quote(symbol: str) -> dict[str, Any]:
        return p.stock_quote(symbol).to_dict()

    return _bind(
        lookup_cn_stock_quote,
        "lookup_cn_stock_quote",
        _QUOTE_SCHEMA,
        _QUOTE_SCHEMA["function"]["description"],
    )


def make_lookup_cn_stock_ohlc_tool(
    *, provider: Optional[PublicCNStockProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNStockProvider()

    def lookup_cn_stock_ohlc(
        symbol: str,
        range: str = "3mo",
        adjustment: str = "none",
    ) -> dict[str, Any]:
        return p.stock_daily(symbol, chart_range=range, adjustment=adjustment).to_dict()

    return _bind(
        lookup_cn_stock_ohlc,
        "lookup_cn_stock_ohlc",
        _OHLC_SCHEMA,
        _OHLC_SCHEMA["function"]["description"],
    )


def make_lookup_cn_stock_minute_tool(
    *, provider: Optional[PublicCNStockProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNStockProvider()

    def lookup_cn_stock_minute(symbol: str, interval: str = "5m") -> dict[str, Any]:
        return p.stock_minute(symbol, interval=interval).to_dict()

    return _bind(
        lookup_cn_stock_minute,
        "lookup_cn_stock_minute",
        _MINUTE_SCHEMA,
        _MINUTE_SCHEMA["function"]["description"],
    )
