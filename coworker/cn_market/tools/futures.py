"""Structured domestic futures tools registered on the global Agent in Run 5."""

from __future__ import annotations

from typing import Any, Callable, Optional

import aisuite as ai

from ..providers.futures import PublicCNFuturesProvider

_QUOTE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_cn_futures_quote",
        "description": (
            "Fetch a keyless China futures snapshot (Sina L1). "
            "Examples: 甲醇, MA, MA2509, 液化气. market_depth is L1, not L2. "
            "Not licensed market data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Product code, Chinese name, or contract."},
            },
            "required": ["symbol"],
        },
    },
}

_OHLC_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_cn_futures_ohlc",
        "description": (
            "Fetch China futures daily OHLC via Sina JSONP. "
            "Default price chart is daily — do not switch to lookup_cn_futures_minute "
            "unless the user asked for 分时/分钟. "
            "series=main uses today's dominant contract by open interest (not spliced). "
            "series=main_continuous is upstream Sina MA0/pg0 continuous — do not call it local dominant. "
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
                "series": {
                    "type": "string",
                    "description": "auto (default), contract, main, main_continuous.",
                },
            },
            "required": ["symbol"],
        },
    },
}

_MINUTE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_cn_futures_minute",
        "description": (
            "Fetch China futures minute OHLC (1m/5m/15m/30m/60m) from Sina JSONP. "
            "Call only when the user asked for 分时/分钟; default price charts use "
            "lookup_cn_futures_ohlc (daily)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "interval": {"type": "string", "description": "1m, 5m (default), 15m, 30m, 60m."},
                "series": {"type": "string", "description": "auto, contract, main, main_continuous."},
            },
            "required": ["symbol"],
        },
    },
}

_L1_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_cn_futures_l1",
        "description": (
            "Fetch China futures L1: last, bid1, bid1_size, ask1, ask1_size, volume, open_interest. "
            "market_depth=L1. Not Level-2."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
            },
            "required": ["symbol"],
        },
    },
}

_MARGIN_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate_cn_futures_margin",
        "description": (
            "Theoretical futures initial margin = price × multiplier × margin_rate × lots. "
            "Not broker occupancy. margin_rate may be 0.08 or 8 (percent)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "lots": {"type": "number"},
                "price": {"type": "number"},
                "multiplier": {"type": "number"},
                "margin_rate": {"type": "number"},
            },
            "required": ["symbol", "lots"],
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


def make_lookup_cn_futures_quote_tool(
    *, provider: Optional[PublicCNFuturesProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNFuturesProvider()

    def lookup_cn_futures_quote(symbol: str) -> dict[str, Any]:
        return p.futures_quote(symbol).to_dict()

    return _bind(
        lookup_cn_futures_quote,
        "lookup_cn_futures_quote",
        _QUOTE_SCHEMA,
        _QUOTE_SCHEMA["function"]["description"],
    )


def make_lookup_cn_futures_ohlc_tool(
    *, provider: Optional[PublicCNFuturesProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNFuturesProvider()

    def lookup_cn_futures_ohlc(
        symbol: str,
        range: str = "3mo",
        series: str = "auto",
    ) -> dict[str, Any]:
        return p.futures_daily(symbol, chart_range=range, series=series).to_dict()

    return _bind(
        lookup_cn_futures_ohlc,
        "lookup_cn_futures_ohlc",
        _OHLC_SCHEMA,
        _OHLC_SCHEMA["function"]["description"],
    )


def make_lookup_cn_futures_minute_tool(
    *, provider: Optional[PublicCNFuturesProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNFuturesProvider()

    def lookup_cn_futures_minute(
        symbol: str,
        interval: str = "5m",
        series: str = "auto",
    ) -> dict[str, Any]:
        return p.futures_minute(symbol, interval=interval, series=series).to_dict()

    return _bind(
        lookup_cn_futures_minute,
        "lookup_cn_futures_minute",
        _MINUTE_SCHEMA,
        _MINUTE_SCHEMA["function"]["description"],
    )


def make_lookup_cn_futures_l1_tool(
    *, provider: Optional[PublicCNFuturesProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNFuturesProvider()

    def lookup_cn_futures_l1(symbol: str) -> dict[str, Any]:
        return p.futures_l1(symbol).to_dict()

    return _bind(
        lookup_cn_futures_l1,
        "lookup_cn_futures_l1",
        _L1_SCHEMA,
        _L1_SCHEMA["function"]["description"],
    )


def make_calculate_cn_futures_margin_tool(
    *, provider: Optional[PublicCNFuturesProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNFuturesProvider()

    def calculate_cn_futures_margin(
        symbol: str,
        lots: float,
        price: Optional[float] = None,
        multiplier: Optional[float] = None,
        margin_rate: Optional[float] = None,
    ) -> dict[str, Any]:
        return p.futures_margin(
            symbol,
            lots=lots,
            price=price,
            multiplier=multiplier,
            margin_rate=margin_rate,
        ).to_dict()

    return _bind(
        calculate_cn_futures_margin,
        "calculate_cn_futures_margin",
        _MARGIN_SCHEMA,
        _MARGIN_SCHEMA["function"]["description"],
    )
