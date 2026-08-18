"""Finance skills must not reference the non-existent Wind tool (D-145)."""

from __future__ import annotations

from pathlib import Path

from coworker.agent import build_engine
from coworker.agents import chat_agent
from coworker.providers import ModelCapabilities
from coworker.runtime_paths import builtin_personas_dir, bundled_skills_dir
from coworker.skills.bootstrap import refresh_finance_skills_without_wind
from coworker.skills.store import SkillStore

WIND_TOOL = "wind_financial_reference_content"


class _Stub:
    def complete(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def capabilities(self, model):
        return ModelCapabilities()


def test_bundled_skills_have_no_wind_tool_name():
    root = bundled_skills_dir()
    offenders: list[str] = []
    for md in root.rglob("SKILL.md"):
        text = md.read_text(encoding="utf-8")
        if WIND_TOOL in text:
            offenders.append(str(md.relative_to(root)))
    assert offenders == [], f"Wind tool still mentioned in: {offenders}"


def test_chain_lobster_persona_has_no_wind_tool_name():
    md = builtin_personas_dir() / "chain-lobster.md"
    text = md.read_text(encoding="utf-8")
    assert WIND_TOOL not in text
    assert "验证层" in text or "不是单点故障" in text


def test_finance_skills_use_yahoo_and_web_and_unavailable():
    root = bundled_skills_dir()
    for name in ("market-analysis", "stock-analysis"):
        text = (root / name / "SKILL.md").read_text(encoding="utf-8")
        assert "lookup_yahoo_ohlc" in text
        assert "web_search" in text
        assert "web_fetch" in text
        assert "unavailable" in text.lower() or "无可靠结构化来源" in text
        assert WIND_TOOL not in text


def test_macro_analysis_has_no_wind():
    text = (bundled_skills_dir() / "macro-analysis" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert WIND_TOOL not in text
    assert "web_search" in text
    assert "web_fetch" in text


def test_build_engine_registers_yahoo_web_not_wind():
    eng = build_engine(agent=chat_agent(), provider=_Stub())
    names = set(eng.registry.names())
    assert "lookup_yahoo_ohlc" in names
    assert "web_search" in names
    assert "web_fetch" in names
    assert WIND_TOOL not in names


def test_refresh_overwrites_installed_wind_skill(tmp_path: Path):
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    skill = store.global_dir / "market-analysis"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: market-analysis\ndescription: old\n---\n"
        f"仅使用 {WIND_TOOL} 工具获取金融分析语料\n"
        f"所有分析内容必须来自 {WIND_TOOL}\n",
        encoding="utf-8",
    )
    updated = refresh_finance_skills_without_wind(store)
    assert "market-analysis" in updated
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert WIND_TOOL not in text
    assert "lookup_yahoo_ohlc" in text
    assert "web_search" in text
    assert refresh_finance_skills_without_wind(store) == []


def test_refresh_skips_uninstalled_bundled(tmp_path: Path):
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    store.mark_bundled_uninstalled("market-analysis")
    skill = store.global_dir / "market-analysis"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"must use {WIND_TOOL}\n", encoding="utf-8")
    assert refresh_finance_skills_without_wind(store) == []
    assert WIND_TOOL in (skill / "SKILL.md").read_text(encoding="utf-8")
