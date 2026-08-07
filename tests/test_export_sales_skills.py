"""Contract tests for the first four export-sales bundled Skill packages."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
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
    """Supply the optional date-time check absent from the minimal test runtime."""
    if not isinstance(value, str) or not RFC3339_DATETIME.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return parsed.tzinfo is not None

PACKAGES = {
    "chem-export-prospecting": {
        "assets": [
            "schemas/prospecting-run.schema.json",
            "references/prospecting-workflow.md",
        ],
        "must_include": ["ProspectingRun", "断点", "审批"],
    },
    "chem-product-intelligence": {
        "assets": [
            "schemas/commercial-sku.schema.json",
            "schemas/product-language-map.schema.json",
            "schemas/application-graph.schema.json",
            "references/product-evidence-rules.md",
            "scripts/cas.py",
        ],
        "must_include": ["CommercialSKU", "ApplicationGraph", "CAS", "不得静默选择", "resources_path"],
    },
    "chem-buyer-discovery": {
        "assets": [
            "schemas/search-run.schema.json",
            "references/query-and-dedup-rules.md",
        ],
        "must_include": ["SearchRun", "每轮最多新增四组查询", "不是合格 Lead"],
    },
    "chem-company-qualification": {
        "assets": [
            "schemas/company-evidence-pack.schema.json",
            "references/qualification-and-evidence-rules.md",
        ],
        "must_include": ["CompanyEvidencePack", "Qualified", "货代"],
    },
}


def _load_cas_module():
    path = BUNDLED / "chem-product-intelligence" / "scripts" / "cas.py"
    spec = importlib.util.spec_from_file_location("export_sales_cas", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _schema(package: str, filename: str) -> dict:
    path = BUNDLED / package / "schemas" / filename
    assert path.is_file(), f"missing schema: {path}"
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def _validator(package: str, filename: str) -> Draft202012Validator:
    return Draft202012Validator(_schema(package, filename), format_checker=FORMAT_CHECKER)


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


def _valid_commercial_sku() -> dict:
    return {
        "schema_version": "chemclaw.commercial-sku.v1",
        "sku_id": "sku-ethanol-001",
        "identity_status": "resolved",
        "names": {
            "standard": "Ethanol",
            "aliases": [
                {"term": "Ethyl alcohol", "language": "en", "evidence_ids": ["ev-identity-1"]}
            ],
        },
        "cas": "64-17-5",
        "identity_evidence_ids": [],
        "specification": {
            "grade": "industrial",
            "purity": "99.5%",
            "packaging": "160 kg drum",
            "delivery_form": "liquid",
        },
        "target_uses": [{"name": "solvent", "evidence_ids": ["ev-use-1"]}],
        "excluded_uses": [{"name": "pharmaceutical", "evidence_ids": ["ev-exclusion-1"]}],
        "regulatory_status": [
            {"market": "DE", "status": "verification_required", "evidence_ids": ["ev-reg-1"]}
        ],
        "conflicts": [],
    }


def _valid_language_map() -> dict:
    return {
        "schema_version": "chemclaw.product-language-map.v1",
        "sku_id": "sku-ethanol-001",
        "chemical_synonyms": [
            {"term": "ethyl alcohol", "language": "en", "source_ids": ["source-1"]}
        ],
        "commercial_synonyms": [
            {"term": "industrial alcohol", "language": "en", "source_ids": ["source-2"]}
        ],
        "brands": [],
        "specification_terms": [
            {"term": "anhydrous", "language": "en", "source_ids": ["source-3"]}
        ],
        "applications": [
            {
                "term": "printing ink solvent",
                "language": "en",
                "support": "direct",
                "evidence_ids": ["ev-use-1"],
            }
        ],
        "customer_roles": [
            {"term": "ink manufacturer", "language": "en", "source_ids": ["source-4"]}
        ],
        "local_terms": [
            {"term": "Ethanol Lieferant", "language": "de", "source_ids": ["source-5"]}
        ],
        "exclusion_terms": [
            {"term": "fuel station", "language": "en", "source_ids": ["source-6"]}
        ],
    }


def _valid_application_graph() -> dict:
    return {
        "schema_version": "chemclaw.application-graph.v1",
        "sku_id": "sku-ethanol-001",
        "nodes": [
            {"node_id": "sku-ethanol-001", "type": "sku", "label": "Industrial ethanol"},
            {"node_id": "application-ink", "type": "downstream_product", "label": "Printing ink"},
        ],
        "edges": [
            {
                "edge_id": "edge-1",
                "from_id": "sku-ethanol-001",
                "to_id": "application-ink",
                "relation": "used_in",
                "support": "direct",
                "evidence_ids": ["ev-use-1"],
            }
        ],
    }


def _valid_search_run() -> dict:
    return {
        "schema_version": "chemclaw.search-run.v1",
        "run_id": "search-001",
        "sku_id": "sku-ethanol-001",
        "target_market": {
            "countries": ["DE"],
            "languages": ["de", "en"],
            "customer_types": ["manufacturer"],
            "exclusions": ["logistics"],
        },
        "queries": [
            {
                "query_id": "query-1",
                "round": 1,
                "text": "Ethanol Druckfarben Hersteller Deutschland",
                "language": "de",
                "reason": "Find downstream ink manufacturers",
                "provider": "configured-search",
                "executed_at": "2026-08-07T08:00:00Z",
                "result_count": 12,
                "new_candidate_count": 1,
                "learned_from_source_ids": [],
            }
        ],
        "candidates": [
            {
                "candidate_id": "candidate-1",
                "raw_name": "Example Ink GmbH",
                "country": "DE",
                "candidate_domain": "example.invalid",
                "discovery_evidence_ids": ["source-result-1"],
                "query_ids": ["query-1"],
                "status": "Discovered",
            }
        ],
        "entity_relationships": [],
        "deduplication": {
            "canonical_candidate_ids": ["candidate-1"],
            "duplicate_groups": [],
            "unresolved_pairs": [],
        },
        "stop": {
            "reason": "budget_reached",
            "rounds_executed": 1,
            "total_results": 12,
            "total_new_candidates": 1,
            "consecutive_low_increment_rounds": 0,
            "details": "Configured one-round budget reached",
        },
    }


def _evidence_item() -> dict:
    return {
        "id": "evidence-1",
        "source": {
            "type": "official_website",
            "url": "https://example.invalid/products/ink",
            "file": None,
            "record_id": None,
        },
        "title": "Product page",
        "raw_fact": "The company publishes a printing-ink product page.",
        "supports_claim": "The company manufactures a relevant downstream product.",
        "supports": ["entity", "sku_application", "role_icp"],
        "polarity": "supports",
        "tier": "A",
        "independence_group": "example.invalid",
        "event_date": None,
        "collected_at": "2026-08-07T08:15:00Z",
        "conflict": "none",
    }


def _valid_company_pack(status: str = "Qualified") -> dict:
    pack = {
        "schema_version": "chemclaw.company-evidence-pack.v1",
        "company_id": "company-1",
        "qualification_status": status,
        "entity": {
            "resolution_status": "resolved",
            "canonical_name": "Example Ink GmbH",
            "country": "DE",
            "website": "https://example.invalid",
            "role": "manufacturer",
        },
        "evidence": [_evidence_item()],
        "risks": [],
        "rejection_reasons": [],
        "unresolved_questions": [],
    }
    if status == "NeedsReview":
        pack["entity"]["resolution_status"] = "unresolved"
        pack["entity"]["canonical_name"] = None
        pack["unresolved_questions"] = ["Confirm the legal entity behind the brand"]
    elif status == "Rejected":
        pack["rejection_reasons"] = ["Verified logistics provider outside this ICP"]
    return pack


def _valid_prospecting_run() -> dict:
    return {
        "schema_version": "chemclaw.prospecting-run.v1",
        "run_id": "prospecting-001",
        "created_at": "2026-08-07T07:00:00Z",
        "updated_at": "2026-08-07T09:00:00Z",
        "status": "complete",
        "input": {
            "sku_id": "sku-ethanol-001",
            "request_summary": "Find German printing-ink manufacturers",
            "requested_lead_count": 10,
            "target_markets": [
                {
                    "country": "DE",
                    "regions": [],
                    "languages": ["de", "en"],
                    "customer_types": ["manufacturer"],
                    "exclusions": ["logistics"],
                    "compliance_constraints": ["No outreach without approval"],
                }
            ],
        },
        "versions": {
            "orchestrator_version": "1.0.0",
            "skill_versions": [
                {"skill_id": "chem-export-prospecting", "version": "1.0.0"}
            ],
            "rule_versions": [{"rule_id": "qualification", "version": "1.0.0"}],
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
                "input_ids": ["sku-ethanol-001"],
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
        "qualified_lead_ids": ["company-1"],
        "needs_review_ids": [],
        "rejected_ids": [],
        "budget": {
            "query_limit": 10,
            "query_used": 1,
            "paid_call_limit": 0,
            "paid_call_used": 0,
        },
        "warnings": [],
        "unresolved_questions": [],
        "next_actions": ["Review the qualified lead before drafting outreach"],
    }


def test_export_sales_packages_have_parseable_frontmatter_and_contract_assets():
    """Catch a package omitted from the bundle or stripped of its executable contract."""
    for name, expected in PACKAGES.items():
        folder = BUNDLED / name
        skill_path = folder / "SKILL.md"
        skill = _parse_skill(skill_path)
        frontmatter = skill_path.read_text(encoding="utf-8").split("---", 2)[1]
        assert skill.name == name
        assert skill.description.startswith("Use when ")
        assert any("\u4e00" <= character <= "\u9fff" for character in skill.description)
        assert "\nsource:" not in frontmatter
        assert skill.instructions.strip()
        for phrase in expected["must_include"]:
            assert phrase in skill.instructions
        for relative_path in expected["assets"]:
            asset = folder / relative_path
            assert asset.is_file(), f"{name} missing {relative_path}"
            if asset.suffix == ".json":
                schema = json.loads(asset.read_text(encoding="utf-8"))
                assert schema["type"] == "object"
                assert schema["additionalProperties"] is False
                assert schema["required"]


def test_bootstrap_copies_export_sales_packages_byte_for_byte_and_loader_discovers_them(tmp_path):
    """Catch bootstrap regressing to a SKILL.md-only copy or losing package discovery."""
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))
    assert set(PACKAGES).issubset(installed)

    loader = SkillLoader([store.global_dir])
    for name, expected in PACKAGES.items():
        source = BUNDLED / name
        target = store.global_dir / name
        loaded = loader.get(name)
        assert loaded is not None
        assert loaded.description == _parse_skill(source / "SKILL.md").description
        for relative_path in ["SKILL.md", *expected["assets"]]:
            assert (target / relative_path).read_bytes() == (source / relative_path).read_bytes()


def test_cas_normalization_and_checksum_are_deterministic():
    """Catch accepting a malformed CAS or changing its canonical hyphenated form."""
    cas = _load_cas_module()
    assert cas.normalize_cas(" 64–17–5 ") == "64-17-5"
    assert cas.is_valid_cas("64-17-5") is True
    assert cas.is_valid_cas("7732-18-5") is True
    assert cas.is_valid_cas("64-17-4") is False
    assert cas.is_valid_cas("64-1-75") is False


@pytest.mark.parametrize("value", [None, "", "64/17/5", "64-17-five", 64175])
def test_cas_rejects_malformed_input_without_guessing(value):
    """Catch permissive coercion that could turn arbitrary product text into an identity."""
    cas = _load_cas_module()
    assert cas.is_valid_cas(value) is False
    with pytest.raises((TypeError, ValueError)):
        cas.normalize_cas(value)


def test_all_export_sales_schemas_are_versioned_strict_and_reject_empty_business_strings():
    """Catch permissive contracts that accept empty facts or drift without a version."""
    expected_ids = {
        "prospecting-run.schema.json": "chemclaw.prospecting-run.v1",
        "commercial-sku.schema.json": "chemclaw.commercial-sku.v1",
        "product-language-map.schema.json": "chemclaw.product-language-map.v1",
        "application-graph.schema.json": "chemclaw.application-graph.v1",
        "search-run.schema.json": "chemclaw.search-run.v1",
        "company-evidence-pack.schema.json": "chemclaw.company-evidence-pack.v1",
    }
    schema_paths = [
        BUNDLED / package / relative_path
        for package, expected in PACKAGES.items()
        for relative_path in expected["assets"]
        if relative_path.endswith(".schema.json")
    ]
    assert {path.name for path in schema_paths} == set(expected_ids)

    for path in schema_paths:
        assert path.is_file(), f"missing schema: {path}"
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["$id"] == expected_ids[path.name]
        assert "schema_version" in schema["required"]
        assert schema["properties"]["schema_version"] == {"const": schema["$id"]}
        _assert_strict_objects_and_nonempty_strings(schema)


def test_product_contracts_accept_auditable_records_and_reject_unresolved_resolved_identity():
    sku_validator = _validator("chem-product-intelligence", "commercial-sku.schema.json")
    language_validator = _validator("chem-product-intelligence", "product-language-map.schema.json")
    graph_validator = _validator("chem-product-intelligence", "application-graph.schema.json")

    _assert_valid(sku_validator, _valid_commercial_sku())
    _assert_valid(language_validator, _valid_language_map())
    _assert_valid(graph_validator, _valid_application_graph())

    empty_name = _valid_commercial_sku()
    empty_name["names"]["standard"] = ""
    _assert_invalid(sku_validator, empty_name)

    no_identity_support = _valid_commercial_sku()
    no_identity_support["cas"] = None
    no_identity_support["identity_evidence_ids"] = []
    _assert_invalid(sku_validator, no_identity_support)

    evidence_backed_identity = _valid_commercial_sku()
    evidence_backed_identity["cas"] = None
    evidence_backed_identity["identity_evidence_ids"] = ["ev-identity-1"]
    _assert_valid(sku_validator, evidence_backed_identity)

    unsupported_term = _valid_language_map()
    unsupported_term["local_terms"][0]["source_ids"] = []
    _assert_invalid(language_validator, unsupported_term)

    unsupported_application = _valid_application_graph()
    unsupported_application["edges"][0]["evidence_ids"] = []
    _assert_invalid(graph_validator, unsupported_application)


def test_search_run_records_query_rounds_deduplication_and_rejects_an_empty_candidate():
    validator = _validator("chem-buyer-discovery", "search-run.schema.json")
    valid = _valid_search_run()
    _assert_valid(validator, valid)

    for field in ("raw_name", "country"):
        invalid = deepcopy(valid)
        invalid["candidates"][0][field] = ""
        _assert_invalid(validator, invalid)

    no_discovery_evidence = deepcopy(valid)
    no_discovery_evidence["candidates"][0]["discovery_evidence_ids"] = []
    _assert_invalid(validator, no_discovery_evidence)

    invalid_timestamp = deepcopy(valid)
    invalid_timestamp["queries"][0]["executed_at"] = "2026/08/07 08:00"
    _assert_invalid(validator, invalid_timestamp)


def test_company_evidence_pack_uses_canonical_evidence_item_and_status_gates():
    validator = _validator("chem-company-qualification", "company-evidence-pack.schema.json")
    schema = validator.schema
    evidence_schema = schema["$defs"]["evidenceItem"]
    assert evidence_schema["required"] == [
        "id",
        "source",
        "title",
        "raw_fact",
        "supports_claim",
        "supports",
        "polarity",
        "tier",
        "independence_group",
        "event_date",
        "collected_at",
        "conflict",
    ]
    assert evidence_schema["properties"]["supports"]["items"]["enum"] == [
        "entity",
        "sku_application",
        "role_icp",
        "business_signal",
        "market_fit",
        "contactability",
        "signal_recency",
    ]

    for status in ("Qualified", "NeedsReview", "Rejected"):
        _assert_valid(validator, _valid_company_pack(status))

    qualified_without_evidence = _valid_company_pack()
    qualified_without_evidence["evidence"] = []
    _assert_invalid(validator, qualified_without_evidence)

    qualified_unresolved = _valid_company_pack()
    qualified_unresolved["entity"]["resolution_status"] = "unresolved"
    qualified_unresolved["entity"]["canonical_name"] = None
    _assert_invalid(validator, qualified_unresolved)

    rejected_without_reason = _valid_company_pack("Rejected")
    rejected_without_reason["rejection_reasons"] = []
    _assert_invalid(validator, rejected_without_reason)

    review_without_question = _valid_company_pack("NeedsReview")
    review_without_question["unresolved_questions"] = []
    _assert_invalid(validator, review_without_question)

    source_without_locator = _valid_company_pack()
    source_without_locator["evidence"][0]["source"].update(
        {"url": None, "file": None, "record_id": None}
    )
    _assert_invalid(validator, source_without_locator)

    invalid_date = _valid_company_pack()
    invalid_date["evidence"][0]["collected_at"] = "yesterday"
    _assert_invalid(validator, invalid_date)

    overstated_search_result = _valid_company_pack()
    overstated_search_result["evidence"][0]["source"].update(
        {
            "type": "search_result",
            "url": "https://search.example.invalid/result/1",
        }
    )
    overstated_search_result["evidence"][0]["tier"] = "A"
    _assert_invalid(validator, overstated_search_result)

    overstated_trade_record = _valid_company_pack()
    overstated_trade_record["evidence"][0]["source"].update(
        {"type": "trade_record", "url": None, "record_id": "trade-record-1"}
    )
    overstated_trade_record["evidence"][0]["tier"] = "A"
    _assert_invalid(validator, overstated_trade_record)


def test_company_evidence_item_contract_matches_deterministic_ranking_contract():
    company_schema = _schema(
        "chem-company-qualification", "company-evidence-pack.schema.json"
    )
    ranking_schema = json.loads(
        (
            BUNDLED
            / "chem-lead-ranking"
            / "schemas"
            / "lead-ranking-input.schema.json"
        ).read_text(encoding="utf-8")
    )

    assert company_schema["$defs"]["source"] == ranking_schema["$defs"]["source"]
    assert company_schema["$defs"]["evidenceItem"] == ranking_schema["$defs"]["evidence"]


def test_qualification_instructions_forbid_fake_locators_and_undated_recency_claims():
    package = BUNDLED / "chem-company-qualification"
    for path in (
        package / "SKILL.md",
        package / "references" / "qualification-and-evidence-rules.md",
    ):
        content = path.read_text(encoding="utf-8")
        assert "task-provided:*" in content
        assert "占位" in content
        assert "NeedsReview" in content
        assert "event_date" in content
        assert "signal_recency" in content


def test_prospecting_run_is_resumable_and_complete_requires_a_stage():
    validator = _validator("chem-export-prospecting", "prospecting-run.schema.json")
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

    malformed_checkpoint = deepcopy(valid)
    malformed_checkpoint["stages"][0]["checkpoint"]["saved_at"] = "not-a-date"
    _assert_invalid(validator, malformed_checkpoint)


def test_seeded_cas_cli_executes_from_the_absolute_resources_path(tmp_path):
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    seed_bundled_skills(store)
    loaded = SkillLoader([store.global_dir]).get("chem-product-intelligence")
    assert loaded is not None
    resources_path = Path(loaded.path).resolve()
    script = resources_path / "scripts" / "cas.py"
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    completed = subprocess.run(
        [sys.executable, str(script), "64-17-5"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    assert json.loads(completed.stdout) == {"normalized": "64-17-5", "valid": True}

    rejected = subprocess.run(
        [sys.executable, str(script), "64-17-4"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert rejected.returncode != 0
    assert "checksum" in rejected.stderr.lower()
