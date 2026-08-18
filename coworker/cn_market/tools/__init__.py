"""CN market structured tools registered on the default Agent in Run 5."""

from __future__ import annotations

from typing import Any, Callable

from .futures import (
    make_calculate_cn_futures_margin_tool,
    make_lookup_cn_futures_l1_tool,
    make_lookup_cn_futures_minute_tool,
    make_lookup_cn_futures_ohlc_tool,
    make_lookup_cn_futures_quote_tool,
)
from .options import make_lookup_cn_option_market_tool
from .stock_features import make_lookup_cn_stock_feature_tool
from .stock_fundamentals import make_lookup_cn_stock_financials_tool
from .stocks import (
    make_lookup_cn_stock_minute_tool,
    make_lookup_cn_stock_ohlc_tool,
    make_lookup_cn_stock_quote_tool,
)


def make_cn_market_tools() -> tuple[Callable[..., Any], ...]:
    return (
        make_lookup_cn_stock_quote_tool(),
        make_lookup_cn_stock_ohlc_tool(),
        make_lookup_cn_stock_minute_tool(),
        make_lookup_cn_stock_financials_tool(),
        make_lookup_cn_stock_feature_tool(),
        make_lookup_cn_futures_quote_tool(),
        make_lookup_cn_futures_ohlc_tool(),
        make_lookup_cn_futures_minute_tool(),
        make_lookup_cn_futures_l1_tool(),
        make_calculate_cn_futures_margin_tool(),
        make_lookup_cn_option_market_tool(),
    )


__all__ = [
    "make_calculate_cn_futures_margin_tool",
    "make_cn_market_tools",
    "make_lookup_cn_futures_l1_tool",
    "make_lookup_cn_futures_minute_tool",
    "make_lookup_cn_futures_ohlc_tool",
    "make_lookup_cn_futures_quote_tool",
    "make_lookup_cn_option_market_tool",
    "make_lookup_cn_stock_feature_tool",
    "make_lookup_cn_stock_financials_tool",
    "make_lookup_cn_stock_minute_tool",
    "make_lookup_cn_stock_ohlc_tool",
    "make_lookup_cn_stock_quote_tool",
]
