"""Contract tests for chem-inquiry-to-quote."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from coworker.quote import calculate_quote
from coworker.skills.base import SkillLoader, _parse_skill
from coworker.skills.bootstrap import seed_bundled_skills
from coworker.skills.store import SkillStore


ROOT = Path(__file__).resolve().parents[1]
BUNDLED = ROOT / "coworker" / "skills" / "bundled"
PACKAGE = "chem-inquiry-to-quote"
FORMAT_CHECKER = FormatChecker()
RFC3339_DATETIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


@FORMAT_CHECKER.checks("date-time")
def _is_rfc3339_datetime(value: object) -> bool:
    if not isinstance(value, str) or not RFC3339_DATETIME.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(
            value[:-1] + "+00:00" if value.endswith("Z") else value
        )
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads(
        (BUNDLED / PACKAGE / "schemas" / name).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)


def test_skill_frontmatter_and_assets():
    folder = BUNDLED / PACKAGE
    skill = _parse_skill(folder / "SKILL.md")
    assert skill.name == PACKAGE
    assert skill.description.startswith("Use when ")
    combined = skill.instructions + (
        folder / "references" / "inquiry-to-quote-discipline.md"
    ).read_text(encoding="utf-8")
    for needle in (
        "QuoteRun",
        "Inquiry",
        "QuoteDraft",
        "calculate_quote",
        "绝不编造",
        "chem-inquiry-feed",
        "ready_for_human_review",
    ):
        assert needle in combined
    for asset in (
        "schemas/inquiry.schema.json",
        "schemas/quote-draft.schema.json",
        "schemas/quote-run.schema.json",
        "references/inquiry-to-quote-discipline.md",
    ):
        assert (folder / asset).is_file()


def test_schemas_and_forward_no_invented_price():
    inquiry = {
        "schema_version": "chemclaw.inquiry.v1",
        "inquiry_id": "inq-1",
        "source_summary": "Please quote 10 MT sodium benzoate CIF Hamburg",
        "buyer_name": None,
        "currency": "USD",
        "incoterm": "CIF",
        "lines": [
            {
                "line_id": "l1",
                "sku_id": "sku-benzoate",
                "product_name": "sodium benzoate",
                "quantity": 10,
                "unit": "MT",
                "unit_price": None,
            }
        ],
        "unresolved_fields": ["lines[0].unit_price"],
        "status": "NeedsReview",
    }
    _validator("inquiry.schema.json").validate(inquiry)

    calc = calculate_quote(
        {
            "currency": "USD",
            "incoterm": "CIF",
            "lines": [
                {
                    "line_id": "l1",
                    "sku_id": "sku-benzoate",
                    "quantity": 10,
                    "unit": "MT",
                    "unit_price": None,
                }
            ],
        }
    )
    # unit_price None → needs_review path via missing key handling
    assert calc.status in {"needs_review", "error"}
    assert calc.grand_total is None

    draft = {
        "schema_version": "chemclaw.quote-draft.v1",
        "draft_id": "qd-1",
        "inquiry_id": "inq-1",
        "currency": "USD",
        "incoterm": "CIF",
        "lines": [
            {
                "line_id": "l1",
                "sku_id": "sku-benzoate",
                "quantity": "10",
                "unit": "MT",
                "unit_price": "1200.00",
                "line_total": "12000.00",
            }
        ],
        "subtotal": "12000.00",
        "freight": "0.00",
        "tax": "0.00",
        "grand_total": "12000.00",
        "calculator_version": "1.0.0",
        "recommended_action": "ready_for_human_review",
        "status": "draft",
    }
    _validator("quote-draft.schema.json").validate(draft)

    run = {
        "schema_version": "chemclaw.quote-run.v1",
        "run_id": "qr-1",
        "created_at": "2026-08-09T05:00:00Z",
        "updated_at": "2026-08-09T05:10:00Z",
        "status": "complete",
        "inquiry_id": "inq-1",
        "draft_ids": ["qd-1"],
        "calculator_version": "1.0.0",
        "missing_fields": [],
        "warnings": [],
        "next_actions": ["人工审阅报价后决定是否外发"],
    }
    _validator("quote-run.schema.json").validate(run)


def test_seed_inquiry_to_quote_skill(tmp_path: Path):
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))
    assert PACKAGE in installed
    assert SkillLoader([store.global_dir]).get(PACKAGE) is not None
