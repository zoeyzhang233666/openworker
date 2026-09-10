"""Deterministic, bounded projection of chem-data-hub price payloads.

The module is intentionally independent of MCP and the agent loop: callers pass the
raw result (or its already-read text) and receive a compact summary suitable for a
prompt, chart, or report.  Large raw payloads never need to be re-read by a model.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable


_DATE_KEYS = ("date", "day", "trade_date", "timestamp", "created_at", "time")
_PRICE_KEYS = ("price", "value", "avg_price", "latest_price", "close")
_REGION_KEYS = ("region", "area", "market", "province")
_SPEC_KEYS = ("spec", "specification", "grade", "product_name", "name")


@dataclass(frozen=True)
class MarketSeriesSummary:
    product_name: str
    start_date: str | None
    end_date: str | None
    observations: int
    latest: tuple[dict[str, Any], ...]
    weekly_change: tuple[dict[str, Any], ...]
    extremes: tuple[dict[str, Any], ...]
    chart_spec: dict[str, Any] | None
    data_gaps: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_name": self.product_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "observations": self.observations,
            "latest": list(self.latest),
            "weekly_change": list(self.weekly_change),
            "extremes": list(self.extremes),
            "chart_spec": self.chart_spec,
            "data_gaps": list(self.data_gaps),
            "source_refs": list(self.source_refs),
        }


class MarketSeriesAggregator:
    """One-method deep module for price-series projection."""

    @classmethod
    def summarize(
        cls, raw: Any, *, product_name: str = "", max_series: int = 12
    ) -> MarketSeriesSummary:
        payload = cls._decode(raw)
        rows = list(cls._rows(payload))
        normalized = [item for item in (cls._normalize(row) for row in rows) if item]
        refs = cls._source_refs(payload)
        if not normalized:
            return MarketSeriesSummary(
                product_name=product_name,
                start_date=None,
                end_date=None,
                observations=0,
                latest=(),
                weekly_change=(),
                extremes=(),
                chart_spec=None,
                data_gaps=("未识别到可计算的日期与价格记录",),
                source_refs=refs,
            )
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in normalized:
            groups[f"{row['region']}｜{row['spec']}"].append(row)
        latest: list[dict[str, Any]] = []
        changes: list[dict[str, Any]] = []
        extremes: list[dict[str, Any]] = []
        chart_labels: list[str] = []
        chart_values: list[float] = []
        all_dates = [row["date"] for row in normalized if row["date"]]
        for key, series in list(sorted(groups.items()))[:max_series]:
            series.sort(key=lambda item: item["date"] or "")
            first, last = series[0], series[-1]
            latest.append({"series": key, "date": last["date"], "price": last["price"], "unit": last["unit"]})
            change = None
            if first["price"]:
                change = round((last["price"] - first["price"]) / first["price"] * 100, 2)
            changes.append({"series": key, "change_pct": change, "from_date": first["date"], "to_date": last["date"]})
            values = [item["price"] for item in series]
            extremes.append({"series": key, "low": min(values), "high": max(values), "unit": last["unit"]})
            if not chart_labels:
                chart_labels = [item["date"] or str(index + 1) for index, item in enumerate(series)]
                chart_values = [item["price"] for item in series]
        chart = None
        if chart_values and latest:
            chart = {
                "version": 1,
                "type": "line",
                "title": product_name or latest[0]["series"],
                "labels": chart_labels,
                "series": [{"name": latest[0]["series"], "values": chart_values}],
                "unit": latest[0].get("unit") or "元/吨",
            }
        return MarketSeriesSummary(
            product_name=product_name,
            start_date=min(all_dates) if all_dates else None,
            end_date=max(all_dates) if all_dates else None,
            observations=len(normalized),
            latest=tuple(latest),
            weekly_change=tuple(changes),
            extremes=tuple(extremes),
            chart_spec=chart,
            source_refs=refs,
        )

    @staticmethod
    def _decode(raw: Any) -> Any:
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return raw

    @classmethod
    def _rows(cls, payload: Any) -> Iterable[dict[str, Any]]:
        if isinstance(payload, list):
            for item in payload:
                yield from cls._rows(item)
        elif isinstance(payload, dict):
            if any(key in payload for key in _PRICE_KEYS):
                yield payload
            for key in ("data", "items", "results", "prices", "records", "rows"):
                if key in payload:
                    yield from cls._rows(payload[key])

    @staticmethod
    def _first(row: dict[str, Any], keys: tuple[str, ...], default: str = "") -> Any:
        for key in keys:
            if row.get(key) not in (None, ""):
                return row[key]
        return default

    @classmethod
    def _normalize(cls, row: dict[str, Any]) -> dict[str, Any] | None:
        raw_price = cls._first(row, _PRICE_KEYS)
        try:
            price = float(str(raw_price).replace(",", ""))
        except (TypeError, ValueError):
            return None
        raw_date = str(cls._first(row, _DATE_KEYS))
        match = re.search(r"\d{4}-\d{1,2}-\d{1,2}", raw_date)
        value = match.group(0) if match else raw_date[:10]
        try:
            value = date.fromisoformat(value).isoformat()
        except ValueError:
            pass
        return {
            "date": value or None,
            "price": price,
            "region": str(cls._first(row, _REGION_KEYS, "全国")),
            "spec": str(cls._first(row, _SPEC_KEYS, "现货")),
            "unit": str(row.get("unit") or "元/吨"),
        }

    @staticmethod
    def _source_refs(payload: Any) -> tuple[str, ...]:
        if not isinstance(payload, dict):
            return ()
        refs = payload.get("source_refs") or payload.get("sources") or ()
        if isinstance(refs, str):
            refs = (refs,)
        return tuple(str(item) for item in refs if item)[:12]
