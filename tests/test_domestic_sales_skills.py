"""Contract tests for the domestic-sales bundled Skill package."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest
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


PACKAGE = {
    "name": "chem-domestic-prospecting",
    "assets": [
        "schemas/prospecting-run.schema.json",
        "references/domestic-prospecting-workflow.md",
    ],
    "must_include": [
        "ProspectingRun",
        "断点",
        "审批",
        "统一社会信用代码",
        "NeedsReview",
        "task-provided:*",
    ],
}


def _schema() -> dict:
    path = BUNDLED / PACKAGE["name"] / "schemas" / "prospecting-run.schema.json"
    assert path.is_file(), f"missing schema: {path}"
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_schema(), format_checker=FORMAT_CHECKER)


def _assert_valid(validator: Draft202012Validator, instance: dict) -> None:
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    assert not errors, "\n".join(error.message for error in errors)


def _assert_invalid(validator: Draft202012Validator, instance: dict) -> None:
    assert list(validator.iter_errors(instance)), "instance unexpectedly passed schema validation"


def _assert_strict_objects_and_nonempty_strings(node: object, path: str = "$") -> None:
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type == "object":
            assert node.get("additionalProperties") is False, f"{path} is not a strict object"
        accepts_string = node_type == "string" or (
            isinstance(node_type, list) and "string" in node_type
        )
        if accepts_string:
            assert any(
                key in node for key in ("minLength", "enum", "const", "pattern", "format")
            ), f"{path} accepts an unconstrained/empty business string"
        for key, value in node.items():
            _assert_strict_objects_and_nonempty_strings(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _assert_strict_objects_and_nonempty_strings(value, f"{path}/{index}")


def _valid_prospecting_run() -> dict:
    return {
        "schema_version": "chemclaw.prospecting-run.v1",
        "run_id": "domestic-prospecting-001",
        "created_at": "2026-08-07T07:00:00Z",
        "updated_at": "2026-08-07T09:00:00Z",
        "status": "complete",
        "input": {
            "sku_id": "sku-sodium-benzoate-001",
            "request_summary": "江苏园区食品添加剂下游厂",
            "requested_lead_count": 10,
            "target_markets": [
                {
                    "country": "CN",
                    "regions": ["江苏"],
                    "languages": ["zh"],
                    "customer_types": ["食品添加剂下游厂"],
                    "exclusions": ["物流", "货代"],
                    "compliance_constraints": ["No outreach without approval"],
                }
            ],
        },
        "versions": {
            "orchestrator_version": "1.0.0",
            "skill_versions": [
                {"skill_id": "chem-domestic-prospecting", "version": "1.0.0"}
            ],
            "rule_versions": [{"rule_id": "domestic-qualification", "version": "1.0.0"}],
        },
        "providers": [
            {
                "provider_id": "configured-search",
                "version": "2026-08-07",
                "status": "available",
                "calls_made": 1,
                "failure": None,
            }
        ],
        "stages": [
            {
                "stage_id": "stage-discovery",
                "name": "discovery",
                "status": "complete",
                "skill_id": "chem-buyer-discovery",
                "skill_version": "1.0.0",
                "rule_version": None,
                "started_at": "2026-08-07T07:10:00Z",
                "updated_at": "2026-08-07T07:30:00Z",
                "completed_at": "2026-08-07T07:30:00Z",
                "input_ids": ["sku-sodium-benzoate-001"],
                "output_ids": ["search-001"],
                "query_ids": ["query-1"],
                "evidence_ids": ["source-result-1"],
                "failure": None,
                "checkpoint": {
                    "artifact_id": "checkpoint-discovery-1",
                    "saved_at": "2026-08-07T07:30:00Z",
                },
            }
        ],
        "candidate_ids": ["candidate-1"],
        "qualified_lead_ids": [],
        "needs_review_ids": ["candidate-1"],
        "rejected_ids": [],
        "budget": {
            "query_limit": 10,
            "query_used": 1,
            "paid_call_limit": 0,
            "paid_call_used": 0,
        },
        "warnings": [],
        "unresolved_questions": ["缺少统一社会信用代码与官网证据"],
        "next_actions": ["补证后再评分"],
    }


def test_domestic_sales_package_has_parseable_frontmatter_and_contract_assets():
    folder = BUNDLED / PACKAGE["name"]
    skill_path = folder / "SKILL.md"
    skill = _parse_skill(skill_path)
    frontmatter = skill_path.read_text(encoding="utf-8").split("---", 2)[1]
    assert skill.name == PACKAGE["name"]
    assert skill.description.startswith("Use when ")
    assert any("\u4e00" <= character <= "\u9fff" for character in skill.description)
    assert "\nsource:" not in frontmatter
    assert skill.instructions.strip()
    for phrase in PACKAGE["must_include"]:
        assert phrase in skill.instructions
    for relative_path in PACKAGE["assets"]:
        asset = folder / relative_path
        assert asset.is_file(), f"missing {relative_path}"
        if asset.suffix == ".json":
            schema = json.loads(asset.read_text(encoding="utf-8"))
            assert schema["type"] == "object"
            assert schema["additionalProperties"] is False
            assert schema["required"]
            assert schema["$id"] == "chemclaw.prospecting-run.v1"
            assert schema["properties"]["schema_version"]["const"] == "chemclaw.prospecting-run.v1"


def test_bootstrap_copies_domestic_package_byte_for_byte_and_loader_discovers_it(tmp_path):
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))
    assert PACKAGE["name"] in installed

    source = BUNDLED / PACKAGE["name"]
    target = store.global_dir / PACKAGE["name"]
    loaded = SkillLoader([store.global_dir]).get(PACKAGE["name"])
    assert loaded is not None
    assert loaded.description == _parse_skill(source / "SKILL.md").description
    for relative_path in ["SKILL.md", *PACKAGE["assets"]]:
        assert (target / relative_path).read_bytes() == (source / relative_path).read_bytes()


def test_domestic_prospecting_schema_is_strict_and_rejects_empty_business_strings():
    schema = _schema()
    _assert_strict_objects_and_nonempty_strings(schema)
    validator = _validator()
    valid = _valid_prospecting_run()
    _assert_valid(validator, valid)

    empty_country = deepcopy(valid)
    empty_country["input"]["target_markets"][0]["country"] = ""
    _assert_invalid(validator, empty_country)


def test_domestic_prospecting_run_complete_requires_a_stage():
    validator = _validator()
    valid = _valid_prospecting_run()
    _assert_valid(validator, valid)

    no_stage = deepcopy(valid)
    no_stage["stages"] = []
    _assert_invalid(validator, no_stage)

    blocked_without_failure = deepcopy(valid)
    blocked_without_failure["status"] = "blocked"
    blocked_without_failure["stages"][0]["status"] = "blocked"
    blocked_without_failure["stages"][0]["failure"] = None
    _assert_invalid(validator, blocked_without_failure)


def test_domestic_workflow_reference_covers_cn_rules_and_placeholder_ban():
    content = (
        BUNDLED
        / PACKAGE["name"]
        / "references"
        / "domestic-prospecting-workflow.md"
    ).read_text(encoding="utf-8")
    for required in (
        "统一社会信用代码",
        "园区",
        "货代",
        "手机",
        "微信",
        "NeedsReview",
        "task-provided:*",
        "断点",
    ):
        assert required in content
