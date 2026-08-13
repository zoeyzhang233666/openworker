"""Regression corpus for chem platform rewrite (M2)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
BUNDLED = ROOT / "coworker" / "skills" / "bundled"
CORPUS = ROOT / "docs" / "chemclaw" / "platform-rewrite" / "corpus" / "cases"
LEXICON = (
    BUNDLED / "chem-content-policy" / "references" / "lexicon" / "managed" / "base.csv"
)
HOOK_SCHEMA = BUNDLED / "chem-hook-cta-pack" / "schemas" / "hook-cta-pack.schema.json"


def _load_script(skill: str, script_name: str):
    path = BUNDLED / skill / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(f"{skill}_{script_name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _case_paths() -> list[Path]:
    return sorted(CORPUS.glob("*.json"))


def test_corpus_has_at_least_twelve_cases() -> None:
    paths = _case_paths()
    assert len(paths) >= 12
    ids = {p.stem for p in paths}
    assert "01-safe-xhs" in ids
    assert "10-hook-cta-safe" in ids
    assert "12-risky-alt-product" in ids


@pytest.mark.parametrize("case_path", _case_paths(), ids=lambda p: p.stem)
def test_corpus_case(case_path: Path) -> None:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    expect = case["expect"]
    assert case["id"] == case_path.stem
    assert case["platform"] in ("xiaohongshu", "douyin", "x")
    assert case["source"].strip()
    assert isinstance(case["brief"], dict)

    scan = _load_script("chem-content-policy", "scan_content.py")
    # Scan the draft/output text when present; otherwise source (risky fixtures).
    text = case.get("output") or case["source"]
    scan_result = scan.scan_content(text, lexicon_path=LEXICON)
    assert scan_result["blocked"] is expect["scan_blocked"], case["id"]

    for forbidden in expect.get("must_not_contain") or []:
        assert forbidden not in text, f"{case['id']}: found {forbidden!r}"

    if expect.get("validate_hook_schema"):
        hook = case["hook_pack"]
        schema = json.loads(HOOK_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(hook)
        assert hook.get("facts_unchanged") is True

    if "gate_verdict" in expect or "gate_verdict_in" in expect:
        check = _load_script("chem-content-quality-check", "check_content.py")
        result = check.check_content(
            {
                "source_text": case["source"],
                "output_text": case["output"],
                "brief": case["brief"],
                "target_platform": case["platform"],
                "required_sections": case.get("required_sections") or [],
                "policy_hits": [],
            }
        )
        if "gate_verdict" in expect:
            assert result["verdict"] == expect["gate_verdict"], (
                case["id"],
                result,
            )
        else:
            assert result["verdict"] in expect["gate_verdict_in"], (
                case["id"],
                result,
            )
