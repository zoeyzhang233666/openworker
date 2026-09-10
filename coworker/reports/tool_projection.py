"""Engine-side projection of large chem MCP payloads (D-202)."""

from __future__ import annotations

import json
from typing import Any

from .market_series import MarketSeriesAggregator
from .product_aliases import resolve_chem_product_name


def rewrite_price_tool_arguments(arguments: dict[str, Any] | None) -> dict[str, Any]:
    args = dict(arguments or {})
    for key in ("product_name", "product", "q", "query"):
        if key in args and isinstance(args[key], str):
            args[key] = resolve_chem_product_name(args[key])
    return args


def should_project_market_tool(tool_name: str) -> bool:
    lowered = (tool_name or "").lower()
    return "get_price_trend" in lowered or "get_compound_prices" in lowered


def project_market_tool_result(
    result: Any,
    *,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> Any:
    """Replace bulky price payloads with a bounded summary the model can use directly."""
    if not should_project_market_tool(tool_name):
        return result
    args = arguments or {}
    product = resolve_chem_product_name(
        str(args.get("product_name") or args.get("product") or "")
    )
    if isinstance(result, dict) and result.get("error"):
        return result
    summary = MarketSeriesAggregator.summarize(result, product_name=product)
    payload = {
        "status": "ok",
        "product_name": summary.product_name or product,
        "summary": summary.to_dict(),
        "note": (
            "结构化摘要已由 ChemClaw 预先计算；禁止用 shell 或 read_file 解析原始大回包。"
            "若 observations=0，如实说明缺口并尝试已映射的规范品名。"
        ),
    }
    if summary.chart_spec:
        payload["chart_spec"] = summary.chart_spec
    return payload


def project_market_tool_result_json(
    result: Any,
    *,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> str:
    projected = project_market_tool_result(
        result, tool_name=tool_name, arguments=arguments
    )
    if isinstance(projected, str):
        return projected
    return json.dumps(projected, ensure_ascii=False, indent=2)
