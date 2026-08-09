"""Tests for format_lead_list / chem-lead-list."""

from __future__ import annotations

from pathlib import Path

from coworker.leads import format_lead_list, make_format_lead_list_tool
from coworker.skills.base import _parse_skill
from coworker.skills.bootstrap import seed_bundled_skills
from coworker.skills.store import SkillStore


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "chem-lead-list"


def test_format_buckets_and_csv():
    result = format_lead_list(
        {
            "list_id": "list-1",
            "title": "德国苯甲酸钠客户清单",
            "sku_summary": "苯甲酸钠食品级",
            "market_summary": "DE",
            "leads": [
                {
                    "company": "Beta GmbH",
                    "customer_type": "distributor",
                    "fit_score": 72,
                    "evidence_confidence": 55,
                    "match_reason": "分销商页面提及防腐剂",
                    "next_action": "补官网产品页",
                    "sales_status": "needs_review",
                },
                {
                    "company": "Alpha Chemie",
                    "customer_type": "manufacturer",
                    "fit_score": 88,
                    "evidence_confidence": 80,
                    "match_reason": "工厂+SKU 证据",
                    "next_action": "岗位开发信",
                    "sales_status": "contactable",
                },
                {
                    "company": "Zed Logistics",
                    "sales_status": "excluded",
                    "exclude_reason": "货代噪声",
                    "next_action": "不再搜索",
                },
            ],
        }
    )
    assert result.status == "ok"
    assert result.counts == {
        "contactable": 1,
        "needs_review": 1,
        "excluded": 1,
        "total": 3,
    }
    assert "Alpha Chemie" in result.markdown
    assert result.csv.splitlines()[0].startswith("company,")
    assert "Zed Logistics" in result.csv
    assert "货代噪声" in result.csv


def test_invalid_status_error():
    result = format_lead_list(
        {"leads": [{"company": "X", "sales_status": "weird"}]}
    )
    assert result.status == "error"
    assert result.csv == ""


def test_tool_and_engine_registration():
    tool = make_format_lead_list_tool()
    out = tool(leads=[{"company": "Acme", "sales_status": "contactable"}])
    assert out["status"] == "ok"
    assert tool.__coworker_schema__["function"]["name"] == "format_lead_list"

    from coworker.agent import build_engine
    from coworker.agents import chat_agent

    class _Stub:
        def complete(self, **_kw):
            from coworker.providers import AssistantTurn

            return AssistantTurn()

        def capabilities(self, _model):
            from coworker.providers.base import ModelCapabilities

            return ModelCapabilities()

    eng = build_engine(agent=chat_agent(), provider=_Stub())
    assert "format_lead_list" in eng.registry.names()


def test_skill_and_seed(tmp_path: Path):
    skill = _parse_skill(
        ROOT / "coworker" / "skills" / "bundled" / PACKAGE / "SKILL.md"
    )
    assert skill.name == PACKAGE
    assert "format_lead_list" in skill.instructions
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    assert PACKAGE in set(seed_bundled_skills(store))
