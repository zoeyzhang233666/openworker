"""Contract tests for chem-opportunity-scoring."""

from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest


SKILL_DIR = (
    Path(__file__).parents[1]
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-opportunity-scoring"
)
SCRIPT_PATH = SKILL_DIR / "scripts" / "score_opportunity.py"


def _module():
    spec = importlib.util.spec_from_file_location("chem_opportunity_scoring", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _signal(
    signal_id,
    supports,
    group,
    *,
    tier="A",
    polarity="supports",
    conflict="none",
    event_date="2026-07-01",
    source_type="official_website",
):
    if source_type == "public_procurement" and tier == "A":
        tier = "B"
    return {
        "id": signal_id,
        "signal_type": "tender",
        "summary": "Public tender mentions sodium benzoate",
        "source": {
            "type": source_type,
            "url": f"https://{group}.example/{signal_id}",
            "file": None,
            "record_id": None,
        },
        "title": f"Signal {signal_id}",
        "raw_fact": "A dated tender notice references the product.",
        "supports": supports,
        "polarity": polarity,
        "tier": tier,
        "independence_group": group,
        "event_date": event_date,
        "collected_at": "2026-07-02T12:00:00Z",
        "conflict": conflict,
    }


def _payload(*, status="Actionable", all_supported=True):
    features = {
        "signal_recency": {"signal_ids": ["s1"]},
        "entity": {"signal_ids": ["s2"]},
        "sku_relevance": {"signal_ids": ["s3"]},
        "urgency": {"signal_ids": ["s4"]},
        "actionability": {"signal_ids": ["s5"]},
    }
    signals = [
        _signal("s1", ["signal_recency"], "tender"),
        _signal("s2", ["entity"], "registry", source_type="government_registry", tier="A"),
        _signal("s3", ["sku_relevance"], "sku"),
        _signal("s4", ["urgency"], "deadline"),
        _signal("s5", ["actionability"], "contact"),
    ]
    if not all_supported:
        features = {key: {"signal_ids": []} for key in features}
        signals = []
    return {
        "schema_version": "chemclaw.opportunity-scoring.input.v1",
        "as_of": "2026-08-07",
        "rule_set": {
            "id": "chem-opportunity-fit",
            "version": "1.0.0",
            "weights": {
                "signal_recency": 25,
                "entity": 20,
                "sku_relevance": 25,
                "urgency": 15,
                "actionability": 15,
            },
        },
        "opportunity": {
            "id": "opp-1",
            "status": status,
            "entity_resolution": "resolved" if status == "Actionable" else "unresolved",
            "sku_relevance": "related" if status == "Actionable" else "unknown",
            "features": features,
        },
        "signals": signals,
    }


def test_skill_description_is_usage_trigger():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    description = next(
        line.removeprefix("description:").strip().strip('"')
        for line in text.splitlines()
        if line.startswith("description:")
    )
    assert description.startswith("Use when ")


def test_scores_fixed_five_weight_total():
    result = _module().score_opportunity(_payload())
    assert result["opportunity_score"]["score"] == 100.0
    assert [item["points"] for item in result["opportunity_score"]["components"]] == [
        25.0,
        20.0,
        25.0,
        15.0,
        15.0,
    ]
    assert result["recommended_action"] == "outreach_now"


def test_unknown_fields_do_not_penalize_fit_but_lower_confidence():
    payload = _payload(status="NeedsReview", all_supported=False)
    result = _module().score_opportunity(payload)
    assert result["opportunity_score"]["score"] == 0.0
    assert result["opportunity_score"]["unscored_weight"] == 100
    assert result["evidence_confidence"]["score"] == 0.0
    assert result["recommended_action"] == "research_first"


def test_signal_recency_requires_event_date():
    payload = _payload()
    payload["signals"][0]["event_date"] = None
    with pytest.raises(ValueError, match="signal_recency.*event_date"):
        _module().score_opportunity(payload)


def test_rejects_placeholder_locators():
    payload = _payload()
    payload["signals"][0]["source"]["url"] = "task-provided:oral-tender"
    with pytest.raises(ValueError, match="placeholder locator"):
        _module().score_opportunity(payload)


def test_actionable_requires_dated_entity_and_related_sku():
    payload = _payload()
    payload["opportunity"]["entity_resolution"] = "unresolved"
    with pytest.raises(ValueError, match="resolved"):
        _module().score_opportunity(payload)

    payload = _payload()
    for item in payload["signals"]:
        item["event_date"] = None
    payload["opportunity"]["features"]["signal_recency"]["signal_ids"] = []
    with pytest.raises(ValueError, match="event_date"):
        _module().score_opportunity(payload)


def test_oral_only_forward_scenario_is_needs_review():
    payload = _payload(status="NeedsReview", all_supported=False)
    payload["opportunity"]["id"] = "oral-benzoate-tender"
    result = _module().score_opportunity(payload)
    assert result["recommended_action"] == "research_first"
    assert result["opportunity_score"]["score"] == 0.0


def test_cli_writes_output(tmp_path):
    payload_path = tmp_path / "in.json"
    payload_path.write_text(json.dumps(_payload()), encoding="utf-8")
    out = tmp_path / "out.json"
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH.resolve()), str(payload_path), "--output", str(out)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert json.loads(out.read_text(encoding="utf-8"))["recommended_action"] == "outreach_now"
