"""Builtin opportunity-radar-lobster persona (D-093)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from coworker.personas.manifest import load_manifest_file
from coworker.personas.registry import PersonaRegistry
from coworker.permissions import Mode
from coworker.server.manager import SessionManager


SKILLS = [
    "chem-opportunity-radar",
    "chem-product-intelligence",
    "chem-company-qualification",
    "chem-opportunity-scoring",
]


def _manifest_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "coworker"
        / "personas"
        / "builtin"
        / "opportunity-radar-lobster.md"
    )


def test_opportunity_radar_lobster_manifest_contract():
    manifest = load_manifest_file(_manifest_path(), builtin=True)
    assert manifest.id == "opportunity-radar-lobster"
    assert manifest.name == "商机雷达龙虾"
    assert manifest.family == "knowledge"
    assert manifest.tools == ["files", "search", "shell", "todo"]
    assert manifest.default_permission_mode == "interactive"
    assert manifest.skills == SKILLS
    prompt = manifest.system_prompt
    for required in (
        "商机清单",
        "不是研究报告",
        "OpportunityRadarRun",
        "Actionable",
        "审批",
        "chem-newbiz-lead",
        "task-provided:",
    ):
        assert required in prompt


def test_opportunity_radar_lobster_not_default(tmp_path):
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")
    entry = registry.get("opportunity-radar-lobster")
    assert entry is not None
    assert entry.builtin is True
    assert registry.skill_ids("opportunity-radar-lobster") == SKILLS
    assert registry.default_id() == "cowork"
    assert registry.is_enabled("opportunity-radar-lobster") is False


def test_opportunity_radar_lobster_interactive_approvals(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    manager = SessionManager(data_dir=tmp_path / "state", mode=Mode.INTERACTIVE)
    manager.set_persona_enabled("opportunity-radar-lobster", True)
    engine = manager.get_engine(
        "opportunity-radar-permissions",
        agent="opportunity-radar-lobster",
        workspace=str(workspace),
    )
    assert engine is not None
    assert engine.permissions.evaluate("read_file", {"path": "a.md"}).allowed
    for tool_name, arguments, metadata in (
        ("write_file", {"path": "opp.json"}, None),
        ("run_shell", {"command": "python score_opportunity.py"}, None),
        (
            "crm_create_lead",
            {"company": "Example"},
            SimpleNamespace(requires_approval=True, category="connector"),
        ),
    ):
        decision = engine.permissions.evaluate(tool_name, arguments, metadata)
        assert decision.allowed is False
        assert decision.needs_user is True
