"""A-share feature datasets. Not registered on the global Agent in Run 2."""

from __future__ import annotations

from typing import Any, Callable, Optional

import aisuite as ai

from ..providers.stocks import PublicCNStockProvider

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_cn_stock_feature",
        "description": (
            "Fetch a keyless A-share market-feature dataset. "
            "dataset enum: lhb_list, lhb_detail, margin_summary, "
            "northbound_history, northbound_holdings, "
            "performance_forecast, performance_express, financial_indicators. "
            "Holdings and indicators may return source_unavailable."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dataset": {"type": "string"},
                "symbol": {"type": "string"},
                "start_date": {"type": "string", "description": "YYYYMMDD"},
                "end_date": {"type": "string", "description": "YYYYMMDD"},
            },
            "required": ["dataset"],
        },
    },
}


def make_lookup_cn_stock_feature_tool(
    *, provider: Optional[PublicCNStockProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNStockProvider()

    def lookup_cn_stock_feature(
        dataset: str,
        symbol: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> dict[str, Any]:
        return p.stock_feature(
            dataset,
            symbol=symbol or None,
            start_date=start_date,
            end_date=end_date,
        ).to_dict()

    lookup_cn_stock_feature.__name__ = "lookup_cn_stock_feature"
    lookup_cn_stock_feature.__doc__ = _SCHEMA["function"]["description"]
    lookup_cn_stock_feature.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="lookup_cn_stock_feature",
        category="web",
        risk_level="low",
        capabilities=["search", "fetch"],
        requires_approval=False,
    )
    lookup_cn_stock_feature.__coworker_schema__ = _SCHEMA
    return lookup_cn_stock_feature
