"""Loose package scan for ChemClaw persona co-install (D-066 / D-069).

A package may mix Agent manifests (persona ``*.md``) and Skill folders (any depth
with ``SKILL.md``). When OpenClaw ``IDENTITY.md`` / ``SOUL.md`` are present, workspace
markdown is composed into one ChemClaw persona (not installed as separate agents).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..skills.base import _parse_skill
from ..skills.store import validate_name
from .manifest import ManifestError, load_manifest_file
from .openclaw_compose import (
    GENERATED_DIR,
    OPENCLAW_WORKSPACE_FILES,
    compose_openclaw_persona,
)

# Paths that are never "content" for the ignored list.
_JUNK_NAMES = {
    ".ds_store",
    ".git",
    ".gitignore",
    ".gitattributes",
    "__macosx",
    "license",
    "license.md",
    "license.txt",
    "readme",
    "readme.md",
    "readme.txt",
    "changelog",
    "changelog.md",
    "notice",
    "notice.md",
}

# OpenClaw workspace dirs that look like persona folders but are not ChemClaw manifests.
_OPENCLAW_WORKSPACE_DIRS = frozenset(
    {"agents", "heartbeat", "tools", "user", "memory"}
)


@dataclass
class PackageScan:
    """Result of scanning a local package directory."""

    agents: list[Path] = field(default_factory=list)
    skills: list[Path] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    composed_from: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def is_junk_name(name: str) -> bool:
    return name.lower() in _JUNK_NAMES or name.startswith("._")


def is_skill_md(path: Path) -> bool:
    """True if ``path`` is a ``SKILL.md`` file (skill marker, not a persona)."""
    return path.is_file() and path.name == "SKILL.md"


def try_load_persona(path: Path) -> bool:
    """Return True if ``path`` parses as a persona manifest (not ``SKILL.md``)."""
    if not path.is_file() or path.name == "SKILL.md":
        return False
    try:
        load_manifest_file(path, builtin=False)
        return True
    except (ManifestError, OSError, UnicodeDecodeError):
        return False


def unwrap_package_root(root: Path) -> Path:
    """If the archive extracted to a single top-level folder, scan inside it."""
    if not root.is_dir():
        return root
    entries = [
        p
        for p in root.iterdir()
        if not is_junk_name(p.name) and p.name not in {".", ".."}
    ]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return root


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _under_skill(path: Path, skill_dirs: set[Path]) -> bool:
    """True if ``path`` is inside (or is) a classified skill directory."""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for skill in skill_dirs:
        if resolved == skill or skill in resolved.parents:
            return True
    return False


def _has_openclaw_identity(root: Path) -> bool:
    return (root / "IDENTITY.md").is_file() or (root / "SOUL.md").is_file()


def _skill_names(skill_dirs: list[Path]) -> list[str]:
    names: list[str] = []
    for skill_dir in skill_dirs:
        try:
            names.append(validate_name(_parse_skill(skill_dir / "SKILL.md").name))
        except (ValueError, OSError):
            continue
    return names


def scan_package_dir(root: Path) -> PackageScan:
    """Classify Agents / Skills under ``root``; collect unclassified content paths."""
    root = unwrap_package_root(Path(root))
    if not root.is_dir():
        return PackageScan()

    skills: list[Path] = []
    skill_dirs: set[Path] = set()
    for md in sorted(root.rglob("SKILL.md")):
        if any(is_junk_name(part) for part in md.parts):
            continue
        if GENERATED_DIR in md.parts:
            continue
        if not md.is_file():
            continue
        parent = md.parent
        try:
            skill_dirs.add(parent.resolve())
        except OSError:
            continue
        skills.append(parent)

    agents: list[Path] = []
    ignored: list[str] = []
    seen_ignored: set[str] = set()
    warnings: list[str] = []
    composed_from: list[str] = []
    openclaw_identity = _has_openclaw_identity(root)

    def add_ignored(path: Path) -> None:
        rel = _rel(root, path)
        if rel and rel not in seen_ignored:
            seen_ignored.add(rel)
            ignored.append(rel)

    # Top-level *.md OR one-level subdir *.md — persona candidates (skip SKILL.md).
    candidates: list[Path] = sorted(root.glob("*.md"))
    for sub in sorted(p for p in root.iterdir() if p.is_dir() and not is_junk_name(p.name)):
        if sub.name == GENERATED_DIR:
            continue
        if _under_skill(sub, skill_dirs):
            continue
        # With OpenClaw identity files, skip workspace dirs that produce false agents.
        if openclaw_identity and sub.name.lower() in _OPENCLAW_WORKSPACE_DIRS:
            continue
        candidates.extend(sorted(sub.glob("*.md")))

    agent_files: set[Path] = set()
    for md in candidates:
        if md.name == "SKILL.md":
            continue
        # OpenClaw workspace files are prompt raw material, not ChemClaw personas.
        if openclaw_identity and md.name.lower() in OPENCLAW_WORKSPACE_FILES:
            continue
        if _under_skill(md, skill_dirs):
            continue
        if try_load_persona(md):
            agents.append(md)
            agent_files.add(md.resolve())
        else:
            add_ignored(md)

    # Compose OpenClaw workspace only when no explicit ChemClaw persona exists.
    if not agents and openclaw_identity:
        composed = compose_openclaw_persona(root, _skill_names(skills))
        if composed is not None:
            manifest_path, composed_from = composed
            agents.append(manifest_path)
            try:
                agent_files.add(manifest_path.resolve())
            except OSError:
                pass
            warnings.append(
                "已检测到 OpenClaw 工作区文件：已合成进智能体提示词，"
                "未将 AGENTS/USER/TOOLS 等安装为独立智能体"
            )
            if (root / "memory").is_dir() and "MEMORY.md" in composed_from:
                warnings.append(
                    "已将 MEMORY.md 写入智能体提示词；memory/ 目录未整树导入"
                    "（与运行时 memory 是不同机制）"
                )
            elif (root / "memory").is_dir():
                warnings.append(
                    "已忽略 memory/：未整树导入 ChemClaw"
                    "（与运行时 memory 是不同机制）"
                )

    composed_set = {name.lower() for name in composed_from}

    # Top-level files that look like content but weren't agents/skills.
    for p in sorted(root.iterdir()):
        if is_junk_name(p.name):
            continue
        if p.name == GENERATED_DIR:
            continue
        if p.is_file():
            if p.suffix.lower() == ".md":
                low = p.name.lower()
                if low in composed_set:
                    continue  # shown via composed_from, not ignored
                if openclaw_identity and low in OPENCLAW_WORKSPACE_FILES:
                    # Present but not folded (e.g. empty HEARTBEAT) — list as ignored.
                    add_ignored(p)
                    continue
                if low in {"identity.md", "soul.md"} and openclaw_identity and agents:
                    # Explicit ChemClaw persona present — identity unused.
                    if not composed_from:
                        add_ignored(p)
                        warnings.append(
                            f"已忽略 {p.name}：包内已有 ChemClaw 智能体清单，"
                            "未再从 OpenClaw 工作区文件合成"
                        )
                    continue
                continue  # already handled in candidate loop
            add_ignored(p)
            continue
        if not p.is_dir():
            continue
        try:
            resolved = p.resolve()
        except OSError:
            add_ignored(p)
            continue
        if resolved in skill_dirs:
            continue
        # Dir holds a classified agent md → not ignored.
        if any(af.parent.resolve() == resolved for af in agent_files):
            continue
        # OpenClaw workspace dirs when identity present → ignore whole dir.
        if openclaw_identity and p.name.lower() in _OPENCLAW_WORKSPACE_DIRS:
            add_ignored(p)
            continue
        # Dir has nested skills only (no top-level agent) — skills already listed.
        if any(resolved in sd.parents or sd == resolved for sd in skill_dirs):
            for child in sorted(p.iterdir()):
                if is_junk_name(child.name):
                    continue
                if child.is_file() and child.suffix.lower() == ".md":
                    continue  # candidate path already handled
                if child.is_dir():
                    try:
                        if child.resolve() in skill_dirs:
                            continue
                        if any(
                            child.resolve() in sd.parents or sd == child.resolve()
                            for sd in skill_dirs
                        ):
                            continue
                    except OSError:
                        pass
                if not _under_skill(child, skill_dirs):
                    add_ignored(child)
            continue
        # Empty-ish or unclassified content directory.
        add_ignored(p)

    return PackageScan(
        agents=agents,
        skills=skills,
        ignored=ignored,
        composed_from=composed_from,
        warnings=warnings,
    )


def persona_id_for(path: Path) -> Optional[str]:
    """Parse persona id from a manifest path, or None if invalid."""
    try:
        return load_manifest_file(path, builtin=False).id
    except (ManifestError, OSError, UnicodeDecodeError):
        return None
