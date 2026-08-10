"""Skill / persona wiring for filter_customs_importers (D-108)."""

from __future__ import annotations

from pathlib import Path

from coworker.skills.base import _parse_skill


ROOT = Path(__file__).resolve().parents[1]
EXPORT = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-export-prospecting"
    / "SKILL.md"
)
WORKFLOW = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-export-prospecting"
    / "references"
    / "prospecting-workflow.md"
)
BUYER = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-buyer-discovery"
    / "SKILL.md"
)
PERSONA = ROOT / "coworker" / "personas" / "builtin" / "export-sales-lobster.md"


def test_export_documents_filter_customs_importers():
    export = _parse_skill(EXPORT)
    text = export.instructions + WORKFLOW.read_text(encoding="utf-8")
    assert "filter_customs_importers" in text
    assert "海关" in text or "提单" in text
    assert "终端买家" in text or "收货方" in text
    assert "Comtrade" in text or "lookup_trade_flow" in text
    assert "不在本 Skill 内嵌" in text or "平台 Tool" in text
    assert "xlsx" in text.lower() or "XLSX" in text


def test_buyer_discovery_mentions_customs_file_tool():
    skill = _parse_skill(BUYER)
    assert "filter_customs_importers" in skill.instructions
    assert "货代" in skill.instructions or "终端买家" in skill.instructions
    assert "xlsx" in skill.instructions.lower() or "XLSX" in skill.instructions


def test_export_sales_lobster_mentions_customs_tool():
    text = PERSONA.read_text(encoding="utf-8")
    assert "filter_customs_importers" in text
    assert "海关" in text or "提单" in text
    assert "xlsx" in text.lower() or "XLSX" in text


def test_tool_registered_on_engine() -> None:
    from coworker.agent import build_engine
    from coworker.agents import chat_agent
    from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient

    class _Stub(ProviderClient):
        def complete(self, *, model, messages, tools=None, **s):
            return AssistantTurn(text="", finish_reason="stop")

        def capabilities(self, model):
            return ModelCapabilities()

    eng = build_engine(agent=chat_agent(), provider=_Stub())
    assert eng.registry.get("filter_customs_importers") is not None
