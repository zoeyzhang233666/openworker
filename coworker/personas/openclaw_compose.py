"""Compose OpenClaw workspace markdown into a ChemClaw persona (D-069).

Install-time synthesis only — ChemClaw does not hot-read these files at runtime.
Workspace docs (IDENTITY/SOUL/AGENTS/…) become sections of one system_prompt; they
are not installed as separate agents.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

# Serenity seven Chinese research skills (D-013 / D-058).
SERENITY_SKILL_NAMES = frozenset(
    {
        "产业链层级测绘",
        "稀缺环节识别",
        "证据强弱分级",
        "证伪条件压力测试",
        "叙事到系统变化",
        "候选优先级排序",
        "研究对话推进",
    }
)

GENERATED_DIR = ".chemclaw-generated"
GENERATED_MANIFEST = "manifest.md"

# Top-level OpenClaw workspace filenames (lowercase). Only skipped as persona
# candidates when IDENTITY/SOUL is present — not a global blacklist.
OPENCLAW_WORKSPACE_FILES = frozenset(
    {
        "identity.md",
        "soul.md",
        "agents.md",
        "heartbeat.md",
        "tools.md",
        "user.md",
        "memory.md",
        "bootstrap.md",
    }
)

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

# HEARTBEAT templates are often empty aside from comments / title lines.
_HEARTBEAT_NOISE = re.compile(
    r"(?i)^(#+)?\s*(heartbeat\.md)?\s*$|"
    r"^#\s*keep this file empty|"
    r"^#\s*add tasks below|"
    r"^---$|"
    r"^title:|"
    r"^summary:|"
    r"^read_when:"
)


def _read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_yaml_frontmatter(text: str) -> str:
    """Remove a leading ``---`` YAML block when present; return body stripped."""
    if not text.startswith("---"):
        return text.strip()
    end = text.find("\n---", 3)
    if end == -1:
        return text.strip()
    return text[end + 4 :].lstrip("\n").strip()


def _slugify(stem: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", stem.strip().lower()).strip("-_")[:64]
    return slug if _ID_RE.match(slug) else "imported-agent"


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            return s.lstrip("#").strip()
        return s
    return ""


def _substantial(text: str) -> bool:
    return len(re.sub(r"\s+", "", text)) >= 20


def _heartbeat_substantial(text: str) -> bool:
    kept: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") and "empty" in s.lower():
            continue
        if _HEARTBEAT_NOISE.match(s):
            continue
        if s.startswith("#") and "heartbeat" in s.lower():
            continue
        kept.append(s)
    return _substantial("\n".join(kept))


def is_serenity_package(root: Path, skill_names: list[str]) -> bool:
    """True when folder name suggests Serenity or skill set overlaps known Serenity skills."""
    if "serenity" in root.name.lower():
        return True
    return bool(SERENITY_SKILL_NAMES.intersection(skill_names))


def resolve_persona_identity(
    root: Path, skill_names: list[str], identity_text: str
) -> tuple[str, str, str, str]:
    """Return (id, name, tagline, description)."""
    if is_serenity_package(root, skill_names):
        return (
            "serenity",
            "白毛股神 Serenity",
            "先拆系统与瓶颈，再谈公司与证据",
            "基于产业链层级、稀缺环节、证据链和证伪条件推进研究。",
        )
    heading = _first_heading(identity_text) if identity_text else ""
    name = heading or root.name or "Imported Agent"
    persona_id = _slugify(root.name or "imported-agent")
    return (
        persona_id,
        name,
        "从 OpenClaw 工作区导入",
        f"由 {root.name} 的 OpenClaw 工作区文件合成。",
    )


def build_manifest_text(
    *,
    persona_id: str,
    name: str,
    tagline: str,
    description: str,
    skill_names: list[str],
    sections: list[tuple[str, str]],
) -> str:
    meta = {
        "id": persona_id,
        "name": name,
        "icon": "chart",
        "tagline": tagline,
        "description": description,
        "family": "knowledge",
        "default_permission_mode": "interactive",
        "skills": list(skill_names),
        "source": "openclaw-compose",
    }
    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    parts = [f"## {title}\n\n{body}" for title, body in sections]
    parts.append(
        "请优先遵循本智能体已挂载的默认技能；不要把技能全文再复制进回复策略。"
    )
    body = "\n\n".join(parts).strip()
    return f"---\n{front}\n---\n\n{body}\n"


def _load_section(path: Path) -> str:
    if not path.is_file():
        return ""
    return strip_yaml_frontmatter(_read_utf8(path))


def compose_openclaw_persona(
    root: Path, skill_names: list[str]
) -> Optional[tuple[Path, list[str]]]:
    """Write ``.chemclaw-generated/manifest.md`` from OpenClaw workspace files.

    Returns ``(manifest_path, composed_from)`` or ``None`` when IDENTITY/SOUL missing.
    """
    root = Path(root)
    identity_path = root / "IDENTITY.md"
    soul_path = root / "SOUL.md"
    if not identity_path.is_file() and not soul_path.is_file():
        return None

    # (filename, section title, path, substantial check)
    section_specs = [
        ("IDENTITY.md", "身份", identity_path, _substantial),
        ("SOUL.md", "行为准则", soul_path, _substantial),
        ("AGENTS.md", "工作区约定", root / "AGENTS.md", _substantial),
        ("USER.md", "用户档案", root / "USER.md", _substantial),
        ("TOOLS.md", "工具与资料备注", root / "TOOLS.md", _substantial),
        ("MEMORY.md", "长期备忘", root / "MEMORY.md", _substantial),
        ("HEARTBEAT.md", "心跳备忘", root / "HEARTBEAT.md", _heartbeat_substantial),
    ]

    sections: list[tuple[str, str]] = []
    composed_from: list[str] = []
    identity_text = ""

    for filename, title, path, ok in section_specs:
        body = _load_section(path)
        if filename == "IDENTITY.md":
            identity_text = body
        if not body or not ok(body):
            continue
        sections.append((title, body))
        composed_from.append(filename)

    if not composed_from:
        return None
    # Require at least identity or soul signal in the composed set.
    if not ({"IDENTITY.md", "SOUL.md"} & set(composed_from)):
        return None

    persona_id, name, tagline, description = resolve_persona_identity(
        root, skill_names, identity_text
    )
    text = build_manifest_text(
        persona_id=persona_id,
        name=name,
        tagline=tagline,
        description=description,
        skill_names=skill_names,
        sections=sections,
    )
    out_dir = root / GENERATED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / GENERATED_MANIFEST
    out_path.write_text(text, encoding="utf-8")
    return out_path, composed_from
