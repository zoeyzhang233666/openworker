"""Contract tests for chem-opportunity-radar."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from coworker.skills.base import SkillLoader, _parse_skill
from coworker.skills.bootstrap import seed_bundled_skills
from coworker.skills.store import SkillStore


ROOT = Path(__file__).resolve().parents[1]
BUNDLED = ROOT / "coworker" / "skills" / "bundled"
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


PACKAGE = "chem-opportunity-radar"
ASSETS = [
    "schemas/opportunity-radar-run.schema.json",
    "references/radar-workflow.md",
]
MUST_INCLUDE = [
    "OpportunityRadarRun",
    "chem-opportunity-scoring",
    "NeedsReview",
    "task-provided",
    "chem-newbiz-lead",
]


def _validator() -> Draft202012Validator:
    schema = json.loads(
        (BUNDLED / PACKAGE / "schemas" / "opportunity-radar-run.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)


def _valid_run() -> dict:
    return {
        "schema_version": "chemclaw.opportunity-radar-run.v1",
        "run_id": "radar-001",
        "created_at": "2026-08-07T07:00:00Z",
        "updated_at": "2026-08-07T08:00:00Z",
        "status": "complete",
        "input": {
            "sku_id": "sku-benzoate",
            "request_summary": "苯甲酸钠相关招标商机",
            "signal_types": ["tender"],
            "markets": [{"country": "CN", "regions": ["江苏"]}],
        },
        "versions": {
            "orchestrator_version": "1.0.0",
            "skill_versions": [{"skill_id": PACKAGE, "version": "1.0.0"}],
            "rule_versions": [{"rule_id": "chem-opportunity-fit", "version": "1.0.0"}],
        },
        "providers": [
            {
                "provider_id": "configured-search",
                "version": "2026-08-07",
                "status": "available",
                "calls_made": 0,
                "failure": None,
            }
        ],
        "stages": [
            {
                "stage_id": "stage-collect",
                "name": "signal_collect",
                "status": "complete",
                "skill_id": PACKAGE,
                "skill_version": "1.0.0",
                "rule_version": None,
                "started_at": "2026-08-07T07:10:00Z",
                "updated_at": "2026-08-07T07:20:00Z",
                "completed_at": "2026-08-07T07:20:00Z",
                "input_ids": ["sku-benzoate"],
                "output_ids": [],
                "signal_ids": [],
                "failure": None,
                "checkpoint": {
                    "artifact_id": "cp-1",
                    "saved_at": "2026-08-07T07:20:00Z",
                },
            }
        ],
        "signal_ids": [],
        "opportunity_ids": [],
        "needs_review_ids": ["oral-gap"],
        "rejected_ids": [],
        "budget": {
            "query_limit": 10,
            "query_used": 0,
            "paid_call_limit": 0,
            "paid_call_used": 0,
        },
        "warnings": [],
        "unresolved_questions": ["缺少招标 URL 或文件"],
        "next_actions": ["请用户提供来源后再评分"],
    }


def test_radar_package_frontmatter_and_assets():
    folder = BUNDLED / PACKAGE
    skill = _parse_skill(folder / "SKILL.md")
    assert skill.name == PACKAGE
    assert skill.description.startswith("Use when ")
    assert any("\u4e00" <= c <= "\u9fff" for c in skill.description)
    for phrase in MUST_INCLUDE:
        assert phrase in skill.instructions
    for relative in ASSETS:
        assert (folder / relative).is_file()


def test_bootstrap_copies_radar_package(tmp_path):
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))
    assert PACKAGE in installed
    assert "chem-opportunity-scoring" in installed
    loaded = SkillLoader([store.global_dir]).get(PACKAGE)
    assert loaded is not None
    source = BUNDLED / PACKAGE
    target = store.global_dir / PACKAGE
    for relative in ["SKILL.md", *ASSETS]:
        assert (target / relative).read_bytes() == (source / relative).read_bytes()


def test_radar_run_schema_complete_requires_stage():
    validator = _validator()
    valid = _valid_run()
    assert not list(validator.iter_errors(valid))
    empty = deepcopy(valid)
    empty["stages"] = []
    assert list(validator.iter_errors(empty))


def test_workflow_forbids_mcp_defaults_and_placeholders():
    content = (BUNDLED / PACKAGE / "references" / "radar-workflow.md").read_text(
        encoding="utf-8"
    )
    for required in ("chem-newbiz-lead", "chem-inquiry-feed", "task-provided:", "NeedsReview"):
        assert required in content
