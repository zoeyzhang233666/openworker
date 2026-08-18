"""Deterministic A-share trade calendar utilities. No network."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Callable, Iterable, Optional

Clock = Callable[[], datetime]


class TradeCalendar:
    """Weekday calendar minus an injected holiday set.

    Real exchange calendars belong in a later data-run; this object only
    provides previous/latest helpers with a testable clock.
    """

    def __init__(
        self,
        *,
        holidays: Optional[Iterable[date]] = None,
        extra_trading_days: Optional[Iterable[date]] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._holidays = frozenset(holidays or ())
        self._extra = frozenset(extra_trading_days or ())
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def is_trading_day(self, day: date) -> bool:
        if day in self._extra:
            return True
        if day in self._holidays:
            return False
        return day.weekday() < 5

    def previous_trade_date(self, day: date) -> date:
        cursor = day - timedelta(days=1)
        for _ in range(366 * 3):
            if self.is_trading_day(cursor):
                return cursor
            cursor -= timedelta(days=1)
        raise RuntimeError("no previous trading day within 3 years")

    def latest_trade_date(self, *, as_of: Optional[date] = None) -> date:
        day = as_of or self._clock().date()
        if self.is_trading_day(day):
            return day
        return self.previous_trade_date(day)
