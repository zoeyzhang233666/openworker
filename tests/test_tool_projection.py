"""HARD STOP E — tool_projection_enabled + provider-visible schema projection."""

from __future__ import annotations

from coworker.execution_profile import RequestRoute, make_execution_profile
from coworker.config import Config
from coworker.tool_policy import TurnToolPolicy
from coworker.tool_projection import (
    project_provider_visible_schemas,
    select_verified_tool_names,
)
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


def test_tool_projection_disabled_restores_legacy_full_schema():
    cfg = Config(tool_projection_enabled=False)
    assert cfg.tool_projection_enabled is False
    registry = _reg("read_file", "web_search", "ask_user", "totally_custom_extra_tool_xyz")
    profile = make_execution_profile(RequestRoute.FAST_CHAT, cfg)
    # Even with FAST_CHAT (tools_enabled=False), kill switch OFF → full legacy exposure.
    out = project_provider_visible_schemas(
        registry,
        tool_projection_enabled=False,
        profile=profile,
        tool_policy=TurnToolPolicy(),
    )
    assert out is not None
    names = {s["function"]["name"] for s in out}
    assert names == {
        "read_file",
        "web_search",
        "ask_user",
        "totally_custom_extra_tool_xyz",
    }


def test_pure_fast_chat_projection_yields_tools_none():
    cfg = Config(tool_projection_enabled=True)
    registry = _reg("read_file", "web_search", "ask_user")
    profile = make_execution_profile(RequestRoute.FAST_CHAT, cfg)
    out = project_provider_visible_schemas(
        registry,
        tool_projection_enabled=True,
        profile=profile,
        tool_policy=TurnToolPolicy(),
    )
    assert out is None


def test_pure_knowledge_projection_yields_tools_none():
    cfg = Config(tool_projection_enabled=True)
    registry = _reg("read_file", "web_search")
    profile = make_execution_profile(RequestRoute.KNOWLEDGE, cfg)
    out = project_provider_visible_schemas(
        registry,
        tool_projection_enabled=True,
        profile=profile,
        tool_policy=TurnToolPolicy(),
    )
    assert out is None


def test_verified_cas_targets_chemical_identity_only():
    available = {
        "lookup_chemical_identity",
        "web_search",
        "read_file",
        "ask_user",
        "search_tenders",
    }
    selected = select_verified_tool_names("苯的 CAS 是多少？", available)
    assert selected == ("lookup_chemical_identity",)


_CN_STOCK = (
    "lookup_cn_stock_quote",
    "lookup_cn_stock_ohlc",
    "lookup_cn_stock_minute",
    "lookup_cn_stock_financials",
    "lookup_cn_stock_feature",
)
_CN_FUTURES = (
    "lookup_cn_futures_quote",
    "lookup_cn_futures_ohlc",
    "lookup_cn_futures_minute",
    "lookup_cn_futures_l1",
    "calculate_cn_futures_margin",
)
_MARKET = {
    "lookup_yahoo_ohlc",
    "lookup_cn_option_market",
    "web_search",
    "web_fetch",
    "read_file",
    "ask_user",
    *_CN_STOCK,
    *_CN_FUTURES,
}


def test_verified_a_share_projects_cn_stock_not_yahoo():
    selected = select_verified_tool_names("分析今天 A 股市场", _MARKET)
    assert selected is not None
    assert "lookup_cn_stock_ohlc" in selected
    assert "lookup_cn_stock_quote" in selected
    assert "lookup_yahoo_ohlc" not in selected
    assert "web_search" not in selected


def test_verified_cn_futures_projects_cn_not_yahoo():
    selected = select_verified_tool_names("液化气最近一年走势", _MARKET)
    assert selected is not None
    assert "lookup_cn_futures_ohlc" in selected
    assert "lookup_yahoo_ohlc" not in selected
    assert "web_search" not in selected


def test_verified_cn_options_project_option_tool():
    selected = select_verified_tool_names("50ETF期权合约列表", _MARKET)
    assert selected is not None
    assert "lookup_cn_option_market" in selected
    assert "lookup_yahoo_ohlc" not in selected


def test_verified_global_futures_still_use_yahoo():
    selected = select_verified_tool_names("CL=F 最近一年走势", _MARKET)
    assert selected is not None
    assert "lookup_yahoo_ohlc" in selected
    assert "lookup_cn_futures_ohlc" not in selected


def test_verified_projection_filters_to_allowed_subset():
    cfg = Config(tool_projection_enabled=True)
    registry = _reg(
        "lookup_chemical_identity",
        "web_search",
        "read_file",
        "search_tenders",
    )
    profile = make_execution_profile(
        RequestRoute.VERIFIED,
        cfg,
        allowed_tool_names=("lookup_chemical_identity",),
    )
    out = project_provider_visible_schemas(
        registry,
        tool_projection_enabled=True,
        profile=profile,
        tool_policy=TurnToolPolicy(),
    )
    assert out is not None
    names = {s["function"]["name"] for s in out}
    assert names == {"lookup_chemical_identity"}


def test_agent_projection_keeps_legacy_when_allowed_is_none():
    cfg = Config(tool_projection_enabled=True)
    registry = _reg(
        "read_file",
        "remember",
        "load_skill",
        "ask_user",
        "web_search",
        "totally_custom_extra_tool_xyz",
        "mcp_foo_bar",
    )
    profile = make_execution_profile(RequestRoute.AGENT, cfg)
    assert profile.allowed_tool_names is None
    out = project_provider_visible_schemas(
        registry,
        tool_projection_enabled=True,
        profile=profile,
        tool_policy=TurnToolPolicy(),
    )
    assert out is not None
    names = {s["function"]["name"] for s in out}
    assert names == set(registry.names())


def test_no_external_network_final_filter_drops_remote_and_unknown_keeps_local():
    cfg = Config(tool_projection_enabled=True)
    registry = _reg(
        "read_file",
        "remember",
        "ask_user",
        "web_search",
        "lookup_chemical_identity",
        "totally_custom_extra_tool_xyz",
    )
    profile = make_execution_profile(RequestRoute.AGENT, cfg)
    out = project_provider_visible_schemas(
        registry,
        tool_projection_enabled=True,
        profile=profile,
        tool_policy=TurnToolPolicy(no_external_network=True),
    )
    assert out is not None
    names = {s["function"]["name"] for s in out}
    assert "read_file" in names
    assert "remember" in names
    assert "ask_user" in names
    assert "web_search" not in names
    assert "lookup_chemical_identity" not in names
    assert "totally_custom_extra_tool_xyz" not in names


def test_agent_keeps_unknown_custom_when_no_network_ban():
    cfg = Config(tool_projection_enabled=True)
    registry = _reg("read_file", "totally_custom_extra_tool_xyz")
    profile = make_execution_profile(RequestRoute.AGENT, cfg)
    out = project_provider_visible_schemas(
        registry,
        tool_projection_enabled=True,
        profile=profile,
        tool_policy=TurnToolPolicy(),
    )
    names = {s["function"]["name"] for s in out}
    assert "totally_custom_extra_tool_xyz" in names


def test_projection_does_not_mutate_registry():
    cfg = Config(tool_projection_enabled=True)
    registry = _reg("read_file", "web_search", "ask_user")
    before = sorted(registry.names())
    profile = make_execution_profile(RequestRoute.FAST_CHAT, cfg)
    project_provider_visible_schemas(
        registry,
        tool_projection_enabled=True,
        profile=profile,
        tool_policy=TurnToolPolicy(),
    )
    assert sorted(registry.names()) == before
    # Execution path still finds tools even when schemas were None.
    assert registry.get("web_search") is not None


def test_routing_and_projection_kill_switches_are_independent():
    """request_routing_enabled OFF must not imply projection OFF, and vice versa."""
    cfg = Config(
        request_routing_enabled=False,
        tool_projection_enabled=True,
    )
    assert cfg.request_routing_enabled is False
    assert cfg.tool_projection_enabled is True
    cfg2 = Config(
        request_routing_enabled=True,
        tool_projection_enabled=False,
    )
    assert cfg2.request_routing_enabled is True
    assert cfg2.tool_projection_enabled is False
