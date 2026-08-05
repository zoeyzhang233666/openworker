"""D-066 persona package scan + co-install (loose layout, conflict skip/overwrite)."""

from __future__ import annotations

from pathlib import Path

from coworker.personas.package_install import preview_or_install
from coworker.personas.package_scan import scan_package_dir
from coworker.personas.registry import PersonaRegistry
from coworker.skills.store import SkillStore

AGENT_MD = """---
id: pack-agent
name: Pack Agent
family: knowledge
skills:
  - pack-skill
  - missing-skill
---
You are the pack agent.
"""

SKILL_MD = """---
name: pack-skill
description: A packaged skill
---
Do the pack thing.
"""

OTHER_AGENT = """---
id: nested-agent
name: Nested Agent
family: knowledge
---
Nested body.
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _loose_package(root: Path) -> Path:
    """Top-level persona md + one-level agent dir + nested skill tree + junk."""
    _write(root / "pack-agent.md", AGENT_MD)
    _write(root / "agents" / "nested.md", OTHER_AGENT)
    _write(root / "skills" / "pack-skill" / "SKILL.md", SKILL_MD)
    _write(root / "skills" / "pack-skill" / "scripts" / "run.py", "print('ok')\n")
    _write(root / "notes.txt", "not classified\n")
    _write(root / "agents" / "readme-notes.md", "not a persona\n")
    return root


def test_scan_loose_layout(tmp_path):
    pkg = _loose_package(tmp_path / "pkg")
    scan = scan_package_dir(pkg)

    agent_names = {p.name for p in scan.agents}
    assert agent_names == {"pack-agent.md", "nested.md"}
    assert len(scan.skills) == 1
    assert scan.skills[0].name == "pack-skill"
    assert (scan.skills[0] / "scripts" / "run.py").is_file()
    # Unclassified content surfaces as relative paths.
    assert "notes.txt" in scan.ignored
    assert any("readme-notes.md" in i for i in scan.ignored)
    # Skill tree itself is not ignored; SKILL.md is not treated as an agent.
    assert not any(p.name == "SKILL.md" for p in scan.agents)


def test_preview_reports_conflicts_and_missing_refs(tmp_path):
    pkg = _loose_package(tmp_path / "pkg")
    reg = PersonaRegistry(state_path=tmp_path / "personas.json")
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    # Pre-install the skill so preview shows a conflict.
    preview_or_install(
        reg,
        store,
        pkg,
        decisions={},  # no conflicts yet on first install
    )
    assert (store.global_dir / "pack-skill" / "SKILL.md").is_file()
    assert "pack-agent" in reg.ids()

    # Second preview against same package → skill + agent conflicts.
    preview = preview_or_install(reg, store, pkg, decisions=None)
    assert preview["ok"] is True and preview["preview"] is True
    keys = {c["key"] for c in preview["conflicts"]}
    assert "skill:pack-skill" in keys
    assert "agent:pack-agent" in keys
    missing = {(m["agent_id"], m["skill"]) for m in preview["missing_skill_refs"]}
    assert ("pack-agent", "missing-skill") in missing


def test_conflict_skip_keeps_existing(tmp_path):
    pkg = _loose_package(tmp_path / "pkg")
    reg = PersonaRegistry(state_path=tmp_path / "personas.json")
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    preview_or_install(reg, store, pkg, decisions={})
    original = (store.global_dir / "pack-skill" / "SKILL.md").read_text(encoding="utf-8")

    # Mutate package skill body, then skip on conflict.
    _write(
        pkg / "skills" / "pack-skill" / "SKILL.md",
        SKILL_MD.replace("Do the pack thing.", "UPDATED BODY"),
    )
    result = preview_or_install(
        reg,
        store,
        pkg,
        decisions={
            "skill:pack-skill": "skip",
            "agent:pack-agent": "skip",
            "agent:nested-agent": "skip",
        },
    )
    assert result["ok"] is True
    assert result["installed"]["skills"] == []
    assert result["installed"]["agents"] == []
    assert any(s["key"] == "skill:pack-skill" for s in result["skipped"])
    assert (store.global_dir / "pack-skill" / "SKILL.md").read_text(
        encoding="utf-8"
    ) == original


def test_conflict_overwrite_replaces_skill_tree_and_agent(tmp_path):
    pkg = _loose_package(tmp_path / "pkg")
    reg = PersonaRegistry(state_path=tmp_path / "personas.json")
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    preview_or_install(reg, store, pkg, decisions={})

    _write(
        pkg / "skills" / "pack-skill" / "SKILL.md",
        SKILL_MD.replace("Do the pack thing.", "UPDATED BODY"),
    )
    _write(
        pkg / "skills" / "pack-skill" / "scripts" / "extra.py",
        "print('extra')\n",
    )
    _write(
        pkg / "pack-agent.md",
        AGENT_MD.replace("You are the pack agent.", "Updated agent prompt."),
    )

    result = preview_or_install(
        reg,
        store,
        pkg,
        decisions={
            "skill:pack-skill": "overwrite",
            "agent:pack-agent": "overwrite",
            "agent:nested-agent": "skip",
        },
    )
    assert result["ok"] is True
    assert "pack-skill" in result["installed"]["skills"]
    assert "pack-agent" in result["installed"]["agents"]
    skill_text = (store.global_dir / "pack-skill" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "UPDATED BODY" in skill_text
    assert (store.global_dir / "pack-skill" / "scripts" / "extra.py").is_file()
    assert "Updated agent prompt." in reg.agent("pack-agent").system_prompt
    # Missing skill ref still installs agent + warning.
    assert any("missing-skill" in w for w in result["warnings"])


def test_builtin_conflict_always_skipped(tmp_path):
    pkg = tmp_path / "pkg"
    _write(
        pkg / "ops.md",
        """---
id: ops
name: Fake Ops
family: knowledge
---
Should not replace builtin.
""",
    )
    reg = PersonaRegistry(state_path=tmp_path / "personas.json")
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    preview = preview_or_install(reg, store, pkg, decisions=None)
    assert any(c.get("builtin") for c in preview["conflicts"])

    result = preview_or_install(
        reg, store, pkg, decisions={"agent:ops": "overwrite"}
    )
    assert "ops" not in result["installed"]["agents"]
    assert reg.get("ops").builtin is True
    assert "Ops Coworker" == reg.get("ops").name


def test_skill_ids_and_persona_detail_fields(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import coworker.skills.bootstrap as boot
    from coworker.server.app import create_app
    from coworker.server.manager import SessionManager

    empty = tmp_path / "empty-bundled"
    empty.mkdir()
    monkeypatch.setattr(boot, "BUNDLED_DIR", empty)

    mgr = SessionManager(data_dir=tmp_path / "data")
    assert mgr.personas.skill_ids("cowork") == []
    assert mgr.personas.skill_ids("nope") == []

    pkg = _loose_package(tmp_path / "pkg")
    out = preview_or_install(mgr.personas, mgr.skill_store, pkg, decisions={})
    assert out["ok"] is True

    assert mgr.personas.skill_ids("pack-agent") == ["pack-skill", "missing-skill"]
    detail = mgr.persona_detail("pack-agent")
    assert detail is not None
    assert "You are the pack agent." in detail["system_prompt"]
    assert detail["builtin"] is False
    assert detail["install_path"]
    by_id = {s["id"]: s["installed"] for s in detail["skills"]}
    assert by_id["pack-skill"] is True
    assert by_id["missing-skill"] is False

    # Builtin builder persona still exposes system_prompt + empty skills.
    cowork = mgr.persona_detail("cowork")
    assert cowork["builtin"] is True
    assert cowork["install_path"] is None
    assert isinstance(cowork["system_prompt"], str) and cowork["system_prompt"]
    assert cowork["skills"] == []

    client = TestClient(create_app(mgr))
    api = client.get("/v1/personas/pack-agent").json()
    assert api["skills"] == detail["skills"]
    assert api["install_path"] == detail["install_path"]


_OPENCLAW_TEMPLATE_FM = """---
title: "{title} Template"
summary: "Workspace template"
read_when:
  - Bootstrapping a workspace manually
---
"""


def _openclaw_serenity_package(root: Path) -> Path:
    """OpenClaw-style pack matching real serenity-full-package top-level layout."""
    _write(root / "IDENTITY.md", "# Serenity\n\nI am Serenity, a research agent.\n")
    _write(root / "SOUL.md", "Be rigorous. Prefer evidence over narrative.\n")
    _write(
        root / "MEMORY.md",
        "## 角色与方法定位\n\n只做研究支持，不直接替用户做交易决策。\n",
    )
    _write(root / "memory" / "2026-01-01.md", "note\n")
    # Top-level workspace templates (real zip) — must NOT become fake agents.
    _write(
        root / "AGENTS.md",
        _OPENCLAW_TEMPLATE_FM.format(title="AGENTS.md")
        + "# AGENTS.md - Your Workspace\n\nThis folder is home. Treat it that way.\n",
    )
    _write(
        root / "HEARTBEAT.md",
        _OPENCLAW_TEMPLATE_FM.format(title="HEARTBEAT.md")
        + "# HEARTBEAT.md\n\n# Keep this file empty (or with only comments) to skip heartbeat.\n",
    )
    _write(
        root / "TOOLS.md",
        _OPENCLAW_TEMPLATE_FM.format(title="TOOLS.md")
        + "# TOOLS.md\n\n记录 Serenity workspace 本地工具与参考资料约定。\n",
    )
    _write(
        root / "USER.md",
        _OPENCLAW_TEMPLATE_FM.format(title="USER.md")
        + "# USER.md\n\n- **Name:**\n- **Notes:** placeholder only\n",
    )
    for skill_name in ("产业链层级测绘", "稀缺环节识别"):
        _write(
            root / "skills" / skill_name / "SKILL.md",
            f"""---
name: "{skill_name}"
description: research skill
---
Do {skill_name}.
""",
        )
    return root


def test_openclaw_identity_composes_serenity_agent(tmp_path):
    pkg = _openclaw_serenity_package(tmp_path / "serenity-full-package")
    scan = scan_package_dir(pkg)

    assert "IDENTITY.md" in scan.composed_from
    assert "SOUL.md" in scan.composed_from
    assert "AGENTS.md" in scan.composed_from
    assert "MEMORY.md" in scan.composed_from
    assert "IDENTITY.md" not in scan.ignored
    assert "SOUL.md" not in scan.ignored
    assert "MEMORY.md" not in scan.ignored
    assert "AGENTS.md" not in scan.ignored
    assert "memory" in scan.ignored
    assert any("MEMORY.md" in w and "提示词" in w for w in scan.warnings)
    assert len(scan.agents) == 1
    assert scan.agents[0].name == "manifest.md"

    reg = PersonaRegistry(state_path=tmp_path / "personas.json")
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    preview = preview_or_install(reg, store, pkg, decisions=None)
    assert preview["ok"] is True
    assert "IDENTITY.md" in preview["composed_from"]
    assert {a["id"] for a in preview["agents"]} == {"serenity"}
    assert preview["agents"][0]["name"] == "白毛股神 Serenity"
    assert "agents" not in {a["id"] for a in preview["agents"]}
    assert "heartbeat" not in {a["id"] for a in preview["agents"]}
    assert "tools" not in {a["id"] for a in preview["agents"]}
    assert "user" not in {a["id"] for a in preview["agents"]}

    result = preview_or_install(reg, store, pkg, decisions={})
    assert result["ok"] is True
    assert "serenity" in result["installed"]["agents"]
    assert "产业链层级测绘" in result["installed"]["skills"]
    prompt = reg.agent("serenity").system_prompt
    assert "I am Serenity" in prompt
    assert "Be rigorous" in prompt
    assert "This folder is home" in prompt
    assert "只做研究支持" in prompt
    assert "请优先遵循本智能体已挂载的默认技能" in prompt
    assert reg.skill_ids("serenity") == ["产业链层级测绘", "稀缺环节识别"]


def test_openclaw_compose_skipped_when_chemclaw_persona_present(tmp_path):
    pkg = tmp_path / "mixed-pack"
    _write(pkg / "IDENTITY.md", "OpenClaw identity with enough body text here.\n")
    _write(pkg / "SOUL.md", "OpenClaw soul with enough body text here.\n")
    _write(pkg / "pack-agent.md", AGENT_MD)
    _write(pkg / "skills" / "pack-skill" / "SKILL.md", SKILL_MD)

    scan = scan_package_dir(pkg)
    assert scan.composed_from == []
    assert "IDENTITY.md" in scan.ignored
    assert "SOUL.md" in scan.ignored
    assert {p.name for p in scan.agents} == {"pack-agent.md"}


def test_agents_md_without_openclaw_identity_still_installs_as_persona(tmp_path):
    """No IDENTITY/SOUL → AGENTS.md is not blacklisted; valid ChemClaw persona installs."""
    pkg = tmp_path / "plain-pack"
    _write(
        pkg / "AGENTS.md",
        """---
id: custom-agents
name: Custom Agents Doc
family: knowledge
---
This is a deliberate ChemClaw persona named via AGENTS.md filename.
""",
    )
    scan = scan_package_dir(pkg)
    assert scan.composed_from == []
    assert {p.name for p in scan.agents} == {"AGENTS.md"}

    reg = PersonaRegistry(state_path=tmp_path / "personas.json")
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    out = preview_or_install(reg, store, pkg, decisions={})
    assert out["ok"] is True
    assert "custom-agents" in out["installed"]["agents"]
