"""The `format_lead_list` tool — deterministic Markdown/CSV lead list for human operation."""

from __future__ import annotations

from typing import Any, Callable

import aisuite as ai

from .format import format_lead_list

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "format_lead_list",
        "description": (
            "Format a ChemClaw lead list into Markdown summary and CSV text. "
            "Input must include scored/qualified leads with company and sales_status. "
            "Does not send email or write CRM. Use for human-operable prospecting deliverables."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "list_id": {"type": "string"},
                "title": {"type": "string"},
                "sku_summary": {"type": "string"},
                "market_summary": {"type": "string"},
                "rule_version": {"type": "string"},
                "leads": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "company": {"type": "string"},
                            "customer_type": {"type": "string"},
                            "fit_score": {"type": ["number", "string", "null"]},
                            "evidence_confidence": {"type": ["number", "string", "null"]},
                            "match_reason": {"type": "string"},
                            "key_evidence": {"type": "string"},
                            "latest_signal": {"type": "string"},
                            "risks_gaps": {"type": "string"},
                            "next_action": {"type": "string"},
                            "sales_status": {
                                "type": "string",
                                "enum": [
                                    "new",
                                    "needs_review",
                                    "contactable",
                                    "contacted",
                                    "replied",
                                    "opportunity",
                                    "excluded",
                                ],
                            },
                            "notes": {"type": "string"},
                            "exclude_reason": {"type": "string"},
                        },
                        "required": ["company", "sales_status"],
                    },
                },
            },
            "required": ["leads"],
        },
    },
}


def make_format_lead_list_tool() -> Callable[..., Any]:
    def format_lead_list_tool(
        leads: list[dict[str, Any]],
        list_id: str = "lead-list",
        title: str = "客户清单",
        sku_summary: str = "",
        market_summary: str = "",
        rule_version: str = "chem-lead-fit@1.0.0",
    ) -> dict[str, Any]:
        payload = {
            "list_id": list_id,
            "title": title,
            "sku_summary": sku_summary,
            "market_summary": market_summary,
            "rule_version": rule_version,
            "leads": leads,
        }
        try:
            return format_lead_list(payload).to_dict()
        except Exception as exc:
            return {
                "status": "error",
                "markdown": "",
                "csv": "",
                "counts": {},
                "formatter_version": "1.0.0",
                "error": f"format_lead_list failed: {exc}",
            }

    format_lead_list_tool.__name__ = "format_lead_list"
    format_lead_list_tool.__doc__ = _SCHEMA["function"]["description"]
    format_lead_list_tool.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="format_lead_list",
        category="utility",
        risk_level="low",
        capabilities=[],
        requires_approval=False,
    )
    format_lead_list_tool.__coworker_schema__ = _SCHEMA
    return format_lead_list_tool
