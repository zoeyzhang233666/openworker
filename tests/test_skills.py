"""Agents (Code/Chat) + SKILL.md loader (catalog + load_skill)."""

from __future__ import annotations

from coworker.agent import build_engine
from coworker.agents import AgentContext, chat_agent, code_agent, get_agent
from coworker.providers import ModelCapabilities
from coworker.skills import (
    SkillLoader,
    select_skill_names,
    skill_catalog_text,
    skill_tools,
)
from coworker.tools import ToolRegistry
from coworker.tools.shell import LocalExecutor
from coworker.tools.todo import TodoList


class _Stub:
    def complete(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def capabilities(self, model):
        return ModelCapabilities()


# -- agents ---------------------------------------------------------------------


def test_code_agent_tools(tmp_path):
    ex = LocalExecutor(cwd=tmp_path, default_timeout=5)
    try:
        ctx = AgentContext(workspace=tmp_path, executor=ex, todo=TodoList())
        names = {getattr(t, "__name__", "?") for t in code_agent().build_tools(ctx)}
        assert {
            "read_file",
            "write_file",
            "git_status",
            "run_shell",
            "todo_write",
        } <= names
    finally:
        ex.close()


def test_chat_agent_has_no_workspace_tools():
    assert chat_agent().build_tools(AgentContext()) == []
    assert chat_agent().needs_workspace is False
    assert code_agent().needs_workspace is True


def test_get_agent_fallback():
    assert get_agent("chat").name == "chat"
    # Unknown ids fall back to the default persona (Cowork), per the persona registry.
    assert get_agent("nope").name == "cowork"


# -- SKILL.md loader ------------------------------------------------------------


def _make_skill(skills_dir, name, desc, body):
    d = skills_dir / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {desc}\n---\n{body}", encoding="utf-8"
    )


def test_skill_loader_catalog_and_load(tmp_path):
    skills_dir = tmp_path / "skills"
    _make_skill(
        skills_dir, "pdf", "extract text from PDFs", "Use pdfplumber to extract text."
    )
    loader = SkillLoader([skills_dir])

    assert loader.catalog() == [
        {"name": "pdf", "description": "extract text from PDFs"}
    ]
    assert "pdf: extract text from PDFs" in skill_catalog_text(loader)

    reg = ToolRegistry()
    reg.register_all(skill_tools(loader))
    loaded = reg.execute("load_skill", {"name": "pdf"})
    assert "pdfplumber" in loaded["instructions"]
    assert reg.execute("load_skill", {"name": "missing"})["error"]
    assert reg.execute("search_skills", {"query": "extract PDF"}) == {
        "skills": [{"name": "pdf", "description": "extract text from PDFs"}]
    }


def test_skill_metadata_search_caps_ordinary_but_keeps_preferred(tmp_path):
    skills_dir = tmp_path / "skills"
    for index in range(12):
        _make_skill(
            skills_dir,
            f"chem-{index}",
            "化学 数据 查询与分析",
            f"instructions {index}",
        )
    loader = SkillLoader([skills_dir])
    ordinary = select_skill_names(loader, "请做化学数据查询分析", limit=8)
    assert len(ordinary) == 8
    preferred = select_skill_names(
        loader,
        "无匹配",
        preferred=[f"chem-{index}" for index in range(10)],
        limit=8,
    )
    assert preferred == tuple(f"chem-{index}" for index in range(10))


# -- engine assembly per agent --------------------------------------------------


def test_build_engine_chat(tmp_path):
    engine = build_engine(agent=chat_agent(), provider=_Stub())
    assert "load_skill" in engine.registry.names()
    assert "read_file" not in engine.registry.names()
    assert engine.executor is None
    assert engine.agent_name == "chat"
    # D-063 / D-180: Mermaid + chart guidance (Simplified Chinese) injected for every agent.
    sys_msg = engine.messages[0]["content"]
    assert "每条边必须有语义标签" in sys_msg
    assert "```chart" in sys_msg and "chart-image" in sys_msg
    assert "时间序列" in sys_msg and "≥2" in sys_msg
    assert "价格走势" in sys_msg
    assert "顶层字符串数组" in sys_msg
    assert "lookup_yahoo_ohlc" in sys_msg and "candlestick" in sys_msg
    assert "lookup_cn_stock_ohlc" in sys_msg and "lookup_cn_futures_ohlc" in sys_msg
    assert "from_tool" in sys_msg and "短引用" in sys_msg
    assert "产物" in sys_msg and "预览" in sys_msg
    assert "日线" in sys_msg
    assert "`lookup_cn_*_minute`" in sys_msg
    assert "(or ≥12 monthly points)" not in sys_msg
    assert "interval=1wk" in sys_msg and "1mo" in sys_msg
    assert "中文名" in sys_msg
    assert "stages" in sys_msg and "tone" in sys_msg
    assert "主导驱动" in sys_msg
    assert "具体价位" in sys_msg
    assert "load_skill" in sys_msg and "grilling" in sys_msg
    assert "网页" in sys_msg
    assert "对齐" in sys_msg
    assert "气泡要短" in sys_msg
    assert 'A -->|"采购"| B' in sys_msg
    assert "旁白：" in sys_msg and "工具效率：" in sys_msg

def test_build_engine_code_has_agents_md_and_skills(tmp_path):
    (tmp_path / "AGENTS.md").write_text("PROJECT RULE: prefer pathlib.")
    engine = build_engine(agent=code_agent(), workspace=tmp_path, provider=_Stub())
    try:
        assert "prefer pathlib" in engine.messages[0]["content"]
        assert "todo_write" in engine.registry.names()
        assert "load_skill" in engine.registry.names()
        assert engine.agent_name == "code"
    finally:
        engine.executor.close()
