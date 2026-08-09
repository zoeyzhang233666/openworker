"""The `calculate_quote` tool — deterministic quote math from explicit numbers.

Does not invent unit prices or quantities. Results are for human-reviewed QuoteDrafts;
draft ≠ send.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import aisuite as ai

from .calc import calculate_quote

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate_quote",
        "description": (
            "Deterministically calculate a chemical sales quote from explicit line "
            "quantities and unit prices. Returns status (ok|needs_review|error), "
            "line totals, subtotal, freight, tax, and grand_total. Never invents "
            "missing prices. Does not send quotes or write CRM."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "currency": {"type": "string", "description": "ISO currency code, e.g. USD."},
                "incoterm": {
                    "type": ["string", "null"],
                    "description": "Optional Incoterm (FOB, CIF, …).",
                },
                "freight": {
                    "type": ["number", "string", "null"],
                    "description": "Freight amount; omit or null for 0.",
                },
                "tax_amount": {
                    "type": ["number", "string", "null"],
                    "description": "Absolute tax amount (mutually exclusive with tax_rate).",
                },
                "tax_rate": {
                    "type": ["number", "string", "null"],
                    "description": "Tax rate fraction, e.g. 0.13 (mutually exclusive with tax_amount).",
                },
                "lines": {
                    "type": "array",
                    "description": "Quote lines with explicit quantity and unit_price.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "line_id": {"type": "string"},
                            "sku_id": {"type": "string"},
                            "quantity": {"type": ["number", "string"]},
                            "unit": {"type": "string"},
                            "unit_price": {"type": ["number", "string"]},
                        },
                        "required": ["sku_id", "quantity", "unit", "unit_price"],
                    },
                },
            },
            "required": ["currency", "lines"],
        },
    },
}


def make_calculate_quote_tool() -> Callable[..., Any]:
    def calculate_quote_tool(
        currency: str,
        lines: list[dict[str, Any]],
        incoterm: Optional[str] = None,
        freight: Any = None,
        tax_amount: Any = None,
        tax_rate: Any = None,
    ) -> dict[str, Any]:
        payload = {
            "currency": currency,
            "lines": lines,
            "incoterm": incoterm,
            "freight": freight,
            "tax_amount": tax_amount,
            "tax_rate": tax_rate,
        }
        try:
            return calculate_quote(payload).to_dict()
        except Exception as exc:
            return {
                "status": "error",
                "currency": None,
                "incoterm": None,
                "lines": [],
                "subtotal": None,
                "freight": None,
                "tax": None,
                "grand_total": None,
                "warnings": [],
                "missing_fields": [],
                "error": f"quote calculation failed: {exc}",
                "calculator_version": "1.0.0",
            }

    calculate_quote_tool.__name__ = "calculate_quote"
    calculate_quote_tool.__doc__ = _SCHEMA["function"]["description"]
    calculate_quote_tool.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="calculate_quote",
        category="utility",
        risk_level="low",
        capabilities=[],
        requires_approval=False,
    )
    calculate_quote_tool.__coworker_schema__ = _SCHEMA
    return calculate_quote_tool
