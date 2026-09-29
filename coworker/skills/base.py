"""Skill loading — Anthropic SKILL.md format with progressive disclosure.

A skill is a folder containing `SKILL.md` (YAML frontmatter: name, description,
optional allowed-tools) + a markdown body of instructions + optional resources/scripts.

Progressive disclosure: search_skills retrieves metadata and load_skill retrieves the
latest body. The full catalog is not attached to every conversation request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Callable, Iterable, Optional, Union

import aisuite as ai


@dataclass
class Skill:
    name: str
    description: str
    instructions: str = ""  # full body — loaded on demand
    path: Optional[str] = None
    allowed_tools: list[str] = field(default_factory=list)


class SkillLoader:
    def __init__(self, dirs: list[str | Path]) -> None:
        self._dirs = [Path(d) for d in dirs]
        self._skills: dict[str, Skill] = {}
        self.rescan()

    def rescan(self) -> None:
        """Refresh installed metadata and bodies for live discovery/load calls."""
        self._skills = {}
        for directory in self._dirs:
            self._discover(directory)

    def _discover(self, directory: Path) -> None:
        if not directory.is_dir():
            return
        for sub in sorted(directory.iterdir()):
            md = sub / "SKILL.md"
            if md.is_file():
                skill = _parse_skill(md)
                self._skills[skill.name] = skill

    def names(self) -> list[str]:
        return list(self._skills)

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def catalog(self) -> list[dict]:
        return [
            {"name": s.name, "description": s.description}
            for s in self._skills.values()
        ]


def _strip_yaml_scalar(value: str) -> str:
    """Strip optional surrounding single/double quotes from a simple YAML scalar."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _parse_skill(md: Path) -> Skill:
    text = md.read_text(encoding="utf-8")
    name, description, allowed, body = md.parent.name, "", [], text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            frontmatter = text[3:end]
            body = text[end + 4 :].lstrip("\n")
            for line in frontmatter.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key, value = key.strip().lower(), value.strip()
                if key == "name" and value:
                    name = _strip_yaml_scalar(value)
                elif key == "description":
                    description = _strip_yaml_scalar(value)
                elif key in ("allowed-tools", "allowed_tools"):
                    allowed = [t.strip() for t in value.split(",") if t.strip()]
    return Skill(
        name=name,
        description=description,
        instructions=body.strip(),
        path=str(md.parent),
        allowed_tools=allowed,
    )


def skill_catalog_text(
    loader: SkillLoader,
    allowed: Optional[set[str]] = None,
    names: Optional[Iterable[str]] = None,
) -> str:
    selected = None if names is None else set(names)
    catalog = [
        c
        for c in loader.catalog()
        if (allowed is None or c["name"] in allowed)
        and (selected is None or c["name"] in selected)
    ]
    if not catalog:
        return ""
    lines = [f"- {c['name']}: {c['description']}" for c in catalog]
    return (
        "可用技能——任务相关时调用 load_skill(name) 加载完整说明：\n" + "\n".join(lines)
    )


AllowedSkills = Union[set, Callable[[], set], None]


def select_skill_names(
    loader: SkillLoader,
    query: str,
    *,
    allowed: Optional[set[str]] = None,
    preferred: Iterable[str] = (),
    limit: int = 8,
) -> tuple[str, ...]:
    """Return metadata-only local matches; never loads SKILL.md instructions.

    Preferred/default/forced names are always kept first. Remaining ordinary
    candidates use a deterministic lexical score and are capped to eight total.
    """
    limit = max(1, min(int(limit), 8))
    catalog = [
        c for c in loader.catalog() if allowed is None or c["name"] in allowed
    ]
    by_name = {c["name"]: c for c in catalog}
    out: list[str] = []
    for name in preferred:
        if name in by_name and name not in out:
            out.append(name)

    terms = _skill_terms(query)
    if not terms:
        return tuple(out)
    ranked: list[tuple[int, str]] = []
    low_query = (query or "").lower()
    for item in catalog:
        name = item["name"]
        if name in out:
            continue
        haystack = f"{name} {item['description']}".lower()
        score = sum(3 if term in name.lower() else 1 for term in terms if term in haystack)
        if name.lower() in low_query:
            score += 8
        if score:
            ranked.append((-score, name))
    for _score, name in sorted(ranked):
        if len(out) >= limit:
            break
        out.append(name)
    return tuple(out)


def _skill_terms(query: str) -> tuple[str, ...]:
    raw = re.findall(
        r"[a-z0-9][a-z0-9._+-]{1,}|[\u4e00-\u9fff]{2,}",
        (query or "").lower(),
    )
    terms: list[str] = []
    for token in raw:
        terms.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]+", token) and len(token) > 3:
            # Chinese intent is rarely whitespace-tokenized. Short n-grams keep
            # metadata search useful without loading skill bodies.
            for width in (2, 3, 4):
                terms.extend(token[i : i + width] for i in range(len(token) - width + 1))
    return tuple(dict.fromkeys(terms[:96]))


def skill_tools(loader: SkillLoader, allowed: AllowedSkills = None) -> list:
    """`allowed` gates load_skill: a set is a build-time snapshot; a CALLABLE is consulted
    on every call — the manager passes one so Settings disables apply to live sessions
    immediately. Every search/load refreshes installed contents."""

    def _allowed_now() -> Optional[set]:
        return allowed() if callable(allowed) else allowed

    def load_skill(name: str) -> dict:
        """按名称加载技能的完整说明与资源路径。当目录中某技能与当前任务相关时调用。"""
        loader.rescan()  # Updates/deletions must apply even within the same model turn.
        skill = loader.get(name)
        gate = _allowed_now()
        if skill is None or (gate is not None and name not in gate):
            available = sorted(
                n for n in loader.names() if gate is None or n in gate
            )
            return {"error": f"unknown skill: {name}", "available": available}
        return {
            "name": skill.name,
            "instructions": skill.instructions,
            "resources_path": skill.path,
        }

    def search_skills(query: str = "", limit: int = 8, offset: int = 0) -> dict:
        """按名称/描述搜索已启用技能；空查询分页浏览。返回元数据，再用 load_skill 加载最新说明。"""
        loader.rescan()
        gate = _allowed_now()
        rows = [c for c in loader.catalog() if gate is None or c["name"] in gate]
        terms = _skill_terms(query)
        if query.strip():
            def score(row):
                name = row["name"].lower()
                haystack = f"{name} {row['description']}".lower()
                return (8 if query.lower().strip() == name else 0) + sum(
                    3 if term in name else 1 for term in terms if term in haystack
                )
            rows = sorted((r for r in rows if score(r)), key=lambda r: (-score(r), r["name"]))
        else:
            rows.sort(key=lambda r: r["name"])
        offset, limit = max(0, int(offset)), max(1, min(int(limit), 20))
        end = offset + limit
        return {"skills": rows[offset:end], "total": len(rows),
                "next_offset": end if end < len(rows) else None}

    return [
        ai.tool(
            load_skill,
            metadata=ai.ToolMetadata(
                category="skills", risk_level="low", capabilities=["load_skill"]
            ),
        ),
        ai.tool(
            search_skills,
            metadata=ai.ToolMetadata(
                category="skills", risk_level="low", capabilities=["search_skills"]
            ),
        ),
    ]
