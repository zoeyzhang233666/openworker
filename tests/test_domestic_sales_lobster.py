"""Builtin domestic-sales-lobster persona (D-092)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from coworker.personas.manifest import load_manifest_file
from coworker.personas.registry import PersonaRegistry
from coworker.permissions import Mode
from coworker.server.manager import SessionManager


SKILLS = [
    "chem-domestic-prospecting",
    "chem-product-intelligence",
    "chem-buyer-discovery",
    "chem-company-qualification",
    "chem-lead-ranking",
    "chem-lead-list",
]


def _manifest_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "coworker"
        / "personas"
        / "builtin"
        / "domestic-sales-lobster.md"
    )


def test_domestic_sales_lobster_manifest_declares_approved_sales_contract():
    manifest = load_manifest_file(_manifest_path(), builtin=True)

    assert manifest.id == "domestic-sales-lobster"
    assert manifest.name == "内贸拓客龙虾"
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
        "统一社会信用代码",
        "手机",
        "微信",
        "草稿",
        "发送",
        "审批",
        "外部写入",
    ):
        assert required in prompt


def test_domestic_sales_lobster_is_discovered_builtin_but_not_default(tmp_path):
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")

    entry = registry.get("domestic-sales-lobster")
    assert entry is not None
    assert entry.builtin is True
    assert registry.skill_ids("domestic-sales-lobster") == SKILLS
    assert registry.default_id() == "cowork"
    assert registry.is_enabled("domestic-sales-lobster") is False


def test_domestic_sales_lobster_runtime_keeps_interactive_approval_boundary(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    manager = SessionManager(data_dir=tmp_path / "state", mode=Mode.INTERACTIVE)
    manager.set_persona_enabled("domestic-sales-lobster", True)

    engine = manager.get_engine(
        "domestic-sales-permissions",
        agent="domestic-sales-lobster",
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
