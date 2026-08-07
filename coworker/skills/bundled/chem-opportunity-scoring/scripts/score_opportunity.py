#!/usr/bin/env python3
"""Calculate deterministic opportunity fit and evidence confidence for one opportunity draft."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


FEATURE_WEIGHTS = {
    "signal_recency": 25,
    "entity": 20,
    "sku_relevance": 25,
    "urgency": 15,
    "actionability": 15,
}
RULE_SET_ID = "chem-opportunity-fit"
RULE_SET_VERSION = "1.0.0"
FEATURE_ORDER = tuple(FEATURE_WEIGHTS)
TIER_VALUES = {"A": 100, "B": 70, "C": 35, "D": 10}
VALID_STATUSES = {"Watch", "NeedsReview", "Actionable", "Rejected"}
VALID_ENTITY_RESOLUTION = {"resolved": 100, "partial": 50, "unresolved": 0}
VALID_SKU_RELEVANCE = {"pending", "related", "unrelated", "unknown"}
VALID_CONFLICTS = {"none", "unresolved", "material"}
SOURCE_TYPES = {
    "official_website",
    "government_registry",
    "trade_record",
    "industry_directory",
    "public_procurement",
    "b2b_directory",
    "search_result",
    "user_file",
    "other",
}
SOURCE_TIER_CEILINGS = {
    "official_website": "A",
    "government_registry": "A",
    "public_procurement": "B",
    "trade_record": "B",
    "industry_directory": "B",
    "user_file": "C",
    "b2b_directory": "C",
    "search_result": "C",
    "other": "D",
}
PLACEHOLDER_LOCATOR_PREFIXES = (
    "task-provided:",
    "unknown:",
    "placeholder:",
)
SIGNAL_TYPES = {
    "inquiry",
    "tender",
    "trade",
    "capacity",
    "hiring",
    "price",
    "exhibition",
    "other",
}


def _fail(message: str) -> None:
    raise ValueError(message)


def _is_placeholder_locator(value: str) -> bool:
    lowered = value.strip().lower()
    return any(lowered.startswith(prefix) for prefix in PLACEHOLDER_LOCATOR_PREFIXES)


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    if set(value) != expected:
        _fail(f"{label} must contain exactly: {', '.join(sorted(expected))}")
    return value


def _parse_date(value: Any, label: str, *, nullable: bool = False) -> date | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        _fail(f"{label} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO date") from exc
    if parsed.isoformat() != value:
        _fail(f"{label} must be an ISO date")
    return parsed


def _parse_datetime(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or "T" not in value:
        _fail(f"{label} must be an ISO date-time with timezone")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO date-time with timezone") from exc
    if parsed.tzinfo is None:
        _fail(f"{label} must be an ISO date-time with timezone")
    return parsed


def _round(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _band(score: float) -> str:
    return "high" if score >= 70 else "medium" if score >= 40 else "low"


def _require_nonempty_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be a non-empty string")


def _validate(
    payload: dict[str, Any],
) -> tuple[date, dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    _exact_keys(payload, {"schema_version", "as_of", "rule_set", "opportunity", "signals"}, "payload")
    if payload["schema_version"] != "chemclaw.opportunity-scoring.input.v1":
        _fail("unsupported schema_version")
    as_of = _parse_date(payload["as_of"], "as_of")
    assert as_of is not None

    rule_set = _exact_keys(payload["rule_set"], {"id", "version", "weights"}, "rule_set")
    if rule_set["id"] != RULE_SET_ID or rule_set["version"] != RULE_SET_VERSION:
        _fail(f"rule_set must be {RULE_SET_ID} version {RULE_SET_VERSION}")
    if rule_set["weights"] != FEATURE_WEIGHTS:
        _fail("rule_set.weights must be the fixed 25/20/25/15/15 mapping")

    opportunity = _exact_keys(
        payload["opportunity"],
        {"id", "status", "entity_resolution", "sku_relevance", "features"},
        "opportunity",
    )
    _require_nonempty_string(opportunity["id"], "opportunity.id")
    status = opportunity["status"]
    if status not in VALID_STATUSES:
        _fail("opportunity.status is invalid")
    if opportunity["entity_resolution"] not in VALID_ENTITY_RESOLUTION:
        _fail("opportunity.entity_resolution is invalid")
    if opportunity["sku_relevance"] not in VALID_SKU_RELEVANCE:
        _fail("opportunity.sku_relevance is invalid")
    if status == "Actionable" and opportunity["entity_resolution"] != "resolved":
        _fail("Actionable opportunities require entity_resolution=resolved")
    if status == "Actionable" and opportunity["sku_relevance"] != "related":
        _fail("Actionable opportunities require sku_relevance=related")

    features = opportunity["features"]
    if not isinstance(features, dict) or set(features) != set(FEATURE_ORDER):
        _fail("opportunity.features must contain exactly the five fixed dimensions")

    signals = payload["signals"]
    if not isinstance(signals, list):
        _fail("signals must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    signal_keys = {
        "id",
        "signal_type",
        "summary",
        "source",
        "title",
        "raw_fact",
        "supports",
        "polarity",
        "tier",
        "independence_group",
        "event_date",
        "collected_at",
        "conflict",
    }
    for index, item in enumerate(signals):
        item = _exact_keys(item, signal_keys, f"signals[{index}]")
        signal_id = item["id"]
        if not isinstance(signal_id, str) or not signal_id or signal_id in by_id:
            _fail("signal ids must be unique non-empty strings")
        if item["signal_type"] not in SIGNAL_TYPES:
            _fail("signal_type is invalid")
        source = _exact_keys(
            item["source"], {"type", "url", "file", "record_id"}, f"signals[{index}].source"
        )
        if source["type"] not in SOURCE_TYPES:
            _fail("signal source.type is invalid")
        locators = []
        for locator in ("url", "file", "record_id"):
            value = source[locator]
            if value is not None and (not isinstance(value, str) or not value.strip()):
                _fail(f"signal source.{locator} must be null or a non-empty string")
            if isinstance(value, str) and value.strip():
                if _is_placeholder_locator(value):
                    _fail(
                        "signal source uses a placeholder locator; keep oral-only "
                        "claims as NeedsReview and request a real url/file/record_id"
                    )
                locators.append(value)
        if not locators:
            _fail("signal source needs at least one non-empty locator")
        for key in ("summary", "title", "raw_fact", "independence_group"):
            _require_nonempty_string(item[key], f"signals[{index}].{key}")
        if item["tier"] not in TIER_VALUES:
            _fail("signal tier is invalid")
        tier_ceiling = SOURCE_TIER_CEILINGS[source["type"]]
        if TIER_VALUES[item["tier"]] > TIER_VALUES[tier_ceiling]:
            _fail(f"signal tier exceeds the {tier_ceiling} ceiling for its source type")
        if item["polarity"] not in {"supports", "contradicts"}:
            _fail("signal polarity is invalid")
        if (
            not isinstance(item["supports"], list)
            or not item["supports"]
            or len(set(item["supports"])) != len(item["supports"])
            or not set(item["supports"]) <= set(FEATURE_ORDER)
        ):
            _fail("signal supports must name unique known fields")
        event_date = _parse_date(item["event_date"], f"signals[{index}].event_date", nullable=True)
        collected_at = _parse_datetime(item["collected_at"], f"signals[{index}].collected_at")
        if (event_date and event_date > as_of) or collected_at.date() > as_of:
            _fail("signal dates cannot be after as_of")
        if item["conflict"] not in VALID_CONFLICTS:
            _fail("signal conflict is invalid")
        by_id[signal_id] = item

    for dimension in FEATURE_ORDER:
        feature = _exact_keys(features[dimension], {"signal_ids"}, f"opportunity.features.{dimension}")
        ids = feature["signal_ids"]
        if not isinstance(ids, list) or len(set(ids)) != len(ids) or not all(
            isinstance(i, str) and i for i in ids
        ):
            _fail(f"{dimension}.signal_ids must be unique non-empty strings")
        for signal_id in ids:
            item = by_id.get(signal_id)
            if not item:
                _fail(f"{dimension} references unknown signal")
            if dimension not in item["supports"]:
                _fail(f"{dimension} signal must support that dimension")
            if dimension == "signal_recency" and item["event_date"] is None:
                _fail("signal_recency evidence requires a concrete event_date")

    if status == "Actionable":
        entity_ok = [
            by_id[sid]
            for sid in features["entity"]["signal_ids"]
            if by_id[sid]["polarity"] == "supports" and by_id[sid]["conflict"] == "none"
        ]
        if not entity_ok:
            _fail("Actionable opportunities require positive, conflict-free entity signals")
        dated = [item for item in signals if item["event_date"] is not None]
        if not dated:
            _fail("Actionable opportunities require at least one signal with event_date")
    return as_of, opportunity, signals, by_id


def _feature_signals(
    opportunity: dict[str, Any], by_id: dict[str, dict[str, Any]], dimension: str
) -> list[dict[str, Any]]:
    return [by_id[signal_id] for signal_id in opportunity["features"][dimension]["signal_ids"]]


def _confidence(
    as_of: date,
    opportunity: dict[str, Any],
    signals: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> tuple[float, dict[str, float], list[str]]:
    coverage = {
        dimension: _feature_signals(opportunity, by_id, dimension) for dimension in FEATURE_ORDER
    }
    relevant = {item["id"]: item for items in coverage.values() for item in items}
    relevant_list = list(relevant.values())
    source_quality = Decimal(
        sum(max((TIER_VALUES[item["tier"]] for item in items), default=0) for items in coverage.values())
    ) / Decimal(len(FEATURE_ORDER))
    groups = {item["independence_group"] for item in relevant_list}
    independence = Decimal(min(len(groups), 3) * 100) / Decimal(3) if groups else Decimal(0)
    entity_resolution = Decimal(VALID_ENTITY_RESOLUTION[opportunity["entity_resolution"]])
    key_coverage = Decimal(sum(bool(items) for items in coverage.values()) * 100) / Decimal(
        len(FEATURE_ORDER)
    )
    freshest_by_group: dict[str, int] = {}
    for item in relevant_list:
        event_date = _parse_date(item["event_date"], "event_date", nullable=True)
        if event_date is None:
            freshness = 0
        else:
            age_days = (as_of - event_date).days
            freshness = (
                100
                if age_days <= 365
                else 60
                if age_days <= 730
                else 25
                if age_days <= 1825
                else 0
            )
        group = item["independence_group"]
        freshest_by_group[group] = max(freshest_by_group.get(group, 0), freshness)
    freshness = (
        Decimal(sum(freshest_by_group.values())) / Decimal(len(freshest_by_group))
        if freshest_by_group
        else Decimal(0)
    )
    conflicts = {item["conflict"] for item in signals}
    conflict = (
        Decimal(0)
        if not signals or "material" in conflicts
        else Decimal(50)
        if "unresolved" in conflicts
        else Decimal(100)
    )
    factors = {
        "source_quality": _round(source_quality),
        "independence": _round(independence),
        "entity_resolution": _round(entity_resolution),
        "key_field_coverage": _round(key_coverage),
        "freshness": _round(freshness),
        "conflict": _round(conflict),
    }
    score = (
        Decimal("0.30") * source_quality
        + Decimal("0.20") * independence
        + Decimal("0.15") * entity_resolution
        + Decimal("0.20") * key_coverage
        + Decimal("0.10") * freshness
        + Decimal("0.05") * conflict
    )
    if len(groups) < 2 or "unresolved" in conflicts:
        score = min(score, Decimal("69.9"))
    if "material" in conflicts:
        score = min(score, Decimal("39.9"))
    return _round(score), factors, [field for field, items in coverage.items() if not items]


def score_opportunity(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and score one opportunity draft without external I/O."""
    as_of, opportunity, signals, by_id = _validate(payload)
    components: list[dict[str, Any]] = []
    fit_total = Decimal(0)
    unscored_weight = 0
    negative_evidence: list[str] = []
    for dimension, weight in FEATURE_WEIGHTS.items():
        items = _feature_signals(opportunity, by_id, dimension)
        support = max(
            (TIER_VALUES[item["tier"]] for item in items if item["polarity"] == "supports"),
            default=0,
        )
        contradiction = max(
            (TIER_VALUES[item["tier"]] for item in items if item["polarity"] == "contradicts"),
            default=0,
        )
        points = Decimal(weight) * Decimal(support - contradiction) / Decimal(100)
        fit_total += points
        state = (
            "unknown"
            if not support and not contradiction
            else "mixed"
            if support and contradiction
            else "supported"
            if support
            else "contradicted"
        )
        if state == "unknown":
            unscored_weight += weight
        if contradiction:
            negative_evidence.append(dimension)
        components.append(
            {
                "dimension": dimension,
                "weight": weight,
                "points": _round(points),
                "support_pct": support,
                "contradiction_pct": contradiction,
                "state": state,
                "signal_ids": opportunity["features"][dimension]["signal_ids"],
            }
        )
    fit_score = _round(max(Decimal(0), min(Decimal(100), fit_total)))
    confidence_score, factors, missing_fields = _confidence(as_of, opportunity, signals, by_id)
    fit_band, confidence_band = _band(fit_score), _band(confidence_score)
    conflicts = {item["conflict"] for item in signals}
    status = opportunity["status"]
    if status == "Rejected":
        action = "exclude"
    elif status in {"NeedsReview", "Watch"} or "material" in conflicts:
        action = "research_first" if status == "NeedsReview" or "material" in conflicts else "watch"
    elif fit_band == "high" and confidence_band == "high" and status == "Actionable":
        action = "outreach_now"
    elif fit_band == "high":
        action = "research_first"
    elif fit_band == "medium" and confidence_band == "high":
        action = "watch"
    else:
        action = "pause"
    risks = [f"contradictory_{dimension}" for dimension in negative_evidence]
    if "material" in conflicts:
        risks.append("material_evidence_conflict")
    elif "unresolved" in conflicts:
        risks.append("unresolved_evidence_conflict")
    return {
        "schema_version": "chemclaw.opportunity-scoring.output.v1",
        "rule_set": {"id": payload["rule_set"]["id"], "version": payload["rule_set"]["version"]},
        "opportunity_id": opportunity["id"],
        "opportunity_score": {
            "score": fit_score,
            "band": fit_band,
            "components": components,
            "unscored_weight": unscored_weight,
            "negative_evidence": negative_evidence,
        },
        "evidence_confidence": {
            "score": confidence_score,
            "band": confidence_band,
            "factors": factors,
            "missing_fields": missing_fields,
        },
        "risks": risks,
        "recommended_action": action,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input JSON file")
    parser.add_argument("--output", type=Path, help="Output JSON file (default: stdout)")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    output = json.dumps(score_opportunity(payload), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    raise SystemExit(main())
