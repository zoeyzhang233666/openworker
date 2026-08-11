"""Skill / persona wiring for SAM search_sam_opportunities (D-106)."""

from __future__ import annotations

from pathlib import Path

from coworker.skills.base import _parse_skill


ROOT = Path(__file__).resolve().parents[1]
SKILL = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-opportunity-radar"
    / "SKILL.md"
)
WORKFLOW = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-opportunity-radar"
    / "references"
    / "radar-workflow.md"
)
PERSONA = (
    ROOT / "coworker" / "personas" / "builtin" / "opportunity-radar-lobster.md"
)


def test_opportunity_radar_documents_search_sam():
    skill = _parse_skill(SKILL)
    text = skill.instructions + WORKFLOW.read_text(encoding="utf-8")
    assert "search_sam_opportunities" in text
    assert "SAM" in text or "sam.gov" in text.lower()
    assert "禁止伪造" in text or "不得伪造" in text or "不得编造" in text
    assert "sam:default" in text or "平台 Tool" in text


def test_opportunity_radar_lobster_mentions_sam_tool():
    text = PERSONA.read_text(encoding="utf-8")
    assert "search_sam_opportunities" in text
    assert "sam:default" in text or "SAM" in text or "sam.gov" in text.lower()
    assert "境外可选" in text or "TED" in text
    assert "validate_eu_vat" in text
