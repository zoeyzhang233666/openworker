"""Skill / persona wiring for HubSpot create-contact approval (D-109)."""

from __future__ import annotations

from pathlib import Path

from coworker.skills.base import _parse_skill


ROOT = Path(__file__).resolve().parents[1]
ENGAGEMENT = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-sales-engagement"
    / "SKILL.md"
)
DISCIPLINE = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-sales-engagement"
    / "references"
    / "engagement-discipline.md"
)
QUALITY = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-sales-quality-check"
    / "references"
    / "quality-rules.md"
)
PERSONA = (
    ROOT / "coworker" / "personas" / "builtin" / "export-engagement-lobster.md"
)


def test_engagement_documents_create_contact_gate():
    skill = _parse_skill(ENGAGEMENT)
    text = (
        skill.instructions
        + DISCIPLINE.read_text(encoding="utf-8")
        + QUALITY.read_text(encoding="utf-8")
    )
    assert "ready_for_crm_create_contact" in text
    assert "hubspot_create_contact" in text
    assert "ready_for_crm_write" in text
    assert "hubspot_log_note" in text
    assert "hubspot_update_object" in text
    assert "禁止" in text or "不得" in text


def test_export_engagement_lobster_mentions_create_contact():
    text = PERSONA.read_text(encoding="utf-8")
    assert "ready_for_crm_create_contact" in text
    assert "hubspot_create_contact" in text
    assert "D-109" in text or "创建联系人" in text
