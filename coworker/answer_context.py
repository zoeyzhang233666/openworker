"""Recoverable model views of evidence; full tool records remain authoritative."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

# Outbound-only budgets. History keeps the full tool payload.
_LIMITS = {
    "fast": {"search_results": 6, "snippet": 1100, "fetch": 4000},
    "deep": {"search_results": 8, "snippet": 1800, "fetch": 8000},
}


def unicode_json(content: str) -> str:
    """Decode JSON escapes once, never alter plain text or literal backslashes."""
    try:
        value = json.loads(content)
    except (ValueError, TypeError):
        return content
    if not isinstance(value, (dict, list)):
        return content
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _excerpt(text: str, query: str, limit: int) -> str:
    # Extract verbatim spans, including the beginning for context. No generated facts.
    if len(text) <= limit:
        return text
    words = set(re.findall(r"[a-z0-9]{2,}", query.casefold()))
    for run in re.findall(r"[\u4e00-\u9fff]+", query):
        words.update(run[i:i + 2] for i in range(len(run) - 1))
    spans = [text[i:i + 350] for i in range(0, len(text), 350)]
    ranked = sorted(range(1, len(spans)), key=lambda i: (
        -sum(word in spans[i].casefold() for word in words), i))
    selected = sorted([0, *ranked[:max(0, limit // 350 - 1)]])
    return "\n[…摘录间省略…]\n".join(spans[i] for i in selected)[:limit] + "\n[…更多内容见完整结果…]"


def _recoverable(view: dict, content: str, workspace: Path) -> str:
    # Content-addressed, exact recovery. Never advertise a path after failed I/O.
    rel = Path("._chemclaw/outbound-clip") / (hashlib.sha256(content.encode()).hexdigest() + ".json")
    path = workspace / rel
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(json.dumps(json.loads(content), ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError):
        return content
    return json.dumps({**view, "full_result_path": rel.as_posix(),
        "view_notice": "这是摘录；仅在核心事实缺失时按需读取完整结果，不要重复搜索或默认全文重读。"},
        ensure_ascii=False, separators=(",", ":"))


def _chart_summary_view(data: dict, tool_name: str) -> dict[str, Any] | None:
    from .report_html.chart_spec import normalize_chart_spec_dict
    if not (isinstance(data.get("chart_spec"), dict) and data.get("chart_id")):
        return None
    spec = normalize_chart_spec_dict(data["chart_spec"])
    if not spec:
        return None
    labels = spec["labels"]
    summaries = []
    for series in spec.get("series", []):
        values = [(label, value) for label, value in zip(labels, series["values"]) if value is not None]
        if values:
            summaries.append({"name": series["name"], "first": values[0], "latest": values[-1],
                "low": min(v for _, v in values), "high": max(v for _, v in values)})
    bars = spec.get("ohlc", [])
    if bars:
        summaries.append({"first": [labels[0], bars[0]], "latest": [labels[-1], bars[-1]],
            "low": min(b["l"] for b in bars), "high": max(b["h"] for b in bars)})
    view = {k: data[k] for k in ("status", "symbol", "name", "product_name", "unit", "source",
        "source_refs", "data_gaps", "warnings", "meta", "as_of", "latest") if k in data}
    view.update(chart_summary={"title": spec.get("title"), "unit": spec.get("unit"),
        "points": len(labels), "from": labels[0], "to": labels[-1], "series": summaries},
        chart_ref={"version": 1, "from_tool": tool_name, "chart_id": data["chart_id"]},
        chart_instruction="在答案中用 ```chart 围栏原样输出 chart_ref，前端读取完整数据绘图；无需工具、脚本或手抄数组。")
    return view


def bounded_evidence_view(
    content: str,
    *,
    tool_name: str,
    query: str,
    workspace: Path,
    depth: str = "fast",
) -> str:
    """Bound web evidence and separate chart transport from model reasoning.

    Applies to every research depth: history stays authoritative; only the
    provider-bound copy is reduced. Deep keeps a larger excerpt budget.
    """
    content = unicode_json(content)
    try:
        data = json.loads(content)
    except ValueError:
        return content
    if not isinstance(data, dict) or data.get("error"):
        return content
    chart_view = _chart_summary_view(data, tool_name)
    if chart_view is not None:
        return _recoverable(chart_view, content, workspace)
    limits = _LIMITS.get(depth, _LIMITS["fast"])
    if tool_name == "web_search" and isinstance(data.get("results"), list):
        rows = []
        for row in data["results"][: limits["search_results"]]:
            if not isinstance(row, dict):
                continue
            item = {k: row[k] for k in ("title", "url", "date", "published_date", "source") if k in row}
            item["snippet"] = _excerpt(str(row.get("snippet", "")), query, limits["snippet"])
            rows.append(item)
        view = {**data, "results": rows}
        if rows != data["results"] or any(
            isinstance(row, dict) and str(row.get("snippet", "")) != item["snippet"]
            for row, item in zip(data["results"], rows)
        ):
            return _recoverable(view, content, workspace)
        return json.dumps(view, ensure_ascii=False, separators=(",", ":"))
    if tool_name == "web_fetch" and isinstance(data.get("text"), str) and len(data["text"]) > limits["fetch"]:
        return _recoverable({**data, "text": _excerpt(data["text"], query, limits["fetch"])}, content, workspace)
    return content


# Compatibility alias used by earlier fast-mode tests and call sites.
fast_evidence_view = bounded_evidence_view


def chart_result(tool_name: str, call_id: str, arguments: dict, result: Any) -> Any:
    """Attach a validated native chart without changing source data or doing I/O."""
    from .report_html.chart_spec import normalize_chart_spec_dict
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            result = parsed
    if isinstance(result, dict) and (result.get("error") or result.get("status", "ok") not in ("ok", "partial", "stale_cache")):
        return result
    if tool_name.startswith("mcp__") and tool_name.endswith("__get_price_trend"):
        from .reports.market_series import MarketSeriesAggregator
        summary = MarketSeriesAggregator.summarize(result, product_name=str(arguments.get("product_name") or arguments.get("product") or ""))
        spec = summary.chart_spec
        if spec and len(set(spec["labels"])) >= 2 and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", x) for x in spec["labels"]):
            result = {**(result if isinstance(result, dict) else {"data": result}), "chart_spec": spec,
                "latest": list(summary.latest), "source_refs": list(summary.source_refs), "data_gaps": list(summary.data_gaps)}
    if isinstance(result, dict) and not result.get("error"):
        spec = normalize_chart_spec_dict(result.get("chart_spec"))
        if spec and len(spec["labels"]) >= 2:
            return {**result, "chart_spec": spec, "chart_id": call_id}
    return result
