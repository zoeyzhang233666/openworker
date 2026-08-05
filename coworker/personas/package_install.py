"""Persona package preview + co-install (D-066 / D-069).

Preview when ``decisions`` is None; install when decisions map each conflict key to
``overwrite`` or ``skip``. Skills copy as full trees; Agents snapshot md only.
OpenClaw IDENTITY/SOUL may be composed into a ChemClaw persona at scan time.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ..skills.base import _parse_skill
from ..skills.store import SkillStore, _ensure_frontmatter_source, validate_name
from .loading import consent_summary
from .manifest import ManifestError, load_manifest_file
from .package_scan import PackageScan, scan_package_dir, unwrap_package_root
from .registry import PersonaRegistry


def _rel_to(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _skill_name(skill_dir: Path) -> str:
    return validate_name(_parse_skill(skill_dir / "SKILL.md").name)


def _skill_exists(store: SkillStore, name: str) -> bool:
    return (store.global_dir / name / "SKILL.md").is_file()


def _install_skill_tree(
    store: SkillStore, src: Path, *, overwrite: bool
) -> dict[str, Any]:
    """Copy a full skill directory into the global store (D-060 / D-066)."""
    name = _skill_name(src)
    dest = store.global_dir / name
    exists = (dest / "SKILL.md").is_file()
    if exists and not overwrite:
        return {"name": name, "action": "skipped", "reason": "已存在，已跳过"}
    store.global_dir.mkdir(parents=True, exist_ok=True)
    if exists:
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    _ensure_frontmatter_source(dest / "SKILL.md", "uploaded")
    return {"name": name, "action": "installed", "path": str(dest)}


def _install_agent_md(
    registry: PersonaRegistry, md: Path, *, overwrite: bool
) -> dict[str, Any]:
    """Snapshot a persona md into the registry (lands disabled pending consent)."""
    m = load_manifest_file(md, builtin=False)
    existing = registry.get(m.id)
    if existing is not None:
        if existing.builtin:
            return {
                "id": m.id,
                "action": "skipped",
                "reason": f"内置智能体「{m.id}」不可覆盖，已跳过",
            }
        if not overwrite:
            return {"id": m.id, "action": "skipped", "reason": "已存在，已跳过"}
        # Overwrite snapshot in place without deleting lifecycle keys first.
        snapshot = registry._snapshot(md, m.id)
        installed = load_manifest_file(snapshot, builtin=False) if snapshot else m
        registry._register_manifest(installed, builtin=False)
        registry._enabled[m.id] = False
        registry._surfaced[m.id] = False
        registry.save()
        return {
            "id": m.id,
            "action": "installed",
            "consent": consent_summary(installed),
        }

    snapshot = registry._snapshot(md, m.id)
    installed = load_manifest_file(snapshot, builtin=False) if snapshot else m
    registry._register_manifest(installed, builtin=False)
    registry._enabled[m.id] = False
    registry._surfaced[m.id] = False
    registry.save()
    return {
        "id": m.id,
        "action": "installed",
        "consent": consent_summary(installed),
    }


def _missing_skill_refs(
    agents: list[Path],
    package_skill_names: set[str],
    store: SkillStore,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for md in agents:
        try:
            m = load_manifest_file(md, builtin=False)
        except (ManifestError, OSError, UnicodeDecodeError):
            continue
        for sid in m.skills:
            if sid in package_skill_names:
                continue
            if _skill_exists(store, sid):
                continue
            out.append({"agent_id": m.id, "skill": sid})
    return out


def _build_preview(
    scan: PackageScan,
    registry: PersonaRegistry,
    skill_store: SkillStore,
    root: Path,
) -> dict[str, Any]:
    agents_info: list[dict[str, Any]] = []
    package_skill_names: set[str] = set()
    skills_info: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for skill_dir in scan.skills:
        try:
            name = _skill_name(skill_dir)
        except (ValueError, OSError):
            continue
        package_skill_names.add(name)
        entry = {
            "key": f"skill:{name}",
            "name": name,
            "path": _rel_to(root, skill_dir),
        }
        skills_info.append(entry)
        if _skill_exists(skill_store, name):
            conflicts.append(
                {
                    "key": f"skill:{name}",
                    "kind": "skill",
                    "name": name,
                    "reason": f"技能「{name}」已安装",
                }
            )

    for md in scan.agents:
        try:
            m = load_manifest_file(md, builtin=False)
        except (ManifestError, OSError, UnicodeDecodeError):
            continue
        agents_info.append(
            {
                "key": f"agent:{m.id}",
                "id": m.id,
                "name": m.name,
                "skills": list(m.skills),
                "path": _rel_to(root, md),
            }
        )
        existing = registry.get(m.id)
        if existing is not None:
            if existing.builtin:
                conflicts.append(
                    {
                        "key": f"agent:{m.id}",
                        "kind": "agent",
                        "id": m.id,
                        "reason": f"内置智能体「{m.id}」不可覆盖",
                        "builtin": True,
                    }
                )
            else:
                conflicts.append(
                    {
                        "key": f"agent:{m.id}",
                        "kind": "agent",
                        "id": m.id,
                        "reason": f"智能体「{m.id}」已安装",
                    }
                )

    missing = _missing_skill_refs(scan.agents, package_skill_names, skill_store)
    warnings = list(scan.warnings)
    return {
        "ok": True,
        "preview": True,
        "agents": agents_info,
        "skills": skills_info,
        "conflicts": conflicts,
        "ignored": list(scan.ignored),
        "composed_from": list(scan.composed_from),
        "warnings": warnings,
        "missing_skill_refs": missing,
    }


def preview_or_install(
    registry: PersonaRegistry,
    skill_store: SkillStore,
    root: Path | str,
    *,
    decisions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Preview a package (``decisions is None``) or install with per-item decisions.

    Decision keys are ``agent:<id>`` / ``skill:<name>``; values ``overwrite`` | ``skip``.
    Items without a conflict install automatically. Built-in agent conflicts are always
    skipped. Missing skill refs still allow the Agent to install (with warnings).
    """
    root = Path(root)
    if not root.is_dir():
        return {"ok": False, "error": f"不是有效目录：{root}"}

    root = unwrap_package_root(root)
    scan = scan_package_dir(root)

    if decisions is None:
        return _build_preview(scan, registry, skill_store, root)

    # Normalize decisions.
    norm: dict[str, str] = {}
    for k, v in decisions.items():
        key = str(k).strip()
        val = str(v).strip().lower()
        if val not in {"overwrite", "skip"}:
            return {
                "ok": False,
                "error": f"无效决定「{v}」（仅支持 overwrite 或 skip）",
            }
        norm[key] = val

    package_skill_names: set[str] = set()
    for skill_dir in scan.skills:
        try:
            package_skill_names.add(_skill_name(skill_dir))
        except (ValueError, OSError):
            continue

    installed_agents: list[str] = []
    installed_skills: list[str] = []
    skipped: list[dict[str, str]] = []
    warnings: list[str] = []
    consent: list[dict] = []

    # Skills first so agent refs in the same package resolve after install.
    for skill_dir in scan.skills:
        try:
            name = _skill_name(skill_dir)
        except (ValueError, OSError) as exc:
            warnings.append(f"无法解析技能目录：{skill_dir.name}（{exc}）")
            continue
        key = f"skill:{name}"
        exists = _skill_exists(skill_store, name)
        if exists:
            decision = norm.get(key, "skip")
            if decision == "skip":
                skipped.append({"key": key, "reason": "已存在，已跳过"})
                continue
            overwrite = True
        else:
            overwrite = False
        try:
            result = _install_skill_tree(skill_store, skill_dir, overwrite=overwrite)
        except (ValueError, OSError) as exc:
            warnings.append(f"安装技能「{name}」失败：{exc}")
            continue
        if result["action"] == "installed":
            installed_skills.append(name)
        else:
            skipped.append({"key": key, "reason": result.get("reason", "已跳过")})

    for md in scan.agents:
        try:
            m = load_manifest_file(md, builtin=False)
        except (ManifestError, OSError, UnicodeDecodeError) as exc:
            warnings.append(f"无法解析智能体清单：{md.name}（{exc}）")
            continue
        key = f"agent:{m.id}"
        existing = registry.get(m.id)
        if existing is not None and existing.builtin:
            skipped.append(
                {
                    "key": key,
                    "reason": f"内置智能体「{m.id}」不可覆盖，已跳过",
                }
            )
            continue
        if existing is not None:
            decision = norm.get(key, "skip")
            if decision == "skip":
                skipped.append({"key": key, "reason": "已存在，已跳过"})
                continue
            overwrite = True
        else:
            overwrite = False
        try:
            result = _install_agent_md(registry, md, overwrite=overwrite)
        except (ManifestError, OSError, ValueError) as exc:
            warnings.append(f"安装智能体「{m.id}」失败：{exc}")
            continue
        if result["action"] == "installed":
            installed_agents.append(m.id)
            if result.get("consent"):
                consent.append(result["consent"])
        else:
            skipped.append({"key": key, "reason": result.get("reason", "已跳过")})

    missing = _missing_skill_refs(scan.agents, package_skill_names, skill_store)
    installed_set = set(installed_agents)
    for ref in missing:
        if ref["agent_id"] in installed_set:
            warnings.append(
                f"智能体「{ref['agent_id']}」引用的技能「{ref['skill']}」未安装，"
                "已继续安装智能体"
            )
    for w in scan.warnings:
        if w not in warnings:
            warnings.append(w)

    return {
        "ok": True,
        "preview": False,
        "installed": {"agents": installed_agents, "skills": installed_skills},
        "skipped": skipped,
        "warnings": warnings,
        "ignored": list(scan.ignored),
        "composed_from": list(scan.composed_from),
        "missing_skill_refs": missing,
        "consent": consent,
        "personas": registry.list_all(),
    }
