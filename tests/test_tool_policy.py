"""HARD STOP D — tool network_scope / usage_class helper (no engine projection)."""

from __future__ import annotations

from coworker.tool_policy import (
    NetworkScope,
    TurnToolPolicy,
    UsageClass,
    classify_tool,
    filter_tool_names,
    tool_allowed_under_policy,
)


def test_local_file_memory_plan_are_local():
    assert classify_tool("read_file") == (NetworkScope.LOCAL, UsageClass.FILE)
    assert classify_tool("write_file") == (NetworkScope.LOCAL, UsageClass.FILE)
    assert classify_tool("remember") == (NetworkScope.LOCAL, UsageClass.MEMORY)
    assert classify_tool("memory_update") == (NetworkScope.LOCAL, UsageClass.MEMORY)
    assert classify_tool("ask_user") == (
        NetworkScope.LOCAL,
        UsageClass.PRODUCT_CONTROL,
    )
    assert classify_tool("propose_plan") == (
        NetworkScope.LOCAL,
        UsageClass.PRODUCT_CONTROL,
    )
    assert classify_tool("load_skill") == (NetworkScope.LOCAL, UsageClass.SKILL)
    assert classify_tool("grep") == (NetworkScope.LOCAL, UsageClass.SEARCH)


def test_web_and_remote_providers_are_remote():
    assert classify_tool("web_search") == (NetworkScope.REMOTE, UsageClass.SEARCH)
    assert classify_tool("web_fetch") == (NetworkScope.REMOTE, UsageClass.OTHER)
    assert classify_tool("lookup_chemical_identity") == (
        NetworkScope.REMOTE,
        UsageClass.OTHER,
    )
    assert classify_tool("lookup_fx_rate")[0] is NetworkScope.REMOTE
    assert classify_tool("lookup_cn_stock_ohlc") == (
        NetworkScope.REMOTE,
        UsageClass.OTHER,
    )
    assert classify_tool("lookup_cn_futures_l1")[0] is NetworkScope.REMOTE
    assert classify_tool("lookup_cn_option_market")[0] is NetworkScope.REMOTE
    assert classify_tool("hubspot_create_task")[0] is NetworkScope.REMOTE
    assert classify_tool("mcp_custom_server_tool")[0] is NetworkScope.REMOTE


def test_unknown_custom_extra_tool_is_unknown():
    scope, usage = classify_tool("totally_custom_extra_tool_xyz")
    assert scope is NetworkScope.UNKNOWN
    assert usage is UsageClass.OTHER


def test_no_external_network_drops_remote_and_unknown_keeps_local():
    policy = TurnToolPolicy(no_external_network=True)
    names = [
        "read_file",
        "remember",
        "web_search",
        "lookup_chemical_identity",
        "totally_custom_extra_tool_xyz",
        "ask_user",
    ]
    kept = filter_tool_names(names, policy)
    assert "read_file" in kept
    assert "remember" in kept
    assert "ask_user" in kept
    assert "web_search" not in kept
    assert "lookup_chemical_identity" not in kept
    assert "totally_custom_extra_tool_xyz" not in kept


def test_normal_agent_keeps_unknown_custom_tool():
    policy = TurnToolPolicy()
    assert tool_allowed_under_policy("totally_custom_extra_tool_xyz", policy) is True


def test_no_search_keeps_local_file_and_memory():
    policy = TurnToolPolicy(no_search=True)
    names = ["read_file", "remember", "web_search", "grep", "ask_user"]
    kept = filter_tool_names(names, policy)
    assert "read_file" in kept
    assert "remember" in kept
    assert "ask_user" in kept
    assert "web_search" not in kept
    assert "grep" not in kept


def test_no_tools_removes_everything():
    policy = TurnToolPolicy(no_tools=True)
    assert filter_tool_names(["read_file", "ask_user", "web_search"], policy) == []
