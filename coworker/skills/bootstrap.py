"""Seed bundled ChemClaw skills into the global skill store on first run."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..runtime_paths import bundled_skills_dir
from .base import _parse_skill
from .store import SkillStore, validate_name

# Mutable so tests can monkeypatch; defaults to source tree or PyInstaller datas.
BUNDLED_DIR = bundled_skills_dir()

# Skills whose managed lexicon may hot-upgrade without reseeding the whole tree (M3).
_MANAGED_LEXICON_SKILLS = ("chem-content-policy",)

_USER_CSV_HEADER = (
    "rule_id,term,platform,locale,category,severity,action,"
    "replacement_strategy,notes\n"
)


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


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in (version or "").strip().split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts) or (0,)


def _read_version(path: Path) -> str:
    if not path.is_file():
        return "0.0.0"
    text = path.read_text(encoding="utf-8").strip()
    return text or "0.0.0"


def _ensure_user_lexicon(user_csv: Path) -> None:
    if user_csv.is_file():
        return
    user_csv.parent.mkdir(parents=True, exist_ok=True)
    user_csv.write_text(_USER_CSV_HEADER, encoding="utf-8")


def _migrate_legacy_lexicon(installed_skill: Path) -> None:
    """Move pre-M3 ``lexicon/base.csv`` into ``lexicon/managed/`` if needed."""
    lexicon = installed_skill / "references" / "lexicon"
    legacy = lexicon / "base.csv"
    managed_dir = lexicon / "managed"
    managed_csv = managed_dir / "base.csv"
    if managed_csv.is_file() or not legacy.is_file():
        return
    managed_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(legacy), str(managed_csv))


def sync_managed_lexicon(skill_store: SkillStore | None = None) -> list[str]:
    """Hot-upgrade managed lexicon files without touching user.csv.

    Returns skill names whose managed lexicon was updated (or migrated).
    """
    store = skill_store or SkillStore()
    updated: list[str] = []
    if not BUNDLED_DIR.is_dir():
        return updated

    for name in _MANAGED_LEXICON_SKILLS:
        bundled_skill = BUNDLED_DIR / name
        installed_skill = store.global_dir / name
        if not (installed_skill / "SKILL.md").is_file():
            continue
        if not (bundled_skill / "SKILL.md").is_file():
            continue

        bundled_managed = bundled_skill / "references" / "lexicon" / "managed"
        bundled_version_path = bundled_managed / "rule_version.txt"
        if not bundled_managed.is_dir() or not (bundled_managed / "base.csv").is_file():
            continue

        _migrate_legacy_lexicon(installed_skill)

        installed_lexicon = installed_skill / "references" / "lexicon"
        installed_managed = installed_lexicon / "managed"
        installed_version_path = installed_managed / "rule_version.txt"
        user_csv = installed_lexicon / "user.csv"

        # Preserve any pre-existing user overrides before we touch managed files.
        user_before = user_csv.read_bytes() if user_csv.is_file() else None

        bundled_ver = _read_version(bundled_version_path)
        installed_ver = _read_version(installed_version_path)
        needs_sync = (
            not (installed_managed / "base.csv").is_file()
            or _version_tuple(bundled_ver) > _version_tuple(installed_ver)
        )

        if needs_sync:
            if installed_managed.exists():
                shutil.rmtree(installed_managed)
            shutil.copytree(bundled_managed, installed_managed)
            updated.append(name)

        if user_before is not None:
            user_csv.parent.mkdir(parents=True, exist_ok=True)
            user_csv.write_bytes(user_before)
        else:
            _ensure_user_lexicon(user_csv)

    return updated
