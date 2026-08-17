"""HARD STOP E — Capability Preservation Gate (automated suites + kill-switch matrix)."""

from __future__ import annotations

from coworker.config import Config
from coworker.execution_profile import RequestRoute, make_execution_profile
from coworker.request_router import route_request
from coworker.tool_policy import TurnToolPolicy
from coworker.tool_projection import project_provider_visible_schemas
from coworker.tools.registry import ToolRegistry


def _reg(*names: str) -> ToolRegistry:
    registry = ToolRegistry()
    for name in names:

        def _make(n: str):
            def _fn(*, x: str = "1") -> str:
                """Doc."""
                return x

            _fn.__name__ = n
            return _fn

        registry.register(_make(name))
    return registry


def test_memory_intent_is_agent_not_fast_chat():
    cfg = Config(request_routing_enabled=True)
    d = route_request("记住我以后喜欢简短回答", config=cfg)
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.allowed_tool_names is None


def test_skill_intent_keeps_load_skill_when_projected():
    cfg = Config(request_routing_enabled=True, tool_projection_enabled=True)
    d = route_request("用指定 skill 分析这份报告", config=cfg)
    assert d is not None
    assert d.route is RequestRoute.AGENT
    registry = _reg("load_skill", "read_file", "web_search")
    out = project_provider_visible_schemas(
        registry,
        tool_projection_enabled=True,
        profile=make_execution_profile(d.route, cfg),
        tool_policy=d.tool_policy,
    )
    names = {s["function"]["name"] for s in out}
    assert "load_skill" in names


def test_pending_ask_user_outranks_fast_path():
    from coworker.request_router import RouterContext

    cfg = Config(request_routing_enabled=True)
    d = route_request(
        "你好",
        config=cfg,
        context=RouterContext(pending_ask_user=True),
    )
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.source == "pending_state"


def test_schedule_intent_is_agent():
    cfg = Config(request_routing_enabled=True)
    d = route_request("明天上午 9 点提醒我联系 BASF", config=cfg)
    assert d is not None
    assert d.route is RequestRoute.AGENT


def test_kill_switches_matrix_routing_vs_projection():
    """Independent ON/OFF domains — one switch must not mask the other."""
    registry = _reg("read_file", "web_search", "ask_user")

    # routing OFF, projection ON + attached FAST profile → tools=None
    cfg_po = Config(request_routing_enabled=False, tool_projection_enabled=True)
    assert route_request("你好", config=cfg_po) is None
    fast = make_execution_profile(RequestRoute.FAST_CHAT, cfg_po)
    assert (
        project_provider_visible_schemas(
            registry,
            tool_projection_enabled=True,
            profile=fast,
            tool_policy=TurnToolPolicy(),
        )
        is None
    )

    # routing ON, projection OFF + FAST decision → still full schemas
    cfg_ro = Config(request_routing_enabled=True, tool_projection_enabled=False)
    d = route_request("你好", config=cfg_ro)
    assert d is not None
    assert d.route is RequestRoute.FAST_CHAT
    profile = make_execution_profile(d.route, cfg_ro, allowed_tool_names=d.allowed_tool_names)
    out = project_provider_visible_schemas(
        registry,
        tool_projection_enabled=False,
        profile=profile,
        tool_policy=d.tool_policy,
    )
    assert out is not None
    assert {s["function"]["name"] for s in out} == {
        "read_file",
        "web_search",
        "ask_user",
    }


def test_post_step59_all_risky_defaults_candidate_on():
    """Step 59 flips Emergency Finalization; all four risky built-in defaults are candidate ON."""
    cfg = Config()
    assert cfg.request_routing_enabled is True
    assert cfg.tool_projection_enabled is True
    assert cfg.structured_tools_true_streaming_enabled is True
    assert cfg.emergency_finalization_enabled is True
