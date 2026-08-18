"""A-share financial statement tool. Not registered on the global Agent in Run 2."""

from __future__ import annotations

from typing import Any, Callable, Optional

import aisuite as ai

from ..providers.stocks import PublicCNStockProvider

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_cn_stock_financials",
        "description": (
            "Fetch A-share financial statements from Sina CompanyFinanceService "
            "(balance_sheet / income_statement / cash_flow). "
            "financial_indicators is unavailable (Run 0 failed)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "statement_type": {
                    "type": "string",
                    "description": "balance_sheet (default), income_statement, cash_flow.",
                },
            },
            "required": ["symbol"],
        },
    },
}


def make_lookup_cn_stock_financials_tool(
    *, provider: Optional[PublicCNStockProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNStockProvider()

    def lookup_cn_stock_financials(
        symbol: str,
        statement_type: str = "balance_sheet",
    ) -> dict[str, Any]:
        return p.stock_financials(symbol, statement_type=statement_type).to_dict()

    lookup_cn_stock_financials.__name__ = "lookup_cn_stock_financials"
    lookup_cn_stock_financials.__doc__ = _SCHEMA["function"]["description"]
    lookup_cn_stock_financials.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="lookup_cn_stock_financials",
        category="web",
        risk_level="low",
        capabilities=["search", "fetch"],
        requires_approval=False,
    )
    lookup_cn_stock_financials.__coworker_schema__ = _SCHEMA
    return lookup_cn_stock_financials
