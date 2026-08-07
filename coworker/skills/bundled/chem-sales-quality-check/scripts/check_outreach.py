#!/usr/bin/env python3
"""Deterministic quality gate for outreach drafts before human send approval."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


RULE_SET_ID = "chem-sales-quality"
RULE_SET_VERSION = "1.0.0"
PLACEHOLDER_PREFIXES = ("task-provided:", "unknown:", "placeholder:")
FAKE_PHONE = re.compile(r"(\+00\b|000-000|555-01)", re.I)
CURRENCY_AMOUNT = re.compile(
    r"(\$|€|£|USD|EUR|CNY|RMB)\s*\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s*(USD|EUR|CNY|RMB|美元|欧元)",
    re.I,
)
ALREADY_DONE = re.compile(
    r"(already\s+sent|already\s+won|already\s+shipped|sample\s+(?:was\s+)?(?:already\s+)?shipped|已发送|已成交|已寄样|已经发送)",
    re.I,
)
BYPASS_APPROVAL = re.compile(
    r"(bypass\s+approval|skip\s+approval|ignore\s+permission|绕过审批|跳过审批|忽略权限)",
    re.I,
)
VALID_CHANNELS = {"email", "linkedin", "other"}


def _fail(message: str) -> None:
    raise ValueError(message)


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    if set(value) != expected:
        _fail(f"{label} must contain exactly: {', '.join(sorted(expected))}")
    return value


def _require_nonempty_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be a non-empty string")


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return any(lowered.startswith(p) for p in PLACEHOLDER_PREFIXES)


def check_outreach(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate draft shape and apply chem-sales-quality@1.0.0 hard rejects."""
    draft = _exact_keys(
        payload,
        {
            "schema_version",
            "draft_id",
            "language",
            "channel",
            "recipient_role",
            "recipient_email",
            "recipient_name",
            "subject",
            "body",
            "lead_or_opportunity_id",
            "evidence_ids",
            "price_evidence_ids",
            "has_price_claim",
            "has_delivery_claim",
        },
        "draft",
    )
    if draft["schema_version"] != "chemclaw.outreach-draft.v1":
        _fail("unsupported schema_version")
    for key in (
        "draft_id",
        "language",
        "recipient_role",
        "subject",
        "body",
        "lead_or_opportunity_id",
    ):
        _require_nonempty_string(draft[key], key)
    if draft["channel"] not in VALID_CHANNELS:
        _fail("channel is invalid")
    if not isinstance(draft["evidence_ids"], list) or not all(
        isinstance(i, str) and i for i in draft["evidence_ids"]
    ):
        _fail("evidence_ids must be an array of non-empty strings")
    if not isinstance(draft["price_evidence_ids"], list) or not all(
        isinstance(i, str) and i for i in draft["price_evidence_ids"]
    ):
        _fail("price_evidence_ids must be an array of non-empty strings")
    if not isinstance(draft["has_price_claim"], bool) or not isinstance(
        draft["has_delivery_claim"], bool
    ):
        _fail("has_price_claim and has_delivery_claim must be booleans")
    for nullable in ("recipient_email", "recipient_name"):
        value = draft[nullable]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            _fail(f"{nullable} must be null or a non-empty string")

    violations: list[dict[str, str]] = []
    email = draft["recipient_email"]
    if isinstance(email, str):
        if _is_placeholder(email) or "example.com" in email.lower():
            violations.append(
                {
                    "code": "placeholder_email",
                    "message": "recipient_email looks like a placeholder or test address",
                }
            )
        if draft["channel"] == "email" and "@" not in email:
            violations.append(
                {
                    "code": "invalid_email",
                    "message": "email channel requires an address containing @, or null with role-only strategy",
                }
            )

    text = f"{draft['subject']}\n{draft['body']}"
    if FAKE_PHONE.search(text):
        violations.append(
            {"code": "fake_phone", "message": "draft contains a fake phone pattern"}
        )
    if draft["has_price_claim"] and not draft["price_evidence_ids"]:
        if CURRENCY_AMOUNT.search(text):
            violations.append(
                {
                    "code": "unbacked_price",
                    "message": "price claim present without price_evidence_ids",
                }
            )
        else:
            violations.append(
                {
                    "code": "unbacked_price_flag",
                    "message": "has_price_claim is true without price_evidence_ids",
                }
            )
    if draft["has_delivery_claim"] and not draft["evidence_ids"]:
        violations.append(
            {
                "code": "unbacked_delivery",
                "message": "delivery claim present without evidence_ids",
            }
        )
    if ALREADY_DONE.search(text):
        violations.append(
            {
                "code": "false_completion",
                "message": "draft claims already sent, won, or sample shipped",
            }
        )
    if BYPASS_APPROVAL.search(text):
        violations.append(
            {
                "code": "bypass_approval",
                "message": "draft asks to bypass approval or permissions",
            }
        )

    passed = not violations
    return {
        "schema_version": "chemclaw.outreach-gate.output.v1",
        "rule_set": {"id": RULE_SET_ID, "version": RULE_SET_VERSION},
        "draft_id": draft["draft_id"],
        "verdict": "pass" if passed else "blocked",
        "violations": violations,
        "recommended_action": "ready_for_human_send" if passed else "revise_draft",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    output = json.dumps(check_outreach(payload), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    raise SystemExit(main())
