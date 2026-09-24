from coworker.tools.registry import ToolRegistry
from coworker.tool_discovery import ToolDiscovery
from coworker.tool_policy import TurnToolPolicy
from coworker.context_budget import estimate


def registry(count=400):
    r = ToolRegistry()
    for i in range(count):
        def tool():
            return "ok"
        tool.__name__ = f"mcp_rare_{i:03}"
        r.register(tool, schema={"type": "function", "function": {
            "name": tool.__name__, "description": f"specialty_{i} " + "description " * 100,
            "parameters": {"type": "object", "properties": {}}}})
    return r


def test_cold_discovery_pagination_and_schema_budget():
    r = registry()
    d = ToolDiscovery(r, lambda: TurnToolPolicy(), lambda: 2000)
    assert len(d.schemas()) == 2
    assert d.search("specialty_399")["tools"][0]["name"] == "mcp_rare_399"
    names, offset = set(), 0
    while offset is not None:
        page = d.search(offset=offset)
        names.update(row["name"] for row in page["tools"])
        offset = page["next_offset"]
    assert set(r.names()) == names
    assert d.load(["mcp_rare_399"])["loaded"] == ["mcp_rare_399"]
    assert "mcp_rare_399" in {s["function"]["name"] for s in d.schemas()}
    d.load(r.names())
    assert estimate(d.schemas()) <= 2000


def test_live_registration_removal_and_user_policy():
    r = registry()
    policy = TurnToolPolicy()
    d = ToolDiscovery(r, lambda: policy, lambda: 2000)
    d.schemas()
    d.load(["mcp_rare_399"])
    r.retain({"mcp_rare_000", "search_tools", "load_tools"})
    assert not d.search("399")["tools"]
    assert "mcp_rare_399" not in {s["function"]["name"] for s in d.schemas()}
    policy = TurnToolPolicy(no_external_network=True)
    assert not d.search("mcp")["tools"]
    assert d.search("search_tools")["tools"]
    policy = TurnToolPolicy(no_tools=True)
    assert d.schemas() == []
