"""Skill / persona wiring for HubSpot update-object / create-task approval (D-127)."""

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


def test_engagement_documents_update_object_and_create_task_gates():
    skill = _parse_skill(ENGAGEMENT)
    text = (
        skill.instructions
        + DISCIPLINE.read_text(encoding="utf-8")
        + QUALITY.read_text(encoding="utf-8")
    )
    assert "ready_for_crm_update_object" in text
    assert "hubspot_update_object" in text
    assert "ready_for_crm_create_task" in text
    assert "hubspot_create_task" in text
    assert "ready_for_crm_write" in text
    assert "hubspot_log_note" in text
    assert "禁止自动写 CRM" in text or "不得在未获用户明确指令时调用任何 HubSpot 写工具" in text


def test_export_engagement_lobster_mentions_update_and_task():
    text = PERSONA.read_text(encoding="utf-8")
    assert "ready_for_crm_update_object" in text
    assert "hubspot_update_object" in text
    assert "ready_for_crm_create_task" in text
    assert "hubspot_create_task" in text
    assert "D-127" in text or "字段更新" in text
