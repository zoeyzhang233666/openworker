"""D-180/D-181: first-party system/tool prompts default to Simplified Chinese CoT + replies."""

from __future__ import annotations

import inspect

from coworker.agent import (
    _CLARIFY_POINTER,
    _DIAGRAM_GUIDANCE,
    _DIRECT_ANSWER_CORE,
    _INLINE_CHART_GUIDANCE,
    _LONG_TASK_GUIDANCE,
    _MEMORY_GUIDANCE,
    _MEMORY_OFF_NOTICE,
    _NARRATION_GUIDANCE,
    _PLAN_MODE_CONTEXT,
    _SUBAGENT_DELEGATION_CONTEXT,
    _TARGETED_ACTION_CORE,
    _TOOL_BATCHING_GUIDANCE,
    _DISCUSS_MODE_CONTEXT,
)
from coworker.agents.cowork import COWORK_INSTRUCTIONS, cowork_agent
from coworker.market_intent import (
    MarketIntentKind,
    resolve_market_tools,
    render_market_turn_context,
)
from coworker.skills.base import SkillLoader, skill_catalog_text, skill_tools
from coworker.subagents.registry import (
    EXPLORER_INSTRUCTIONS,
    RESEARCHER_INSTRUCTIONS,
    WORKER_INSTRUCTIONS,
)
from coworker.subagents import tools as subagent_tools_mod
from coworker.tools.ask import _ASK_SCHEMA
from coworker.tools.files import _SCHEMA as _READ_FILE_SCHEMA
from coworker.tools.search import _SCHEMA as _GREP_SCHEMA
from coworker.tools.shell import _RUN_SHELL_SCHEMA, _TASK_KILL_SCHEMA, _TASK_OUTPUT_SCHEMA
from coworker.tools.todo import _TODO_SCHEMA
from coworker.web.fetch import _SCHEMA as _WEB_FETCH_SCHEMA
from coworker.web.tool import _SCHEMA as _WEB_SEARCH_SCHEMA


_LANG = "用简体中文思考与回复"


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def test_direct_and_targeted_cores_require_chinese_think_and_reply():
    for text in (_DIRECT_ANSWER_CORE, _TARGETED_ACTION_CORE):
        assert "ChemClaw" in text
        assert _LANG in text
        assert "Reply in Simplified Chinese" not in text
        assert "You are ChemClaw" not in text


def test_cowork_instructions_are_chinese_with_language_policy():
    assert "ChemClaw" in COWORK_INSTRUCTIONS
    assert _LANG in COWORK_INSTRUCTIONS
    assert "grep" in COWORK_INSTRUCTIONS
    assert "read_file" in COWORK_INSTRUCTIONS
    assert "todo_write" in COWORK_INSTRUCTIONS
    assert "._chemclaw/charts/" in COWORK_INSTRUCTIONS
    assert "You are ChemClaw —" not in COWORK_INSTRUCTIONS
    assert cowork_agent().system_prompt == COWORK_INSTRUCTIONS


def test_shared_guidance_blocks_are_chinese():
    blocks = (
        _DISCUSS_MODE_CONTEXT,
        _PLAN_MODE_CONTEXT,
        _MEMORY_GUIDANCE,
        _MEMORY_OFF_NOTICE,
        _NARRATION_GUIDANCE,
        _TOOL_BATCHING_GUIDANCE,
        _SUBAGENT_DELEGATION_CONTEXT,
        _LONG_TASK_GUIDANCE,
        _DIAGRAM_GUIDANCE,
        _INLINE_CHART_GUIDANCE,
        _CLARIFY_POINTER,
    )
    for text in blocks:
        assert _has_cjk(text), text[:80]
        assert "Narration:" not in text
        assert "Tool efficiency:" not in text
        assert "Long-turn research:" not in text


def test_long_task_and_clarify_keep_product_semantics():
    assert "._chemclaw/charts/" in _LONG_TASK_GUIDANCE
    assert "会话工作区根目录" in _LONG_TASK_GUIDANCE or "工作区根" in _LONG_TASK_GUIDANCE
    assert "网页版" in _LONG_TASK_GUIDANCE
    assert "气泡" in _LONG_TASK_GUIDANCE
    assert "做网页版" in _LONG_TASK_GUIDANCE
    assert "网页版" in _CLARIFY_POINTER
    assert "短" in _CLARIFY_POINTER


def test_core_tool_descriptions_are_chinese_names_stay_english():
    specs = (
        (_READ_FILE_SCHEMA, "read_file"),
        (_GREP_SCHEMA, "grep"),
        (_RUN_SHELL_SCHEMA, "run_shell"),
        (_TASK_OUTPUT_SCHEMA, "shell_task_output"),
        (_TASK_KILL_SCHEMA, "shell_task_kill"),
        (_TODO_SCHEMA, "todo_write"),
        (_ASK_SCHEMA, "ask_user"),
        (_WEB_SEARCH_SCHEMA, "web_search"),
        (_WEB_FETCH_SCHEMA, "web_fetch"),
    )
    for schema, name in specs:
        fn = schema["function"]
        assert fn["name"] == name
        desc = fn["description"]
        assert _has_cjk(desc), desc
        assert "Read a text file" not in desc
        assert "Search the workspace" not in desc
        assert "Run a shell command" not in desc
        props = fn["parameters"].get("properties") or {}
        for key, meta in props.items():
            assert key.isascii()
            if isinstance(meta, dict) and "description" in meta:
                d = meta["description"]
                if isinstance(d, str) and d:
                    assert _has_cjk(d), f"{name}.{key}: {d}"


def test_d182_subagent_profile_instructions_are_chinese():
    for text in (
        EXPLORER_INSTRUCTIONS,
        RESEARCHER_INSTRUCTIONS,
        WORKER_INSTRUCTIONS,
    ):
        assert _LANG in text
        assert _has_cjk(text)
        assert "You are a" not in text


def test_d182_subagent_tool_docstrings_are_chinese():
    src = inspect.getsource(subagent_tools_mod)
    assert "把有界任务委派" in src
    assert "短窥" in src
    assert "Delegate a bounded" not in src
    assert "Short peek" not in src


def test_d182_skill_catalog_and_load_search_are_chinese(tmp_path):
    skill_dir = tmp_path / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: 演示技能\n---\n\n# Demo\n",
        encoding="utf-8",
    )
    loader = SkillLoader([tmp_path / "skills"])
    catalog = skill_catalog_text(loader)
    assert "可用技能" in catalog
    assert "load_skill" in catalog
    assert "Available skills" not in catalog

    tools = {fn.__name__: fn for fn in skill_tools(loader)}
    assert _has_cjk(tools["load_skill"].__doc__ or "")
    assert _has_cjk(tools["search_skills"].__doc__ or "")
    assert "Load a skill" not in (tools["load_skill"].__doc__ or "")
    assert "Search enabled" not in (tools["search_skills"].__doc__ or "")


def test_d182_market_scope_policy_is_chinese():
    from coworker.tools.registry import ToolDescriptor

    tools = [
        ToolDescriptor(
            "mcp__chem-data-hub__get_price_trend",
            "mcp",
            ("chem-data-hub",),
        ),
        ToolDescriptor("lookup_cn_futures_quote"),
        ToolDescriptor("lookup_cn_futures_ohlc"),
        ToolDescriptor("web_search"),
        ToolDescriptor("web_fetch"),
    ]
    spot = render_market_turn_context(
        resolve_market_tools("查甲醇现货价格", tools)
    )
    dual = render_market_turn_context(
        resolve_market_tools("结合现货看甲醇期货基差", tools)
    )
    assert resolve_market_tools("结合现货看甲醇期货基差", tools).intent.kind is (
        MarketIntentKind.CN_SPOT_FUTURES
    )
    for context in (spot, dual):
        assert "<market-scope-policy>" in context
        assert _has_cjk(context)
        assert "CHEMICAL SPOT" not in context
        assert "The user requested BOTH" not in context
        assert "Do not call CN futures" not in context
