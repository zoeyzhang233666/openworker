"""Skill / persona wiring for Comtrade lookup_trade_flow (D-103)."""

from __future__ import annotations

from pathlib import Path

from coworker.skills.base import _parse_skill


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-product-intelligence"
    / "SKILL.md"
)
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
PERSONA = ROOT / "coworker" / "personas" / "builtin" / "export-sales-lobster.md"


def test_product_and_export_document_lookup_trade_flow():
    product = _parse_skill(PRODUCT)
    export = _parse_skill(EXPORT)
    text = (
        product.instructions
        + export.instructions
        + WORKFLOW.read_text(encoding="utf-8")
    )
    assert "lookup_trade_flow" in text
    assert "Comtrade" in text or "comtrade" in text
    assert "买家" in text or "进口商" in text
    assert "不在本 Skill 内嵌" in text or "平台 Tool" in text


def test_export_sales_lobster_mentions_comtrade_tool():
    text = PERSONA.read_text(encoding="utf-8")
    assert "lookup_trade_flow" in text
    assert "Comtrade" in text or "贸易流" in text
