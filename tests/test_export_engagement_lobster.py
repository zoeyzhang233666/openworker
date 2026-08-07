"""Builtin export-engagement-lobster persona (D-094)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from coworker.personas.manifest import load_manifest_file
from coworker.personas.registry import PersonaRegistry
from coworker.permissions import Mode
from coworker.server.manager import SessionManager


SKILLS = [
    "chem-sales-engagement",
    "chem-product-intelligence",
    "chem-sales-quality-check",
]


def _manifest_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "coworker"
        / "personas"
        / "builtin"
        / "export-engagement-lobster.md"
    )


def test_export_engagement_lobster_manifest_contract():
    manifest = load_manifest_file(_manifest_path(), builtin=True)
    assert manifest.id == "export-engagement-lobster"
    assert manifest.name == "外贸转化龙虾"
    assert manifest.family == "knowledge"
    assert manifest.tools == ["files", "search", "shell", "todo"]
    assert manifest.default_permission_mode == "interactive"
    assert manifest.skills == SKILLS
    prompt = manifest.system_prompt
    for required in (
        "EngagementRun",
        "草稿 ≠ 发送",
        "岗位策略",
        "审批",
        "task-provided:",
        "chem-sales-quality-check",
    ):
        assert required in prompt


def test_export_engagement_lobster_not_default(tmp_path):
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")
    entry = registry.get("export-engagement-lobster")
    assert entry is not None
    assert entry.builtin is True
    assert registry.skill_ids("export-engagement-lobster") == SKILLS
    assert registry.default_id() == "cowork"
    assert registry.is_enabled("export-engagement-lobster") is False


def test_export_engagement_lobster_interactive_approvals(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    manager = SessionManager(data_dir=tmp_path / "state", mode=Mode.INTERACTIVE)
    manager.set_persona_enabled("export-engagement-lobster", True)
    engine = manager.get_engine(
        "export-engagement-permissions",
        agent="export-engagement-lobster",
        workspace=str(workspace),
    )
    assert engine is not None
    assert engine.permissions.evaluate("read_file", {"path": "a.md"}).allowed
    for tool_name, arguments, metadata in (
        ("write_file", {"path": "draft.json"}, None),
        ("run_shell", {"command": "python check_outreach.py"}, None),
        (
            "send_email",
            {"to": "buyer@example.com"},
            SimpleNamespace(requires_approval=True, category="connector"),
        ),
        (
            "crm_create_lead",
            {"company": "Example"},
            SimpleNamespace(requires_approval=True, category="connector"),
        ),
    ):
        decision = engine.permissions.evaluate(tool_name, arguments, metadata)
        assert decision.allowed is False
        assert decision.needs_user is True
