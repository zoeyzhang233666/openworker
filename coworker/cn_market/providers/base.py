"""Provider protocols. Real HTTP adapters arrive in later runs."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import MarketResult, OhlcSeries


class CNMarketProvider(ABC):
    name: str = "base"

    @abstractmethod
    def stock_daily(
        self,
        query: str,
        *,
        chart_range: str = "3mo",
        adjustment: str = "qfq",
    ) -> OhlcSeries: ...

    def tick_l2(self, query: str) -> MarketResult:
        raise NotImplementedError
