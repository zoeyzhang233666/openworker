import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest


SKILL_DIR = Path(__file__).parents[1] / "coworker" / "skills" / "bundled" / "chem-lead-ranking"
SCRIPT_PATH = SKILL_DIR / "scripts" / "score_lead.py"


def test_skill_description_is_a_concise_usage_trigger():
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    description = next(
        line.removeprefix("description:").strip()
        for line in skill_text.splitlines()
        if line.startswith("description:")
    )
    assert description.startswith("Use when ")
    assert len(description) <= 300


def _module():
    spec = importlib.util.spec_from_file_location("chem_lead_ranking", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _evidence(
    evidence_id,
    supports,
    group,
    *,
    tier="A",
    polarity="supports",
    conflict="none",
    source_type="official_website",
):
    return {
        "id": evidence_id,
        "source": {
            "type": source_type,
            "url": f"https://{group}.example/{evidence_id}",
            "file": None,
            "record_id": None,
        },
        "title": f"Evidence {evidence_id}",
        "raw_fact": "The supplied source contains a verifiable business fact.",
        "supports_claim": "The fact supports or contradicts the named lead-ranking field.",
        "supports": supports,
        "polarity": polarity,
        "tier": tier,
        "independence_group": group,
        "event_date": "2026-07-01",
        "collected_at": "2026-07-02T12:00:00Z",
        "conflict": conflict,
    }


def _payload(*, status="Qualified", all_supported=True):
    features = {
        "sku_application": {"evidence_ids": ["e1"]},
        "role_icp": {"evidence_ids": ["e2"]},
        "business_signal": {"evidence_ids": ["e3"]},
        "market_fit": {"evidence_ids": ["e4"]},
        "contactability": {"evidence_ids": ["e5"]},
        "signal_recency": {"evidence_ids": ["e6"]},
    }
    evidence = [
        _evidence("e1", ["sku_application"], "company"),
        _evidence("e2", ["role_icp", "entity"], "registry"),
        _evidence("e3", ["business_signal"], "trade"),
        _evidence("e4", ["market_fit"], "market"),
        _evidence("e5", ["contactability"], "contact"),
        _evidence("e6", ["signal_recency"], "signal"),
    ]
    if not all_supported:
        features = {key: {"evidence_ids": []} for key in features}
        evidence = []
    return {
        "schema_version": "chemclaw.lead-ranking.input.v1",
        "as_of": "2026-08-07",
        "rule_set": {
            "id": "chem-lead-fit",
            "version": "1.0.0",
            "weights": {
                "sku_application": 30,
                "role_icp": 20,
                "business_signal": 20,
                "market_fit": 10,
                "contactability": 10,
                "signal_recency": 10,
            },
        },
        "lead": {
            "id": "lead-acme",
            "qualification_status": status,
            "entity_resolution": "resolved",
            "features": features,
        },
        "evidence": evidence,
    }


def test_scores_fixed_six_weight_total_and_keeps_confidence_separate():
    result = _module().score_lead(_payload())

    assert result["lead_fit"]["score"] == 100.0
    assert result["evidence_confidence"]["score"] == 100.0
    assert result["recommended_action"] == "prioritize_contact"
    assert [item["points"] for item in result["lead_fit"]["components"]] == [30.0, 20.0, 20.0, 10.0, 10.0, 10.0]


def test_tier_and_polarity_derive_exact_points_without_model_percentages():
    payload = _payload(status="NeedsReview")
    payload["evidence"][0]["tier"] = "B"
    payload["lead"]["features"]["role_icp"]["evidence_ids"].append("e7")
    payload["evidence"].append(_evidence("e7", ["role_icp"], "independent", tier="B", polarity="contradicts"))

    result = _module().score_lead(payload)

    assert result["lead_fit"]["components"][0]["support_pct"] == 70
    assert result["lead_fit"]["components"][0]["points"] == 21.0
    assert result["lead_fit"]["components"][1]["support_pct"] == 100
    assert result["lead_fit"]["components"][1]["contradiction_pct"] == 70
    assert result["lead_fit"]["components"][1]["points"] == 6.0
    assert result["lead_fit"]["score"] == 77.0


def test_unknown_fields_do_not_penalize_fit_but_lower_confidence():
    payload = _payload(status="NeedsReview", all_supported=False)
    payload["lead"]["entity_resolution"] = "unresolved"
    result = _module().score_lead(payload)

    assert result["lead_fit"]["score"] == 0.0
    assert result["lead_fit"]["unscored_weight"] == 100
    assert result["lead_fit"]["negative_evidence"] == []
    assert result["evidence_confidence"]["score"] == 0.0
    assert result["recommended_action"] == "research_first"


def test_event_based_evidence_without_event_date_is_not_treated_as_fresh():
    payload = _payload()
    payload["evidence"][2]["event_date"] = None

    result = _module().score_lead(payload)

    assert result["evidence_confidence"]["factors"]["freshness"] == 83.3
    assert result["evidence_confidence"]["score"] == 98.3


def test_signal_recency_cannot_reference_evidence_without_an_event_date():
    payload = _payload()
    payload["evidence"][5]["event_date"] = None

    with pytest.raises(ValueError, match="signal_recency.*event_date"):
        _module().score_lead(payload)


def test_one_a_source_cannot_prioritize_contact_without_independent_evidence():
    payload = _payload()
    payload["evidence"] = [_evidence("e1", ["entity", "sku_application", "role_icp", "business_signal", "market_fit", "contactability", "signal_recency"], "single-source")]
    for feature in payload["lead"]["features"].values():
        feature["evidence_ids"] = ["e1"]

    result = _module().score_lead(payload)

    assert result["lead_fit"]["score"] == 100.0
    assert result["evidence_confidence"]["score"] == 69.9
    assert result["recommended_action"] == "research_first"


@pytest.mark.parametrize(
    ("source_type", "allowed_tier", "forbidden_tier"),
    [
        ("public_procurement", "B", "A"),
        ("industry_directory", "B", "A"),
        ("search_result", "C", "B"),
        ("other", "D", "C"),
    ],
)
def test_source_type_caps_the_best_permitted_evidence_tier(
    source_type, allowed_tier, forbidden_tier
):
    allowed = _payload(status="NeedsReview")
    allowed["evidence"][0] = _evidence(
        "e1",
        ["sku_application"],
        "source-group",
        tier=allowed_tier,
        source_type=source_type,
    )
    assert _module().score_lead(allowed)["lead_fit"]["components"][0]["support_pct"]

    forbidden = deepcopy(allowed)
    forbidden["evidence"][0]["tier"] = forbidden_tier
    with pytest.raises(ValueError, match="source type"):
        _module().score_lead(forbidden)


def test_material_conflict_caps_confidence_and_never_prioritizes_contact():
    payload = _payload()
    payload["evidence"][2]["conflict"] = "material"

    result = _module().score_lead(payload)

    assert result["evidence_confidence"]["score"] == 39.9
    assert result["recommended_action"] == "research_first"


def test_needs_review_never_recommends_contact_and_rejected_is_excluded():
    review = _module().score_lead(_payload(status="NeedsReview"))
    rejected = _module().score_lead(_payload(status="Rejected"))

    assert review["recommended_action"] == "research_first"
    assert rejected["recommended_action"] == "exclude"


@pytest.mark.parametrize(
    "defect",
    [
        lambda value: value["lead"]["features"].update({"invented": {"evidence_ids": []}}),
        lambda value: value["rule_set"]["weights"].update({"sku_application": 29}),
        lambda value: value["rule_set"].update({"version": "9.9.9"}),
        lambda value: value["evidence"][0].update({"event_date": "2026/07/01"}),
        lambda value: value["lead"]["features"]["sku_application"].update({"evidence_ids": ["not-present"]}),
        lambda value: value["evidence"][0]["source"].update({"url": None, "file": None, "record_id": None}),
    ],
    ids=[
        "unknown_feature_key",
        "wrong_fixed_weight",
        "unsupported_rule_version",
        "invalid_date",
        "unknown_evidence_reference",
        "source_needs_locator",
    ],
)
def test_rejects_malformed_contracts(defect):
    payload = _payload()
    defect(payload)

    with pytest.raises(ValueError):
        _module().score_lead(payload)


def test_rejects_discovered_or_unresolved_qualified_leads_before_scoring():
    with pytest.raises(ValueError, match="Discovered"):
        _module().score_lead(_payload(status="Discovered"))
    unresolved = _payload()
    unresolved["lead"]["entity_resolution"] = "unresolved"
    with pytest.raises(ValueError, match="resolved"):
        _module().score_lead(unresolved)


@pytest.mark.parametrize(
    "locator_field,locator_value",
    [
        ("url", "task-provided:oral-sku"),
        ("url", "unknown:german-distributor"),
        ("file", "placeholder:user-said-so"),
        ("record_id", "TASK-PROVIDED:import-claim"),
    ],
)
def test_rejects_placeholder_source_locators(locator_field, locator_value):
    payload = _payload()
    payload["evidence"][0]["source"] = {
        "type": "official_website",
        "url": None,
        "file": None,
        "record_id": None,
    }
    payload["evidence"][0]["source"][locator_field] = locator_value

    with pytest.raises(ValueError, match="placeholder locator"):
        _module().score_lead(payload)


def test_oral_only_forward_scenario_scores_needs_review_without_inventing_sources():
    """User only said DE distributor + sodium benzoate + recent import; no firm identity."""
    payload = _payload(status="NeedsReview", all_supported=False)
    payload["lead"]["id"] = "oral-de-benzoate"
    payload["lead"]["entity_resolution"] = "unresolved"

    result = _module().score_lead(payload)

    assert result["lead_fit"]["score"] == 0.0
    assert result["evidence_confidence"]["score"] == 0.0
    assert result["recommended_action"] == "research_first"
    assert "entity" in result["evidence_confidence"]["missing_fields"]


def test_qualified_requires_entity_role_and_strong_or_independent_relevance_evidence():
    missing_entity = _payload()
    missing_entity["evidence"][1]["supports"] = ["role_icp"]
    with pytest.raises(ValueError, match="entity evidence"):
        _module().score_lead(missing_entity)

    only_one_medium = _payload()
    only_one_medium["evidence"][0]["tier"] = "B"
    with pytest.raises(ValueError, match="one A or two independent B"):
        _module().score_lead(only_one_medium)

    two_independent_medium = deepcopy(only_one_medium)
    two_independent_medium["lead"]["features"]["sku_application"]["evidence_ids"].append(
        "e7"
    )
    two_independent_medium["evidence"].append(
        _evidence("e7", ["sku_application"], "second-relevance-source", tier="B")
    )
    assert _module().score_lead(two_independent_medium)["lead_fit"]["score"] == 91.0


def test_cli_uses_an_absolute_resources_path(tmp_path):
    payload_path = tmp_path / "lead.json"
    payload_path.write_text(json.dumps(_payload()), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH.resolve()), str(payload_path.resolve())],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout)["recommended_action"] == "prioritize_contact"


def test_output_validates_against_strict_schema_when_validator_is_available():
    input_schema = json.loads((SKILL_DIR / "schemas" / "lead-ranking-input.schema.json").read_text(encoding="utf-8"))
    output_schema = json.loads((SKILL_DIR / "schemas" / "lead-ranking-output.schema.json").read_text(encoding="utf-8"))
    result = _module().score_lead(_payload())
    assert input_schema["additionalProperties"] is False
    assert output_schema["additionalProperties"] is False
    assert output_schema["properties"]["rule_set"]["properties"] == {
        "id": {"const": "chem-lead-fit"},
        "version": {"const": "1.0.0"},
    }
    assert output_schema["properties"]["lead_fit"]["properties"]["components"] == {
        "type": "array",
        "minItems": 6,
        "maxItems": 6,
        "items": {"$ref": "#/$defs/component"},
    }
    try:
        import jsonschema
    except ImportError:
        assert set(result) == {"schema_version", "rule_set", "lead_id", "lead_fit", "evidence_confidence", "risks", "recommended_action"}
    else:
        jsonschema.Draft202012Validator(output_schema).validate(result)
