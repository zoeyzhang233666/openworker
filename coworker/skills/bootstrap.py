"""Seed bundled ChemClaw skills into the global skill store on first run."""

from __future__ import annotations

import shutil
from pathlib import Path

from .store import SkillStore

BUNDLED_DIR = Path(__file__).resolve().parent / "bundled"


def seed_bundled_skills(skill_store: SkillStore | None = None) -> list[str]:
    """Copy bundled skills into the global store when missing. Returns newly installed names."""
    store = skill_store or SkillStore()
    installed: list[str] = []
    if not BUNDLED_DIR.is_dir():
        return installed
    store.global_dir.mkdir(parents=True, exist_ok=True)
    for skill_dir in sorted(BUNDLED_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").is_file():
            continue
        target = store.global_dir / skill_dir.name
        if (target / "SKILL.md").is_file():
            continue
        shutil.copytree(skill_dir, target)
        installed.append(skill_dir.name)
    return installed
