"""Builtin export-sales-lobster persona (D-087)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from coworker.personas.manifest import load_manifest_file
from coworker.personas.registry import PersonaRegistry
from coworker.permissions import Mode
from coworker.server.manager import SessionManager


SKILLS = [
    "chem-export-prospecting",
    "chem-product-intelligence",
    "chem-buyer-discovery",
    "chem-company-qualification",
    "chem-lead-ranking",
]


def _manifest_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "coworker"
        / "personas"
        / "builtin"
        / "export-sales-lobster.md"
    )


def test_export_sales_lobster_manifest_declares_approved_sales_contract():
    manifest = load_manifest_file(_manifest_path(), builtin=True)

    assert manifest.id == "export-sales-lobster"
    assert manifest.name == "外贸拓客龙虾"
    assert manifest.family == "knowledge"
    assert manifest.tools == ["files", "search", "shell", "todo"]
    assert manifest.default_permission_mode == "interactive"
    assert manifest.skills == SKILLS

    prompt = manifest.system_prompt
    for required in (
        "客户清单",
        "不是研究报告",
        "EvidenceItem",
        "Lead Fit Score",
        "Evidence Confidence",
        "部分失败",
        "不可信数据",
        "姓名、邮箱或采购量",
        "草稿",
        "发送",
        "审批",
        "外部写入",
    ):
        assert required in prompt


def test_export_sales_lobster_is_discovered_builtin_but_not_default(tmp_path):
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")

    entry = registry.get("export-sales-lobster")
    assert entry is not None
    assert entry.builtin is True
    assert registry.skill_ids("export-sales-lobster") == SKILLS
    assert registry.default_id() == "cowork"


def test_export_sales_lobster_runtime_keeps_interactive_approval_boundary(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    manager = SessionManager(data_dir=tmp_path / "state", mode=Mode.INTERACTIVE)
    manager.set_persona_enabled("export-sales-lobster", True)

    engine = manager.get_engine(
        "export-sales-permissions",
        agent="export-sales-lobster",
        workspace=str(workspace),
    )

    assert engine is not None
    assert engine.permissions.mode is Mode.INTERACTIVE
    assert engine.permissions.evaluate("read_file", {"path": "input.md"}).allowed

    for tool_name, arguments, metadata in (
        ("write_file", {"path": "lead-list.json"}, None),
        ("run_shell", {"command": "python score_lead.py"}, None),
        (
            "crm_create_lead",
            {"company": "Example"},
            SimpleNamespace(requires_approval=True, category="connector"),
        ),
    ):
        decision = engine.permissions.evaluate(tool_name, arguments, metadata)
        assert decision.allowed is False
        assert decision.needs_user is True
