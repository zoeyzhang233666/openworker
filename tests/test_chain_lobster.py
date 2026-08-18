"""Builtin chain-lobster persona (D-072 / D-145)."""

from __future__ import annotations

from pathlib import Path

from coworker.personas.manifest import load_manifest_file
from coworker.personas.registry import PersonaRegistry


def test_chain_lobster_builtin_manifest_and_skills():
    md = (
        Path(__file__).resolve().parents[1]
        / "coworker"
        / "personas"
        / "builtin"
        / "chain-lobster.md"
    )
    m = load_manifest_file(md, builtin=True)
    assert m.id == "chain-lobster"
    assert m.name == "产业链龙虾"
    assert "Serenity" not in m.name
    assert "化工" in m.system_prompt or "产业链" in m.system_prompt
    assert "验证层" in m.system_prompt or "不是单点故障" in m.system_prompt
    assert "wind_financial_reference_content" not in m.system_prompt
    assert "lookup_yahoo_ohlc" in m.system_prompt
    expected = {
        "产业链层级测绘",
        "稀缺环节识别",
        "证据强弱分级",
        "证伪条件压力测试",
        "叙事到系统变化",
        "候选优先级排序",
        "研究对话推进",
        "pdf",
        "chart-image",
        "file-search",
        "multi-search-engine",
        "market-analysis",
        "stock-analysis",
        "chem-price-daily",
    }
    assert set(m.skills) == expected


def test_chain_lobster_registered_builtin(tmp_path):
    reg = PersonaRegistry(state_path=tmp_path / "personas.json")
    assert "chain-lobster" in reg.ids()
    entry = reg.get("chain-lobster")
    assert entry is not None and entry.builtin is True
    assert reg.skill_ids("chain-lobster") == [
        "产业链层级测绘",
        "稀缺环节识别",
        "证据强弱分级",
        "证伪条件压力测试",
        "叙事到系统变化",
        "候选优先级排序",
        "研究对话推进",
        "pdf",
        "chart-image",
        "file-search",
        "multi-search-engine",
        "market-analysis",
        "stock-analysis",
        "chem-price-daily",
    ]
    # Default product agent remains cowork (D-072 Def1).
    assert reg.default_id() == "cowork"
