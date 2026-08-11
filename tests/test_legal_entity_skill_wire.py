"""Skill wiring for GLEIF legal entity Tool (D-096)."""

from __future__ import annotations

from pathlib import Path

from coworker.skills.base import _parse_skill


ROOT = Path(__file__).resolve().parents[1]
SKILL = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-company-qualification"
    / "SKILL.md"
)
RULES = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-company-qualification"
    / "references"
    / "qualification-and-evidence-rules.md"
)


def test_company_qualification_documents_lookup_tool():
    skill = _parse_skill(SKILL)
    text = skill.instructions + RULES.read_text(encoding="utf-8")
    assert "lookup_legal_entity" in text
    assert "GLEIF" in text
    assert "USCC" in text or "统一社会信用" in text or "cn_registry" in text
    assert "validate_eu_vat" in text
    assert "government_registry" in text
    assert "NeedsReview" in text
    assert "不得编造 LEI" in text or "不得伪造 LEI" in text
    assert "不在本 Skill 内直接访问" in text or "平台 Provider" in text
