"""Contract tests for chem-sales-engagement."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from coworker.skills.base import SkillLoader, _parse_skill
from coworker.skills.bootstrap import seed_bundled_skills
from coworker.skills.store import SkillStore


ROOT = Path(__file__).resolve().parents[1]
BUNDLED = ROOT / "coworker" / "skills" / "bundled"
PACKAGE = "chem-sales-engagement"
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


def _valid_draft(**overrides) -> dict:
    base = {
        "schema_version": "chemclaw.outreach-draft.v1",
        "draft_id": "draft-de-dist-1",
        "language": "de",
        "channel": "email",
        "recipient_role": "Purchasing Manager / Technical Buyer",
        "recipient_email": None,
        "recipient_name": None,
        "subject": "Natriumbenzoat – Lieferantenanfrage",
        "body": (
            "Guten Tag, wir bieten Natriumbenzoat in Lebensmittelqualität an. "
            "Gerne senden wir COA und Spezifikation nach Erhalt Ihrer Kontaktdaten."
        ),
        "lead_or_opportunity_id": "lead-de-distributor-1",
        "evidence_ids": ["ev-sku-1"],
        "price_evidence_ids": [],
        "has_price_claim": False,
        "has_delivery_claim": False,
    }
    base.update(overrides)
    return base


def _valid_plan() -> dict:
    return {
        "schema_version": "chemclaw.followup-plan.v1",
        "plan_id": "plan-1",
        "lead_or_opportunity_id": "lead-de-distributor-1",
        "steps": [
            {
                "day_offset": 0,
                "purpose": "首封岗位开发信",
                "draft_outline": "介绍 SKU + 请求正确采购岗位邮箱",
            },
            {
                "day_offset": 7,
                "purpose": "礼貌跟进",
                "draft_outline": "确认是否收到、是否需要样品流程说明",
            },
        ],
        "stop_conditions": ["明确拒绝", "14 天无回复后暂停并待补证"],
        "human_checkpoints": ["确认真实收件邮箱后再提交发送审批"],
    }


def _valid_run() -> dict:
    return {
        "schema_version": "chemclaw.engagement-run.v1",
        "run_id": "eng-001",
        "created_at": "2026-08-07T09:00:00Z",
        "updated_at": "2026-08-07T10:00:00Z",
        "status": "complete",
        "input": {
            "lead_or_opportunity_id": "lead-de-distributor-1",
            "request_summary": "写德国分销商开发信",
            "sku_id": "sku-benzoate",
            "target_market": "DE",
            "preferred_channel": "email",
            "language": "de",
            "known_contact_email": None,
        },
        "versions": {
            "orchestrator_version": "1.0.0",
            "skill_versions": [
                {"skill_id": PACKAGE, "version": "1.0.0"},
                {"skill_id": "chem-sales-quality-check", "version": "1.0.0"},
            ],
            "rule_versions": [
                {"rule_id": "chem-sales-quality", "version": "1.0.0"}
            ],
        },
        "stages": [
            {
                "stage_id": "s1",
                "name": "strategy",
                "status": "complete",
                "skill_id": PACKAGE,
                "skill_version": "1.0.0",
                "started_at": "2026-08-07T09:05:00Z",
                "updated_at": "2026-08-07T09:10:00Z",
                "completed_at": "2026-08-07T09:10:00Z",
                "failure": None,
            },
            {
                "stage_id": "s2",
                "name": "draft",
                "status": "complete",
                "skill_id": PACKAGE,
                "skill_version": "1.0.0",
                "started_at": "2026-08-07T09:10:00Z",
                "updated_at": "2026-08-07T09:30:00Z",
                "completed_at": "2026-08-07T09:30:00Z",
                "failure": None,
            },
            {
                "stage_id": "s3",
                "name": "quality_gate",
                "status": "complete",
                "skill_id": "chem-sales-quality-check",
                "skill_version": "1.0.0",
                "started_at": "2026-08-07T09:30:00Z",
                "updated_at": "2026-08-07T09:35:00Z",
                "completed_at": "2026-08-07T09:35:00Z",
                "failure": None,
            },
        ],
        "draft_ids": ["draft-de-dist-1"],
        "followup_plan_ids": ["plan-1"],
        "quality_gate": {
            "verdict": "pass",
            "recommended_action": "ready_for_human_send",
            "rule_set": {"id": "chem-sales-quality", "version": "1.0.0"},
        },
        "warnings": ["无已知个人邮箱，仅岗位策略"],
        "unresolved_questions": ["请补充德国分销商真实采购邮箱"],
        "next_actions": ["人工确认联系人后提交发送审批", "待补证：采购邮箱"],
    }


def test_skill_frontmatter_and_assets():
    folder = BUNDLED / PACKAGE
    skill = _parse_skill(folder / "SKILL.md")
    assert skill.name == PACKAGE
    assert skill.description.startswith("Use when ")
    for asset in (
        "schemas/engagement-run.schema.json",
        "schemas/outreach-draft.schema.json",
        "schemas/followup-plan.schema.json",
        "references/engagement-discipline.md",
    ):
        assert (folder / asset).is_file()
    combined = skill.instructions + (
        folder / "references" / "engagement-discipline.md"
    ).read_text(encoding="utf-8")
    for needle in (
        "EngagementRun",
        "OutreachDraft",
        "FollowupPlan",
        "ready_for_human_send",
        "task-provided",
        "chem-sales-quality-check",
    ):
        assert needle in combined


def test_schemas_accept_valid_contracts():
    _validator("outreach-draft.schema.json").validate(_valid_draft())
    _validator("followup-plan.schema.json").validate(_valid_plan())
    _validator("engagement-run.schema.json").validate(_valid_run())


def test_draft_rejects_missing_role():
    bad = _valid_draft()
    del bad["recipient_role"]
    errors = list(_validator("outreach-draft.schema.json").iter_errors(bad))
    assert errors


def test_forward_germany_distributor_no_email_role_only():
    """「写德国分销商开发信」无邮箱 → 岗位策略 + 补证，不造邮箱。"""
    draft = _valid_draft()
    assert draft["recipient_email"] is None
    assert "Purchasing" in draft["recipient_role"] or "Buyer" in draft["recipient_role"]
    assert "@" not in draft["body"]
    run = _valid_run()
    assert run["input"]["known_contact_email"] is None
    assert any("补证" in a or "邮箱" in a for a in run["next_actions"])
    assert not any(
        isinstance(a, str) and a.count("@") and "example.com" in a.lower()
        for a in run["next_actions"]
    )


def test_seed_engagement_skill(tmp_path: Path):
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))
    assert PACKAGE in installed
    loader = SkillLoader([store.global_dir])
    assert loader.get(PACKAGE) is not None
