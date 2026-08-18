"""Offline fake provider for unit tests. Never opens a network socket."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

from ..cache import CacheKey, MarketCache
from ..errors import InvalidSymbolError
from ..models import (
    STATUS_INVALID_SYMBOL,
    STATUS_OK,
    STATUS_STALE_CACHE,
    STATUS_UNSUPPORTED_KEYLESS,
    MarketResult,
    OhlcBar,
    OhlcSeries,
    SourceMeta,
)
from ..source_policy import policy_for
from ..symbols import resolve_stock
from .base import CNMarketProvider

Clock = Callable[[], datetime]


def _fixture_series(symbol: str, adjustment: str, fetched_at: str) -> OhlcSeries:
    labels = ["2026-08-12", "2026-08-13", "2026-08-14", "2026-08-18"]
    closes = [1410.0, 1420.0, 1415.0, 1430.0]
    ohlc = [
        OhlcBar(o=c - 5.0, h=c + 8.0, l=c - 9.0, c=c) for c in closes
    ]
    return OhlcSeries(
        status=STATUS_OK,
        source=SourceMeta(
            provider="fake",
            upstream="fixture",
            cached=False,
            fetched_at=fetched_at,
            source_version="fake-1",
        ),
        as_of=labels[-1],
        warnings=["fake provider; not live market data"],
        error=None,
        labels=labels,
        ohlc=ohlc,
        volume=[1000.0, 1100.0, 1050.0, 1200.0],
        amount=[1.4e6, 1.5e6, 1.45e6, 1.6e6],
        adjustment=adjustment,
        symbol=symbol,
        interval="1d",
        actual_range="1mo",
    )


class FakeCNMarketProvider(CNMarketProvider):
    name = "fake"

    def __init__(
        self,
        *,
        cache: Optional[MarketCache] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._cache = cache
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now_iso(self) -> str:
        return self._clock().isoformat()

    def _key(self, symbol: str, adjustment: str, chart_range: str) -> CacheKey:
        return CacheKey(
            domain="stock",
            symbol=symbol,
            dataset="daily",
            interval="1d",
            adjustment=adjustment,
            source_version=f"fake-1:{chart_range}",
        )

    def stock_daily(
        self,
        query: str,
        *,
        chart_range: str = "3mo",
        adjustment: str = "qfq",
    ) -> OhlcSeries:
        try:
            resolved = resolve_stock(query)
        except InvalidSymbolError as exc:
            return OhlcSeries(
                status=STATUS_INVALID_SYMBOL,
                source=SourceMeta(provider="fake", upstream="fixture", cached=False),
                error=str(exc),
                warnings=[],
            )

        key = self._key(resolved.canonical, adjustment, chart_range)
        if self._cache is not None:
            hit = self._cache.get(key)
            if hit is not None:
                series = OhlcSeries.from_dict(hit.payload, cached=True)
                if hit.fresh:
                    series.status = STATUS_OK
                else:
                    series.status = STATUS_STALE_CACHE
                    series.warnings = list(series.warnings) + ["stale cache"]
                return series

        series = _fixture_series(resolved.canonical, adjustment, self._now_iso())
        if self._cache is not None:
            self._cache.put(key, series.to_dict(), dataset_kind="daily")
        return series

    def tick_l2(self, query: str) -> MarketResult:
        policy = policy_for("tick_l2")
        return MarketResult(
            status=STATUS_UNSUPPORTED_KEYLESS,
            source=SourceMeta(provider="none", upstream="", cached=False),
            error="tick/L2 is not available from a stable keyless source",
            warnings=[f"dataset={policy.dataset}"],
        )
