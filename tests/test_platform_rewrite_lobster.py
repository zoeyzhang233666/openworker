"""Builtin platform-rewrite-lobster persona (content rewrite M1)."""

from __future__ import annotations

from pathlib import Path

from coworker.personas.manifest import load_manifest_file
from coworker.personas.registry import PersonaRegistry
from coworker.permissions import Mode
from coworker.secrets import state_dir
from coworker.server.manager import SessionManager
from coworker.skills.bootstrap import BUNDLED_DIR, seed_bundled_skills
from coworker.skills.store import SkillStore


SKILLS = [
    "chem-rewrite-brief",
    "chem-platform-rewrite",
    "chem-content-policy",
    "chem-content-quality-check",
]


def _manifest_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "coworker"
        / "personas"
        / "builtin"
        / "platform-rewrite-lobster.md"
    )


def test_platform_rewrite_lobster_manifest_contract():
    manifest = load_manifest_file(_manifest_path(), builtin=True)

    assert manifest.id == "platform-rewrite-lobster"
    assert manifest.name == "化工内容重构龙虾"
    assert manifest.family == "knowledge"
    assert manifest.tools == ["files", "search", "shell", "todo"]
    assert manifest.messaging is False
    assert manifest.connectors is False
    assert manifest.default_permission_mode == "interactive"
    assert manifest.skills == SKILLS

    prompt = manifest.system_prompt
    for required in (
        "事实保持",
        "RewriteBrief",
        "load_skill",
        "chem-rewrite-brief",
        "chem-platform-rewrite",
        "chem-content-policy",
        "chem-content-quality-check",
        "ready_for_publish_review",
        "不得主动联网",
        "自动发帖",
        "【标题】",
        "【口播稿】",
    ):
        assert required in prompt


def test_platform_rewrite_lobster_discovered_but_not_default(tmp_path):
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")

    entry = registry.get("platform-rewrite-lobster")
    assert entry is not None
    assert entry.builtin is True
    assert registry.skill_ids("platform-rewrite-lobster") == SKILLS
    assert registry.default_id() == "cowork"
    assert registry.is_enabled("platform-rewrite-lobster") is False


def test_platform_rewrite_pack_seeds_and_session_loads(tmp_path: Path) -> None:
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))
    assert set(SKILLS) <= installed

    manager_data = tmp_path / "manager-data"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    assert manager_data.resolve() != state_dir().resolve()
    manager = SessionManager(data_dir=manager_data)
    manager.set_persona_enabled("platform-rewrite-lobster", True)
    engine = manager.get_engine(
        "platform-rewrite-runtime",
        agent="platform-rewrite-lobster",
        workspace=str(workspace),
    )
    assert engine is not None
    assert engine.permissions.mode is Mode.INTERACTIVE
    for name in SKILLS:
        result = engine.registry.execute("load_skill", {"name": name})
        assert "error" not in result, result
        assert Path(result["resources_path"]).resolve() == (
            manager_data / "skills" / name
        ).resolve()
        assert (BUNDLED_DIR / name / "SKILL.md").is_file()
