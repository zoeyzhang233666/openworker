"""Runtime renewal replaces D-165/D-202 keyword routing contracts."""
import pytest
from coworker.config import Config
from coworker.turn_planner import TurnPlanner, TurnOrigin, PromptProfile

TOOLS = ("read_file", "run_shell", "load_skill", "start_subagent", "web_search", "mcp_rare")

@pytest.mark.parametrize("question", ["你好", "柠檬酸现货价格", "甲醇期现套利深度研究", "液化气周报", "使用冷门 MCP"])
@pytest.mark.parametrize("source", [None, {"connector": "wecom", "target": "test"}, {"connector": "weixin", "target": "test"}])
def test_general_plan_keeps_capabilities_and_full_budget(question, source):
    plan = TurnPlanner(config=Config(), available_tool_names=lambda: TOOLS).plan(question, source=source)
    assert plan.execution_profile.max_iterations == 150
    assert plan.execution_profile.allowed_tool_names is None
    assert plan.capability_plan.selected_tool_names == TOOLS
    assert plan.skill_names is None
    assert plan.market_selection is None and not plan.subagent_eligible
    assert not plan.scenario_projection_applied
    assert plan.prompt_profile == PromptProfile.AGENT

@pytest.mark.parametrize("text,denied", [("不要联网", "web_search"), ("不要使用任何工具", "read_file"), ("不要搜索", "web_search")])
def test_explicit_user_constraints_apply_even_with_old_flags(text, denied):
    plan = TurnPlanner(config=Config(request_routing_enabled=False), available_tool_names=lambda: TOOLS).plan(text)
    assert denied not in plan.capability_plan.selected_tool_names
