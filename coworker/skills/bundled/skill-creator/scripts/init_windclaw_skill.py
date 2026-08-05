#!/usr/bin/env python3
"""
Initialize a skill directly inside the correct WindClaw managed workspace scope.

Usage:
    init_windclaw_skill.py <skill-slug> [--display-name "Name"] [--cwd <cwd>] [--json]

This script is intended for skill creation inside a live WindClaw/OpenClaw workspace.
It resolves the current workspace ownership model and creates the skill under the
final managed runtimeKey directory rather than a transient `skills/<slug>` folder.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SAFE_PART_RE = re.compile(r"[^a-z0-9]+")


def normalize_key_part(value: str, fallback: str) -> str:
    normalized = SAFE_PART_RE.sub("-", value.strip().lower()).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    return normalized or fallback


def normalize_skill_slug(value: str) -> str:
    return normalize_key_part(value, "skill")


def normalize_agent_id(value: str) -> str:
    return normalize_key_part(value, "main")


def build_runtime_key(agent_id: str, slug: str) -> str:
    return f"{normalize_agent_id(agent_id)}-{normalize_skill_slug(slug)}"


def find_openclaw_workspace(start: Path) -> tuple[Path, Path]:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if candidate.name == "workspace" or candidate.name.startswith("workspace-"):
            openclaw_root = candidate.parent
            if (openclaw_root / "openclaw.json").exists():
                return candidate, openclaw_root
    raise RuntimeError("Current working directory is not inside a WindClaw workspace")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def determine_owner_workspace(workspace: Path, openclaw_root: Path) -> tuple[Path, str]:
    meta_path = workspace / ".windclaw-workspace.json"
    meta = load_json(meta_path) if meta_path.exists() else {}
    if workspace.name == "workspace":
        return workspace, "default-owner"

    if isinstance(meta.get("agentProfile"), dict):
        return workspace, "isolated"

    return openclaw_root / "workspace", "follower"


def resolve_agent_id(owner_workspace: Path, openclaw_root: Path) -> str:
    if owner_workspace.name == "workspace":
        return "main"

    config = load_json(openclaw_root / "openclaw.json")
    agent_list = (((config or {}).get("agents") or {}).get("list") or [])
    owner_workspace_str = str(owner_workspace.resolve())
    for entry in agent_list:
        if not isinstance(entry, dict):
            continue
        workspace_path = entry.get("workspace")
        agent_id = entry.get("id")
        if isinstance(workspace_path, str) and isinstance(agent_id, str):
            try:
                if str(Path(workspace_path).resolve()) == owner_workspace_str and agent_id.strip():
                    return agent_id.strip()
            except Exception:
                continue

    if owner_workspace.name.startswith("workspace-"):
        inferred = owner_workspace.name[len("workspace-"):].strip()
        if inferred:
            return inferred
    return "main"


def build_skill_template(skill_slug: str, display_name: str) -> str:
    return f"""---
name: {display_name}
description: TODO: Explain what this skill does and when to use it.
metadata:
  openclaw:
    skillKey: TODO_RUNTIME_KEY
---

# {display_name}

## Overview

TODO: Explain what this skill enables.

## Workflow

1. TODO: Describe the main workflow.
2. TODO: Add key decision points.
3. TODO: Reference any scripts or supporting docs.

## Resources

- `scripts/`: executable helpers for repeated or deterministic operations.
- `references/`: longer documentation loaded on demand.
- `assets/`: templates or output-side assets when needed.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a managed WindClaw skill")
    parser.add_argument("skill_slug", help="Skill slug in kebab-case")
    parser.add_argument("--display-name", dest="display_name", default=None, help="Human-readable skill name")
    parser.add_argument("--cwd", dest="cwd", default=".", help="Current working directory inside the active workspace")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args()

    cwd = Path(args.cwd).expanduser()
    workspace, openclaw_root = find_openclaw_workspace(cwd)
    owner_workspace, mode = determine_owner_workspace(workspace, openclaw_root)
    agent_id = resolve_agent_id(owner_workspace, openclaw_root)
    skill_slug = normalize_skill_slug(args.skill_slug)
    runtime_key = build_runtime_key(agent_id, skill_slug)
    display_name = (args.display_name or skill_slug).strip() or skill_slug

    skills_root = owner_workspace / "skills"
    skill_dir = skills_root / runtime_key
    skill_md_path = skill_dir / "SKILL.md"

    if skill_dir.exists():
        raise RuntimeError(f"Managed skill directory already exists: {skill_dir}")

    skill_dir.mkdir(parents=True, exist_ok=False)
    (skill_dir / "scripts").mkdir()
    (skill_dir / "references").mkdir()
    (skill_dir / "assets").mkdir()

    template = build_skill_template(skill_slug, display_name).replace("TODO_RUNTIME_KEY", runtime_key)
    skill_md_path.write_text(template, encoding="utf-8")

    payload = {
        "requested_workspace": str(workspace),
        "owner_workspace": str(owner_workspace),
        "mode": mode,
        "agent_id": agent_id,
        "slug": skill_slug,
        "runtime_key": runtime_key,
        "skill_dir": str(skill_dir),
        "skill_md_path": str(skill_md_path),
    }

    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Initialized managed WindClaw skill at: {skill_dir}")
        print(f"SKILL.md: {skill_md_path}")
        print(f"runtimeKey: {runtime_key}")
        print(f"mode: {mode}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
