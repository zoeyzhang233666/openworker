"""Minimal ChartSpec v1 parse for report HTML cook (subset of GUI chartSpec.ts)."""

from __future__ import annotations

import json
from typing import Any, Optional


CHART_TYPES = frozenset({"line", "bar", "area", "scatter", "candlestick"})
OHLC_CHART_TOOLS = frozenset(
    {
        "lookup_yahoo_ohlc",
        "lookup_cn_stock_ohlc",
        "lookup_cn_stock_minute",
        "lookup_cn_futures_ohlc",
        "lookup_cn_futures_minute",
        "lookup_cn_option_market",
    }
)


def parse_chart_spec(raw: Any) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Return (normalized_spec, error). Missing version treated as 1."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None, "chart JSON 无效"
    if not isinstance(raw, dict):
        return None, "chart 必须是对象"
    data = dict(raw)
    # Short-ref: caller should bake before parse; reject unresolved.
    if data.get("from_tool") and not data.get("labels") and not data.get("ohlc"):
        return None, "短引用图表缺少烘焙数据"
    version = data.get("version", 1)
    if version not in (1, "1"):
        return None, "仅支持 ChartSpec version 1"
    ctype = data.get("type")
    if ctype not in CHART_TYPES:
        return None, f"不支持的图表类型: {ctype!r}"
    labels = data.get("labels")
    if not isinstance(labels, list) or not labels:
        return None, "labels 必须是非空数组"
    labels = [str(x) for x in labels]
    n = len(labels)
    series_out: list[dict[str, Any]] = []
    ohlc_out: list[dict[str, float]] | None = None
    if ctype == "candlestick":
        ohlc = data.get("ohlc")
        if not isinstance(ohlc, list) or len(ohlc) != n:
            return None, "candlestick 需要与 labels 等长的 ohlc"
        ohlc_out = []
        for i, bar in enumerate(ohlc):
            parsed = _parse_ohlc_bar(bar, i)
            if isinstance(parsed, str):
                return None, parsed
            ohlc_out.append(parsed)
    else:
        series = data.get("series")
        if not isinstance(series, list) or not series:
            return None, "series 必须是非空数组"
        for i, item in enumerate(series):
            if not isinstance(item, dict):
                return None, f"series[{i}] 必须是对象"
            name = item.get("name")
            values = item.get("values")
            if not isinstance(name, str) or not name.strip():
                return None, f"series[{i}].name 无效"
            if not isinstance(values, list) or len(values) != n:
                return None, f"series[{i}].values 长度必须等于 labels"
            cleaned: list[float | None] = []
            for j, v in enumerate(values):
                if v is None:
                    cleaned.append(None)
                elif isinstance(v, (int, float)) and v == v:  # not NaN
                    cleaned.append(float(v))
                else:
                    return None, f"series[{i}].values[{j}] 必须是数字或 null"
            series_out.append({"name": name.strip(), "values": cleaned})
    spec: dict[str, Any] = {
        "version": 1,
        "type": ctype,
        "labels": labels,
        "series": series_out,
    }
    if ohlc_out is not None:
        spec["ohlc"] = ohlc_out
    for key in ("title", "subtitle", "unit", "xTitle", "yTitle", "focusLabel"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            spec[key] = val.strip()
    for key in ("yMin", "yMax"):
        val = data.get(key)
        if isinstance(val, (int, float)) and val == val:
            spec[key] = float(val)
    if isinstance(data.get("showLegend"), bool):
        spec["showLegend"] = data["showLegend"]
    stages = data.get("stages")
    if isinstance(stages, list):
        cleaned_stages = []
        for item in stages[:8]:
            if not isinstance(item, dict):
                continue
            tone = item.get("tone")
            if tone not in ("up", "down", "side"):
                continue
            start = item.get("start")
            end = item.get("end")
            reason = item.get("reason")
            if not isinstance(start, str) or not isinstance(end, str):
                continue
            if not isinstance(reason, str):
                reason = ""
            cleaned_stages.append(
                {
                    "start": start.strip(),
                    "end": end.strip(),
                    "tone": tone,
                    "reason": reason.strip()[:80],
                }
            )
        if cleaned_stages:
            spec["stages"] = cleaned_stages
    return spec, None


def _parse_ohlc_bar(raw: Any, index: int) -> dict[str, float] | str:
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        o, h, l, c = raw
    elif isinstance(raw, dict):
        o = raw.get("o", raw.get("open"))
        h = raw.get("h", raw.get("high"))
        l = raw.get("l", raw.get("low"))
        c = raw.get("c", raw.get("close"))
    else:
        return f"ohlc[{index}] 必须是 [o,h,l,c] 或对象"
    out: dict[str, float] = {}
    for key, val in (("o", o), ("h", h), ("l", l), ("c", c)):
        if not isinstance(val, (int, float)) or val != val:
            return f"ohlc[{index}].{key} 必须是有限数字"
        out[key] = float(val)
    return out


def bake_short_ref(
    raw: dict[str, Any],
    chart_tool_results: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """If ``from_tool`` short-ref, merge matching tool chart_spec / OHLC into a full spec."""
    if not isinstance(raw, dict):
        return raw
    tool_name = raw.get("from_tool")
    if not tool_name or not isinstance(tool_name, str):
        return raw
    if raw.get("labels") and (raw.get("ohlc") or raw.get("series")):
        return raw
    symbol = str(raw.get("symbol") or "").strip()
    name_hint = str(raw.get("name") or "").strip()
    results = list(chart_tool_results or [])
    for row in reversed(results):
        if not isinstance(row, dict):
            continue
        row_name = str(row.get("name") or "")
        if row_name != tool_name and tool_name not in OHLC_CHART_TOOLS:
            continue
        if tool_name in OHLC_CHART_TOOLS and row_name != tool_name:
            continue
        spec = row.get("chart_spec")
        if not isinstance(spec, dict):
            continue
        args = row.get("args") if isinstance(row.get("args"), dict) else {}
        payload_symbol = str(args.get("symbol") or spec.get("symbol") or "").strip()
        aliases = spec.get("aliases") if isinstance(spec.get("aliases"), list) else []
        display = str(spec.get("name") or "").strip()
        if symbol:
            matched = (
                symbol == payload_symbol
                or symbol == display
                or symbol in {str(a) for a in aliases}
            )
            if not matched:
                continue
        if name_hint and name_hint not in {display, payload_symbol} and name_hint not in {
            str(a) for a in aliases
        }:
            continue
        baked = dict(spec)
        for key in ("title", "subtitle", "stages", "focusLabel", "unit"):
            if key in raw and raw[key] is not None:
                baked[key] = raw[key]
        baked["version"] = 1
        baked.pop("from_tool", None)
        return baked
    return raw
