"""Skill / persona wiring for FX + Wikipedia + VAT (D-117)."""

from __future__ import annotations

from pathlib import Path

from coworker.skills.base import _parse_skill


ROOT = Path(__file__).resolve().parents[1]


def test_inquiry_to_quote_documents_fx():
    skill = _parse_skill(
        ROOT / "coworker/skills/bundled/chem-inquiry-to-quote/SKILL.md"
    )
    assert "lookup_fx_rate" in skill.instructions
    assert "calculate_quote" in skill.instructions


def test_export_engagement_lobster_documents_fx():
    text = (
        ROOT / "coworker/personas/builtin/export-engagement-lobster.md"
    ).read_text(encoding="utf-8")
    assert "lookup_fx_rate" in text


def test_product_intelligence_documents_wikipedia():
    skill = _parse_skill(
        ROOT / "coworker/skills/bundled/chem-product-intelligence/SKILL.md"
    )
    assert "lookup_wikipedia" in skill.instructions
    assert "lookup_chemical_identity" in skill.instructions
    assert "search_huagongshe" in skill.instructions
    assert "lookup_huagongshe_chemical" in skill.instructions
    assert "Lead" in skill.instructions or "评分" in skill.instructions


def test_sales_lobsters_document_wikipedia_or_vat():
    export = (
        ROOT / "coworker/personas/builtin/export-sales-lobster.md"
    ).read_text(encoding="utf-8")
    domestic = (
        ROOT / "coworker/personas/builtin/domestic-sales-lobster.md"
    ).read_text(encoding="utf-8")
    radar = (
        ROOT / "coworker/personas/builtin/opportunity-radar-lobster.md"
    ).read_text(encoding="utf-8")
    assert "lookup_wikipedia" in export and "validate_eu_vat" in export
    assert "search_huagongshe" in export
    assert "lookup_wikipedia" in domestic
    assert "search_huagongshe" in domestic
    assert "lookup_wikipedia" in radar and "validate_eu_vat" in radar


def test_company_qualification_documents_vat():
    skill = _parse_skill(
        ROOT / "coworker/skills/bundled/chem-company-qualification/SKILL.md"
    )
    assert "validate_eu_vat" in skill.instructions
