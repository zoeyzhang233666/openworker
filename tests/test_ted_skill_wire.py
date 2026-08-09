"""Skill / persona wiring for TED search_tenders (D-101)."""

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


def test_opportunity_radar_documents_search_tenders():
    skill = _parse_skill(SKILL)
    text = skill.instructions + WORKFLOW.read_text(encoding="utf-8")
    assert "search_tenders" in text
    assert "TED" in text
    assert "禁止伪造" in text or "不得伪造" in text
    assert "不在本 Skill 内嵌" in text or "平台 Tool" in text


def test_opportunity_radar_lobster_mentions_ted_tool():
    text = PERSONA.read_text(encoding="utf-8")
    assert "search_tenders" in text
    assert "TED" in text
