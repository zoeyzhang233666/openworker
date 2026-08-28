"""Background delivery (channel / self-wake) must mount MCP like GUI WebSocket attach."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from coworker.mcp.config import put_global_server
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient
from coworker.server.manager import SessionManager


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class ScriptedProvider(ProviderClient):
    def complete(self, *, model, messages, tools=None, **settings):
        return AssistantTurn(text="ok", finish_reason="stop")

    def capabilities(self, model):
        return ModelCapabilities()


def _fake_tool(name):
    return SimpleNamespace(
        name=name,
        description=f"tool {name}",
        inputSchema={"type": "object", "properties": {}},
    )


def test_deliver_to_session_mounts_mcp_without_ws(tmp_path, monkeypatch):
    """Channel/WeCom turns call deliver_to_session, not the GUI WS prep path."""
    monkeypatch.setenv("COWORKER_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        "coworker.server.manager.retire_builtin_mcp", lambda *a, **k: []
    )
    put_global_server(
        "chem-data-hub",
        {
            "type": "http",
            "url": "https://example.test/mcp",
            "enabled": True,
        },
    )

    manager = SessionManager(
        data_dir=tmp_path / "data", provider=ScriptedProvider()
    )

    async def fake_ensure(server):
        return SimpleNamespace(tools=[_fake_tool("search_compound")])

    monkeypatch.setattr(manager.mcp, "ensure", fake_ensure)

    # Materialize a durable chat session the way channel routing would — no WS attach.
    engine = manager.get_engine("s-wecom", agent="chat")
    assert engine is not None
    assert not any(n.startswith("mcp__chem-data-hub__") for n in engine.registry.names())

    asyncio.run(manager.deliver_to_session("s-wecom", "ping"))

    names = engine.registry.names()
    assert "mcp__chem-data-hub__search_compound" in names


def test_deliver_to_session_mounts_mcp_on_first_turn(tmp_path, monkeypatch):
    """A session that only ever receives channel delivery still gets MCP tools."""
    monkeypatch.setenv("COWORKER_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        "coworker.server.manager.retire_builtin_mcp", lambda *a, **k: []
    )
    put_global_server(
        "chem-data-hub",
        {
            "type": "http",
            "url": "https://example.test/mcp",
            "enabled": True,
        },
    )

    manager = SessionManager(
        data_dir=tmp_path / "data", provider=ScriptedProvider()
    )

    async def fake_ensure(server):
        return SimpleNamespace(tools=[_fake_tool("get_price_trend")])

    monkeypatch.setattr(manager.mcp, "ensure", fake_ensure)

    asyncio.run(manager.deliver_to_session("s-new", "hello"))

    engine = manager._engines.get("s-new")
    assert engine is not None
    assert "mcp__chem-data-hub__get_price_trend" in engine.registry.names()
