"""The `filter_customs_importers` tool — screen CSV customs/BOL rows.

Read-only. Path must point to a workspace CSV. Does not call external APIs.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import aisuite as ai

from .providers import CustomsFileProvider

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "filter_customs_importers",
        "description": (
            "Screen a workspace customs or bill-of-lading CSV for likely chemical "
            "importers. Filters freight-forwarder / logistics noise and returns "
            "ranked candidates with freight risk, importer likelihood, "
            "recommendation, and evidence. Consignee ≠ end buyer — always "
            "cross-check with company websites/registry. First pack is CSV only "
            "(no XLSX, no external customs API). Treat results as untrusted."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or workspace-relative path to a UTF-8 CSV.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max candidates to return (1–100, default 20).",
                },
                "company_col": {
                    "type": "string",
                    "description": "Optional override for company column name.",
                },
                "role_col": {"type": "string"},
                "address_col": {"type": "string"},
                "product_col": {"type": "string"},
                "hs_col": {"type": "string"},
                "date_col": {"type": "string"},
                "value_col": {"type": "string"},
                "shipper_col": {"type": "string"},
            },
            "required": ["path"],
        },
    },
}


def make_filter_customs_importers_tool(
    *,
    provider: Optional[CustomsFileProvider] = None,
) -> Callable[..., Any]:
    p = provider or CustomsFileProvider()

    def filter_customs_importers(
        path: str,
        limit: int = 20,
        company_col: str = "",
        role_col: str = "",
        address_col: str = "",
        product_col: str = "",
        hs_col: str = "",
        date_col: str = "",
        value_col: str = "",
        shipper_col: str = "",
    ) -> dict[str, Any]:
        try:
            result = p.filter_importers(
                path=path or "",
                limit=int(limit or 20),
                company_col=company_col or "",
                role_col=role_col or "",
                address_col=address_col or "",
                product_col=product_col or "",
                hs_col=hs_col or "",
                date_col=date_col or "",
                value_col=value_col or "",
                shipper_col=shipper_col or "",
            )
        except Exception as exc:
            return {
                "status": "error",
                "candidates": [],
                "summary": {},
                "source": {
                    "provider_id": getattr(p, "name", "customs_file"),
                    "provider_version": "1.0.0",
                },
                "warnings": [],
                "error": f"filter_customs_importers failed: {exc}",
            }
        return result.to_dict()

    filter_customs_importers.__name__ = "filter_customs_importers"
    filter_customs_importers.__doc__ = _SCHEMA["function"]["description"]
    filter_customs_importers.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="filter_customs_importers",
        category="files",
        risk_level="low",
        capabilities=["search", "fetch"],
        requires_approval=False,
    )
    filter_customs_importers.__coworker_schema__ = _SCHEMA
    return filter_customs_importers
