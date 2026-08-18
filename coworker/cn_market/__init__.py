"""Keyless structured China market data. AKShare is not a core dependency and must
not be imported here. Structured tools are registered on the default Agent in Run 5.
"""

from __future__ import annotations

from .calendar import TradeCalendar
from .cache import CacheKey, MarketCache, ttl_for
from .errors import (
    CNMarketError,
    InvalidSymbolError,
    UnsupportedKeylessError,
)
from .models import (
    MarketResult,
    OhlcBar,
    OhlcSeries,
    SourceMeta,
)
from .source_policy import MAX_PROVIDER_ATTEMPTS, policy_for
from .symbols import CNFuturesSymbol, CNStockSymbol, resolve_futures, resolve_stock

__all__ = [
    "CNFuturesSymbol",
    "CNMarketError",
    "CNStockSymbol",
    "CacheKey",
    "InvalidSymbolError",
    "MAX_PROVIDER_ATTEMPTS",
    "MarketCache",
    "MarketResult",
    "OhlcBar",
    "OhlcSeries",
    "SourceMeta",
    "TradeCalendar",
    "UnsupportedKeylessError",
    "policy_for",
    "resolve_futures",
    "resolve_stock",
    "ttl_for",
]
