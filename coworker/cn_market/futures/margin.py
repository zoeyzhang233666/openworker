"""Theoretical futures initial margin. Not broker occupancy."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from ..http import DISCLAIMER
from ..models import STATUS_INVALID_REQUEST, STATUS_OK, MarginEstimate, SourceMeta

# Exchange contract sizes (tons or barrels per lot). Spec table, not today's notice.
CONTRACT_MULTIPLIER: dict[str, float] = {
    "PG": 20,
    "MA": 10,
    "EB": 5,
    "PP": 5,
    "L": 5,
    "V": 5,
    "EG": 10,
    "SA": 20,
    "UR": 20,
    "SC": 1000,
    "FU": 10,
    "BU": 10,
    "RU": 10,
    "BR": 5,
    "TA": 5,
    "PF": 5,
    "PX": 5,
    "SH": 30,
    "FG": 20,
    "SI": 5,
    "LC": 1,
}

_WARNINGS = [
    DISCLAIMER,
    "此为理论初始保证金估算，不等于期货公司实际占用或交易所当日通知。",
]


def _dec(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None


def _as_rate(raw: Any) -> Optional[Decimal]:
    rate = _dec(raw)
    if rate is None or rate <= 0:
        return None
    if rate > 1:
        return rate / Decimal("100")
    return rate


def calculate_theoretical_margin(
    *,
    price: Any,
    multiplier: Any,
    margin_rate: Any,
    lots: Any,
    symbol: Optional[str] = None,
) -> MarginEstimate:
    source = SourceMeta(provider="local_formula", upstream="none", cached=False, attempt=1)
    price_d = _dec(price)
    mult_d = _dec(multiplier)
    lots_d = _dec(lots)
    rate_d = _as_rate(margin_rate)
    if None in (price_d, mult_d, lots_d, rate_d):
        return MarginEstimate(
            status=STATUS_INVALID_REQUEST,
            source=source,
            error="须提供正数 price、multiplier、margin_rate、lots；rate 为 0.08 或 8（百分数）",
            warnings=list(_WARNINGS),
            symbol=symbol,
            estimate_kind="theoretical",
        )
    assert price_d is not None and mult_d is not None and lots_d is not None and rate_d is not None
    if price_d <= 0 or mult_d <= 0 or lots_d <= 0:
        return MarginEstimate(
            status=STATUS_INVALID_REQUEST,
            source=source,
            error="price / multiplier / lots 必须为正数",
            warnings=list(_WARNINGS),
            symbol=symbol,
            estimate_kind="theoretical",
        )
    margin = (price_d * mult_d * rate_d * lots_d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return MarginEstimate(
        status=STATUS_OK,
        source=source,
        warnings=list(_WARNINGS),
        symbol=symbol,
        price=float(price_d),
        multiplier=float(mult_d),
        margin_rate=float(rate_d),
        lots=float(lots_d),
        margin=margin,
        estimate_kind="theoretical",
    )
