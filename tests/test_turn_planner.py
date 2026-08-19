from __future__ import annotations

from dataclasses import replace

from coworker.config import Config
from coworker.execution_profile import RequestRoute
from coworker.request_router import RouterContext
from coworker.turn_planner import PromptProfile, TurnPlanner


TOOLS = (
    "read_file",
    "write_file",
    "run_shell",
    "ask_user",
    "propose_plan",
    "request_directory",
    "memory_read",
    "remember",
    "schedule_task",
    "send_message",
    "load_skill",
    "search_skills",
    "lookup_cn_stock_quote",
    "lookup_cn_stock_ohlc",
    "lookup_cn_futures_quote",
    "lookup_cn_futures_ohlc",
    "lookup_yahoo_ohlc",
    "web_search",
    "web_fetch",
    "mcp__chem-data-hub__get_price_trend",
    "mcp_custom_unknown",
)


def _planner(context: RouterContext | None = None) -> TurnPlanner:
    return TurnPlanner(
        config=Config(),
        available_tool_names=lambda: TOOLS,
        context_provider=lambda: context or RouterContext(),
        skill_selector=lambda _query, preferred: tuple(preferred) or ("matched",),
    )


def test_turn_planner_fast_chat_is_direct_tools_none_and_no_skills():
    plan = _planner().plan("你好")
    assert plan.decision is not None
    assert plan.decision.route is RequestRoute.FAST_CHAT
    assert plan.execution_profile is not None
    assert plan.execution_profile.tools_enabled is False
    assert plan.execution_profile.allowed_tool_names == ()
    assert plan.prompt_profile is PromptProfile.FAST
    assert plan.skill_names == ()
    assert plan.show_reasoning is True


def test_turn_planner_verified_reselects_against_live_registry():
    plan = _planner().plan("贵州茅台最新股价和日线 K 线")
    assert plan.decision is not None
    assert plan.decision.route is RequestRoute.VERIFIED
    assert plan.execution_profile is not None
    assert plan.execution_profile.allowed_tool_names == (
        "lookup_cn_stock_quote",
        "lookup_cn_stock_ohlc",
    )
    assert plan.prompt_profile is PromptProfile.VERIFIED_MARKET
    assert plan.skill_names == ()


def test_turn_planner_explicit_spot_uses_only_chem_data_hub():
    plan = _planner().plan("查甲醇现货价格")
    assert plan.decision is not None
    assert plan.decision.route is RequestRoute.VERIFIED
    assert plan.execution_profile is not None
    assert plan.execution_profile.allowed_tool_names == (
        "mcp__chem-data-hub__get_price_trend",
    )
    assert plan.market_selection is not None
    assert plan.prompt_profile is PromptProfile.VERIFIED_MARKET


def test_turn_planner_bare_methanol_requires_ask_user_not_web():
    plan = _planner().plan("查甲醇价格")
    assert plan.execution_profile is not None
    allowed = set(plan.execution_profile.allowed_tool_names or ())
    assert "ask_user" in allowed
    assert "lookup_cn_futures_ohlc" in allowed
    assert "mcp__chem-data-hub__get_price_trend" in allowed
    assert "web_search" not in allowed
    assert "web_fetch" not in allowed
    assert plan.market_selection is not None
    assert plan.market_selection.needs_clarification


def test_turn_planner_wti_futures_promotes_market_fallback_to_verified_yahoo():
    plan = _planner().plan("查 WTI 原油期货")
    assert plan.decision is not None
    assert plan.decision.route is RequestRoute.VERIFIED
    assert plan.decision.source == "market_intent"
    assert plan.execution_profile is not None
    assert plan.execution_profile.allowed_tool_names == ("lookup_yahoo_ohlc",)
    assert plan.prompt_profile is PromptProfile.VERIFIED_MARKET


def test_turn_planner_agent_action_keeps_workspace_and_selected_market_tool():
    plan = _planner().plan("查甲醇现货价格并写入 report.md")
    assert plan.decision is not None
    assert plan.decision.route is RequestRoute.AGENT
    allowed = set(plan.execution_profile.allowed_tool_names or ())
    assert "write_file" in allowed
    assert "mcp__chem-data-hub__get_price_trend" in allowed
    assert "lookup_cn_futures_ohlc" not in allowed
    assert "web_search" not in allowed
    assert plan.market_selection is not None


def test_turn_planner_projects_strong_agent_capability_pack():
    plan = _planner().plan("读取并修改这个 Python 文件，然后运行测试")
    assert plan.decision is not None
    assert plan.decision.route is RequestRoute.AGENT
    allowed = set(plan.execution_profile.allowed_tool_names or ())
    assert {"read_file", "write_file", "run_shell"} <= allowed
    assert {"ask_user", "propose_plan", "request_directory"} <= allowed
    assert "memory_read" not in allowed
    assert plan.prompt_profile is PromptProfile.AGENT_WORKSPACE
    assert plan.skill_names == ("matched",)


def test_turn_planner_uses_targeted_prompt_for_memory_without_workspace_context():
    plan = _planner().plan("记住我偏好简体中文")
    assert plan.decision is not None
    assert plan.decision.route is RequestRoute.AGENT
    assert plan.execution_profile is not None
    allowed = set(plan.execution_profile.allowed_tool_names or ())
    assert {"memory_read", "remember"} <= allowed
    assert "read_file" not in allowed
    assert plan.prompt_profile is PromptProfile.AGENT_TARGETED


def test_turn_planner_unknown_mcp_and_ambiguous_actions_keep_full_registry():
    mcp = _planner().plan("用 MCP connector 处理这个请求")
    assert mcp.execution_profile is not None
    assert mcp.execution_profile.allowed_tool_names is None

    ambiguous = _planner().plan("帮我处理一下这个")
    assert ambiguous.execution_profile is not None
    assert ambiguous.execution_profile.allowed_tool_names is None


def test_turn_planner_guards_attachment_source_skill_persona_and_resume():
    planner = _planner()
    attachment = planner.plan(
        [{"type": "text", "text": "你好"}, {"type": "image_url", "image_url": {}}]
    )
    source = planner.plan("你好", source={"kind": "slack"})
    forced = planner.plan("你好", display="/skill finance")
    resumed = planner.plan("(resumed)", durable_resume=True)
    for plan in (attachment, source, forced, resumed):
        assert plan.decision is not None
        assert plan.decision.route is RequestRoute.AGENT
        assert plan.execution_profile is not None
        assert plan.execution_profile.allowed_tool_names is None

    scheduled = planner.plan("⏰ Scheduled run — daily report\n\n读取文件并发送结果")
    assert scheduled.execution_profile is not None
    assert scheduled.execution_profile.allowed_tool_names is None

    persona = _planner(
        replace(
            RouterContext(),
            selected_persona_id="sales-lobster",
            is_default_persona=False,
        )
    ).plan("你好")
    assert persona.decision is not None
    assert persona.decision.route is RequestRoute.AGENT


def test_router_off_is_fully_legacy():
    planner = TurnPlanner(
        config=Config(request_routing_enabled=False),
        available_tool_names=lambda: TOOLS,
    )
    plan = planner.plan("你好")
    assert plan.prompt_profile is PromptProfile.LEGACY
    assert plan.execution_profile is None
    assert plan.skill_names is None


def test_tool_projection_off_keeps_market_policy_legacy_inert():
    planner = TurnPlanner(
        config=Config(tool_projection_enabled=False),
        available_tool_names=lambda: TOOLS,
    )
    plan = planner.plan("查甲醇现货价格")
    assert plan.decision is not None
    assert plan.decision.route is RequestRoute.VERIFIED
    assert plan.market_selection is None
    assert plan.prompt_profile is PromptProfile.VERIFIED
