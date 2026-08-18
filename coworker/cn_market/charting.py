"""ChartSpec helpers for CN market OHLC. GUI short-ref resolves lookup_cn_* and Yahoo."""

from __future__ import annotations

from typing import Any, Optional

from .models import STATUS_OK, STATUS_PARTIAL, STATUS_STALE_CACHE, OhlcSeries

_PLOT_OK = {STATUS_OK, STATUS_PARTIAL, STATUS_STALE_CACHE}


def ohlc_chart_spec(series: OhlcSeries) -> Optional[dict[str, Any]]:
    if series.status not in _PLOT_OK:
        return None
    if not series.labels or not series.ohlc:
        return None
    if len(series.labels) != len(series.ohlc):
        return None
    title = series.symbol or "OHLC"
    return {
        "version": 1,
        "type": "candlestick",
        "title": title,
        "labels": list(series.labels),
        "ohlc": [bar.to_dict() for bar in series.ohlc],
        "yLabel": "CNY",
    }
