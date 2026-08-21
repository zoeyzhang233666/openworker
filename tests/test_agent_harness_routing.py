from __future__ import annotations

import time

from coworker.config import Config
from coworker.scenarios import ScenarioResolver
from coworker.capabilities import CapabilityResolver
from coworker.tools.registry import ToolDescriptor
from coworker.turn_planner import TurnPlanner


TOOLS = (
    ToolDescriptor(
        name="mcp__chem-data-hub__get_price_trend",
        category="mcp",
        capabilities=("chem-data-hub",),
    ),
    ToolDescriptor(name="lookup_cn_futures_quote"),
    ToolDescriptor(name="lookup_cn_futures_ohlc"),
    ToolDescriptor(name="lookup_chemical_identity"),
    ToolDescriptor(name="lookup_legal_entity"),
    ToolDescriptor(name="web_search"),
    ToolDescriptor(name="web_fetch"),
    ToolDescriptor(name="ask_user"),
    ToolDescriptor(name="start_subagent"),
    ToolDescriptor(name="background_task_status"),
    ToolDescriptor(name="background_task_output"),
    ToolDescriptor(name="background_task_send"),
    ToolDescriptor(name="background_task_stop"),
    ToolDescriptor(name="background_task_gather"),
)


def _planner() -> TurnPlanner:
    return TurnPlanner(
        config=Config(),
        available_tool_names=lambda: tuple(item.name for item in TOOLS),
        available_tools=lambda: TOOLS,
    )


def test_five_core_requests_flow_through_turn_planner_capability_projection() -> None:
    planner = _planner()
    futures = planner.plan("甲醇期货现在多少钱").preview()
    spot = planner.plan("甲醇现货多少钱").preview()
    ambiguous = planner.plan("甲醇最近走势").preview()
    identity = planner.plan("查询 CAS 67-56-1").preview()
    research = planner.plan("帮我深度研究万华化学未来半年 MDI").preview()
    crude_research = planner.plan("上海原油期货深度研究").preview()

    assert futures.scenario.scenario_id == "cn_futures_market"
    assert set(futures.selected_tool_names) == {
        "lookup_cn_futures_quote",
        "web_search",
        "web_fetch",
    }
    assert "web_search" not in futures.blocked_tool_names
    assert futures.subagent_eligible is False
    assert set(spot.selected_tool_names) == {
        "mcp__chem-data-hub__get_price_trend",
        "web_search",
        "web_fetch",
    }
    assert ambiguous.scenario.status == "ambiguous"
    assert set(ambiguous.selected_tool_names) == {"ask_user", "web_search", "web_fetch"}
    assert identity.selected_tool_names == ("lookup_chemical_identity",)
    assert research.scenario.scenario_id == "chemical_company_research"
    assert research.subagent_eligible is True
    assert research.subagent_started is False
    assert "start_subagent" in research.selected_tool_names
    assert "background_task_gather" in research.selected_tool_names
    assert "start_subagent" not in research.blocked_tool_names
    assert "start_subagent" not in identity.selected_tool_names
    assert crude_research.scenario.scenario_id == "chemical_market_research"
    assert crude_research.subagent_eligible is True
    assert "start_subagent" in crude_research.selected_tool_names

    asphalt = planner.plan("研究沥青期货产业链上下游套利怎么做")
    asphalt_preview = asphalt.preview()
    assert asphalt.decision is not None
    assert asphalt.decision.route.value == "deep_research"
    assert asphalt_preview.scenario.scenario_id == "chemical_market_research"
    assert asphalt_preview.subagent_eligible is True
    assert "start_subagent" in asphalt_preview.selected_tool_names
    selected = set(asphalt.execution_profile.allowed_tool_names or ())
    assert "mcp__chem-data-hub__get_price_trend" not in selected
    assert "lookup_cn_futures_quote" not in selected


def test_deterministic_resolution_and_cached_preview_meet_local_latency_targets() -> None:
    scenarios = ScenarioResolver()
    capabilities = CapabilityResolver()
    samples: list[float] = []
    for _ in range(1000):
        started = time.perf_counter()
        scenario = scenarios.resolve("甲醇期货现在多少钱", tools=TOOLS)
        capabilities.resolve(scenario, text="甲醇期货现在多少钱", tools=TOOLS)
        samples.append((time.perf_counter() - started) * 1000.0)
    p95 = sorted(samples)[949]
    assert p95 < 10.0

    planner = _planner()
    previews: list[float] = []
    for _ in range(100):
        started = time.perf_counter()
        planner.plan("查询 CAS 67-56-1").preview()
        previews.append((time.perf_counter() - started) * 1000.0)
    assert sorted(previews)[94] < 50.0
