"""Minimal ChartSpec v1 parse for report HTML cook (subset of GUI chartSpec.ts)."""

from __future__ import annotations

import json
import re
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


def normalize_chart_spec_dict(raw: Any) -> Optional[dict[str, Any]]:
    """Coerce legacy/aggregated shapes into ChartSpec v1; None when unusable."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, dict):
        return None
    data = dict(raw)
    inner = data.get("data")
    if isinstance(inner, dict):
        labels = inner.get("labels")
        datasets = inner.get("datasets")
        if isinstance(labels, list) and isinstance(datasets, list) and datasets:
            data["labels"] = labels
            series: list[dict[str, Any]] = []
            for ds in datasets:
                if not isinstance(ds, dict):
                    continue
                values = ds.get("data")
                if values is None:
                    values = ds.get("values")
                if not isinstance(values, list):
                    continue
                name = ds.get("label") or ds.get("name") or "系列"
                series.append({"name": str(name), "values": values})
            if series:
                data["series"] = series
            data.pop("data", None)
    x = data.get("x")
    if isinstance(x, dict) and isinstance(x.get("labels"), list) and "labels" not in data:
        data["labels"] = x["labels"]
    if "type" not in data:
        data["type"] = "line"
    if "version" not in data:
        data["version"] = 1
    spec, err = parse_chart_spec(data)
    return spec if err is None else None


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


def _symbol_key(raw: str) -> str:
    return (raw or "").strip().upper()


def _symbols_match(want: str, got: str) -> bool:
    """Align with GUI ``chartSpec.ts`` — SC2610 matches SC2610.INE, etc."""
    a = _symbol_key(want)
    b = _symbol_key(got)
    if not a or not b:
        return False
    if a == b:
        return True
    a_base = a.split(".")[0]
    b_base = b.split(".")[0]
    if a_base and a_base == b_base:
        return True
    if (
        re.match(r"^[A-Z]{1,3}$", a_base)
        and b_base.startswith(a_base)
        and re.search(r"\d", b_base[len(a_base) :])
    ):
        return True
    if (
        re.match(r"^[A-Z]{1,3}$", b_base)
        and a_base.startswith(b_base)
        and re.search(r"\d", a_base[len(b_base) :])
    ):
        return True
    return False


def _row_name_labels(row: dict[str, Any]) -> set[str]:
    args = row.get("args") if isinstance(row.get("args"), dict) else {}
    spec = row.get("chart_spec") if isinstance(row.get("chart_spec"), dict) else {}
    labels: set[str] = set()
    for key in ("symbol", "series_name"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            labels.add(val.strip())
    arg_sym = args.get("symbol")
    if isinstance(arg_sym, str) and arg_sym.strip():
        labels.add(arg_sym.strip())
    for key in ("symbol", "name", "title"):
        val = spec.get(key)
        if isinstance(val, str) and val.strip():
            labels.add(val.strip())
    for source in (row.get("aliases"), spec.get("aliases")):
        if isinstance(source, list):
            labels.update(str(item).strip() for item in source if item)
    return labels


def _row_matches_symbol(row: dict[str, Any], symbol: str) -> bool:
    if not symbol:
        return True
    return any(_symbols_match(symbol, label) for label in _row_name_labels(row))


def _row_matches_name_hint(row: dict[str, Any], name_hint: str) -> bool:
    if not name_hint:
        return True
    return any(_symbols_match(name_hint, label) for label in _row_name_labels(row))


def _rows_for_tool(
    results: list[dict[str, Any]], tool_name: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        row_name = str(row.get("name") or "")
        if tool_name in OHLC_CHART_TOOLS:
            if row_name != tool_name:
                continue
        elif row_name != tool_name:
            continue
        if not isinstance(row.get("chart_spec"), dict):
            continue
        rows.append(row)
    return rows


def _merge_baked_spec(raw: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    baked = dict(spec)
    for key in ("title", "subtitle", "stages", "focusLabel", "unit"):
        if key in raw and raw[key] is not None:
            baked[key] = raw[key]
    baked["version"] = 1
    baked.pop("from_tool", None)
    return baked


def collect_chart_tool_results_from_messages(
    messages: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Rebuild OHLC chart sidecars from session messages (D-162 parity for Channel HTML)."""
    if not messages:
        return []
    pending: dict[str, tuple[str, dict[str, Any]]] = {}
    results: list[dict[str, Any]] = []
    for msg in messages:
        role = str(msg.get("role") or "")
        if role == "assistant":
            for tc in msg.get("tool_calls") or []:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
                name = str(fn.get("name") or "")
                args_raw = fn.get("arguments")
                args: dict[str, Any] = {}
                if isinstance(args_raw, str):
                    try:
                        parsed = json.loads(args_raw)
                        if isinstance(parsed, dict):
                            args = parsed
                    except json.JSONDecodeError:
                        args = {}
                elif isinstance(args_raw, dict):
                    args = dict(args_raw)
                tc_id = str(tc.get("id") or "")
                if tc_id and name:
                    pending[tc_id] = (name, args)
            continue
        if role != "tool":
            continue
        tc_id = str(msg.get("tool_call_id") or "")
        name, args = pending.get(tc_id, ("", {}))
        if name not in OHLC_CHART_TOOLS:
            continue
        content = msg.get("content")
        if isinstance(content, str):
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                continue
        elif isinstance(content, dict):
            payload = content
        else:
            continue
        if not isinstance(payload, dict):
            continue
        spec = payload.get("chart_spec")
        if not isinstance(spec, dict):
            continue
        row: dict[str, Any] = {"name": name, "args": args, "chart_spec": spec}
        symbol = payload.get("symbol")
        if isinstance(symbol, str) and symbol.strip():
            row["symbol"] = symbol.strip()
        series_name = payload.get("name")
        if isinstance(series_name, str) and series_name.strip():
            row["series_name"] = series_name.strip()
        aliases = payload.get("aliases")
        if isinstance(aliases, list):
            row["aliases"] = [
                str(item).strip() for item in aliases if isinstance(item, str) and item.strip()
            ]
        results.append(row)
    return results


def merge_chart_tool_results(
    *sources: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Merge chart sidecar rows; later sources win for the same tool+symbol key."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for source in sources:
        for row in source or []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "")
            spec = row.get("chart_spec") if isinstance(row.get("chart_spec"), dict) else {}
            args = row.get("args") if isinstance(row.get("args"), dict) else {}
            sym = str(
                row.get("symbol")
                or args.get("symbol")
                or spec.get("symbol")
                or spec.get("title")
                or ""
            ).strip()
            merged[(name, sym)] = row
    return list(merged.values())


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
    tool_rows = _rows_for_tool(results, tool_name)
    for row in reversed(tool_rows):
        if symbol and not _row_matches_symbol(row, symbol):
            continue
        if name_hint and not _row_matches_name_hint(row, name_hint):
            continue
        return _merge_baked_spec(raw, row["chart_spec"])
    if symbol and len(tool_rows) == 1:
        row = tool_rows[0]
        if not name_hint or _row_matches_name_hint(row, name_hint):
            return _merge_baked_spec(raw, row["chart_spec"])
    if not symbol and tool_rows:
        row = tool_rows[-1]
        if not name_hint or _row_matches_name_hint(row, name_hint):
            return _merge_baked_spec(raw, row["chart_spec"])
    return raw
