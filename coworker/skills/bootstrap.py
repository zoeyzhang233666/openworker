"""Seed bundled ChemClaw skills into the global skill store on first run."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..runtime_paths import bundled_skills_dir
from .base import _parse_skill
from .store import SkillStore, validate_name

# Mutable so tests can monkeypatch; defaults to source tree or PyInstaller datas.
BUNDLED_DIR = bundled_skills_dir()


def list_bundled_skill_names() -> set[str]:
    """Return frontmatter names for every skill folder under ``bundled/``."""
    names: set[str] = set()
    if not BUNDLED_DIR.is_dir():
        return names
    for skill_dir in BUNDLED_DIR.iterdir():
        md = skill_dir / "SKILL.md"
        if not skill_dir.is_dir() or not md.is_file():
            continue
        try:
            names.add(validate_name(_parse_skill(md).name))
        except ValueError:
            continue
    return names


def seed_bundled_skills(skill_store: SkillStore | None = None) -> list[str]:
    """Copy bundled skills into the global store when missing. Returns newly installed names.

    Skips names the user previously deleted (``uninstalled_bundled`` in skills-settings).
    Target folder name always matches the skill's frontmatter ``name``.
    """
    store = skill_store or SkillStore()
    installed: list[str] = []
    if not BUNDLED_DIR.is_dir():
        return installed
    uninstalled = store.uninstalled_bundled_names()
    store.global_dir.mkdir(parents=True, exist_ok=True)
    for skill_dir in sorted(BUNDLED_DIR.iterdir(), key=lambda p: p.name):
        if not skill_dir.is_dir():
            continue
        md = skill_dir / "SKILL.md"
        if not md.is_file():
            continue
        try:
            name = validate_name(_parse_skill(md).name)
        except ValueError:
            continue
        if name in uninstalled:
            continue
        target = store.global_dir / name
        if (target / "SKILL.md").is_file():
            continue
        shutil.copytree(skill_dir, target)
        installed.append(name)
    return installed
