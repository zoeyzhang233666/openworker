"""chem-huagongshe-reaction Skill wire (D-119)."""

from __future__ import annotations

from pathlib import Path

from coworker.skills.base import _parse_skill


ROOT = Path(__file__).resolve().parents[1]


def test_chem_huagongshe_reaction_skill_documents_tools_and_boundaries():
    skill = _parse_skill(
        ROOT / "coworker/skills/bundled/chem-huagongshe-reaction/SKILL.md"
    )
    text = skill.instructions
    assert "validate_huagongshe_reaction" in text
    assert "create_huagongshe_reaction" in text
    assert "Lead" in text or "评分" in text
    assert "可见性" in text or "visibility" in text
    assert "确认" in text
    assert "RDKit" in text
    assert skill.name == "chem-huagongshe-reaction"


def test_sales_lobsters_do_not_force_write_reaction_skill():
    for name in (
        "export-sales-lobster",
        "domestic-sales-lobster",
        "opportunity-radar-lobster",
        "export-engagement-lobster",
    ):
        text = (
            ROOT / f"coworker/personas/builtin/{name}.md"
        ).read_text(encoding="utf-8")
        # Optional mention of read tools is fine; do not force write skill in skills: list.
        assert "chem-huagongshe-reaction" not in text or "load_skill" in text
