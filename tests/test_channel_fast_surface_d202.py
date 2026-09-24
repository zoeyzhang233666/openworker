"""D-202 Channel fast surface and engine guards."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from coworker.connectors.context import reset_current_channel_target, set_current_channel_target
from coworker.providers.base import ToolCall
from coworker.reports.product_aliases import resolve_chem_product_name
from coworker.reports.tool_projection import project_market_tool_result
from coworker.turn_planner import PromptProfile, TurnPlanner
from coworker.config import Config
from coworker.execution_profile import RequestRoute


TOOLS = (
    "ask_user",
    "read_file",
    "write_file",
    "edit_file",
    "run_shell",
    "load_skill",
    "search_skills",
    "todo_write",
    "start_subagent",
    "web_search",
    "web_fetch",
    "mcp__chem-data-hub__get_price_trend",
    "mcp__chem-data-hub__list_market_news_live",
)


def _planner() -> TurnPlanner:
    return TurnPlanner(
        config=Config(
            request_routing_enabled=True,
            tool_projection_enabled=True,
            scenario_resolution_enabled=True,
        ),
        available_tool_names=lambda: TOOLS,
    )


def _wecom_source() -> dict:
    return {
        "connector": "wecom",
        "target": "wecom:default:user_alice",
        "kind": "dm",
    }


@pytest.mark.parametrize("text", ["生成液化气的市场周报", "帮我查一下甲醇现货价格", "给我柠檬酸价格走势图"])
def test_channel_and_desktop_share_general_execution(text):
    desktop = _planner().plan(text)
    channel = _planner().plan(text, source=_wecom_source())
    assert desktop.execution_profile == channel.execution_profile
    assert channel.execution_profile.max_iterations == 150
    assert channel.execution_profile.allowed_tool_names is None
    assert channel.skill_names is None
    assert set(channel.capability_plan.selected_tool_names) == set(TOOLS)


def test_resolve_lpg_alias() -> None:
    assert resolve_chem_product_name("液化气") == "液化石油气"
    assert resolve_chem_product_name("LPG") == "液化石油气"


def test_project_price_trend_compresses_payload() -> None:
    raw = {
        "data": [
            {"date": "2026-09-01", "price": 6128, "region": "华东", "spec": "民用气"},
            {"date": "2026-08-31", "price": 5984, "region": "华东", "spec": "民用气"},
        ]
    }
    projected = project_market_tool_result(
        raw,
        tool_name="mcp__chem-data-hub__get_price_trend",
        arguments={"product_name": "液化气"},
    )
    assert isinstance(projected, dict)
    assert projected["product_name"] == "液化石油气"
    assert projected["summary"]["observations"] == 2
    assert "note" in projected


def test_channel_defers_shell_to_permission_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    from coworker.engine import TurnEngine
    from coworker.tools import ToolRegistry

    registry = ToolRegistry()
    engine = TurnEngine(
        provider=MagicMock(),
        registry=registry,
        permissions=MagicMock(),
        model="test-model",
        approver=MagicMock(),
    )
    token = set_current_channel_target("wecom:default:alice")
    try:
        guard = engine._channel_delivery_tool_guard(
            ToolCall(id="1", name="run_shell", arguments={"command": "python x.py"})
        )
        assert guard is None
    finally:
        reset_current_channel_target(token)
