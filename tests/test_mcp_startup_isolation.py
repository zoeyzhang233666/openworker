"""MCP availability must never be a prerequisite for ordinary conversation."""
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from coworker.mcp import client as mcp_client
from coworker.mcp.config import MCPServerDef
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient
from coworker.server import SessionManager, create_app
from coworker.tool_discovery import ToolDiscovery


@pytest.fixture
def transports(monkeypatch):
    gates = {}
    started = []

    @asynccontextmanager
    async def stdio(params):
        yield params.command, params.command

    class Session:
        def __init__(self, read, write):
            self.name = read

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def initialize(self):
            started.append(self.name)
            if self.name in gates:
                await gates[self.name].wait()

        async def list_tools(self):
            return SimpleNamespace(tools=[])

    monkeypatch.setattr(mcp_client, "stdio_client", stdio)
    monkeypatch.setattr(mcp_client, "ClientSession", Session)
    return gates, started


def server(name):
    return MCPServerDef(name=name, transport="stdio", command=name)


@pytest.mark.asyncio
async def test_slow_server_does_not_block_other_servers(transports):
    gates, started = transports
    gates["slow"] = asyncio.Event()
    manager = mcp_client.MCPManager()
    pending = asyncio.create_task(manager.ensure(server("slow")))
    try:
        await asyncio.sleep(0)
        conn = await asyncio.wait_for(manager.ensure(server("fast")), .2)
        assert conn is not None
        assert set(started) == {"slow", "fast"}
    finally:
        gates["slow"].set()
        await pending
        await manager.aclose()


@pytest.mark.asyncio
async def test_cancelled_waiter_does_not_restart_shared_connection(transports):
    gates, started = transports
    gates["shared"] = asyncio.Event()
    manager = mcp_client.MCPManager()
    first = asyncio.create_task(manager.ensure(server("shared")))
    await asyncio.sleep(0)
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    second = asyncio.create_task(manager.ensure(server("shared")))
    await asyncio.sleep(0)
    gates["shared"].set()
    try:
        assert await asyncio.wait_for(second, .2) is not None
        assert started == ["shared"]
    finally:
        await manager.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("before_start", [False, True])
async def test_cancelled_connection_owner_finishes_waiters(transports, before_start):
    gates, _ = transports
    gates["slow"] = asyncio.Event()
    manager = mcp_client.MCPManager()
    waiter = asyncio.create_task(manager.ensure(server("slow")))
    await asyncio.sleep(0)
    if not before_start:
        await asyncio.sleep(0)
    manager._tasks["slow"].cancel()
    try:
        with pytest.raises(ConnectionError):
            await asyncio.wait_for(waiter, .2)
    finally:
        await manager.aclose()


@pytest.mark.asyncio
async def test_connection_timeout_settles_and_can_retry(transports, monkeypatch):
    gates, _ = transports
    gates["slow"] = asyncio.Event()
    monkeypatch.setattr(mcp_client, "MCP_CONNECT_TIMEOUT_SECONDS", .02, raising=False)
    manager = mcp_client.MCPManager()
    try:
        with pytest.raises(TimeoutError, match="MCP"):
            await asyncio.wait_for(manager.ensure(server("slow")), .2)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        gates["slow"].set()
        assert await asyncio.wait_for(manager.ensure(server("slow")), .2)
    finally:
        gates["slow"].set()
        await manager.aclose()


def configured_manager(tmp_path, monkeypatch):
    monkeypatch.setattr("coworker.server.manager.load_mcp_servers", lambda *a, **k: [server("slow")])
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "state")
    monkeypatch.setattr(manager, "start_autotitle", lambda *a, **k: None, raising=False)
    return manager


@pytest.mark.asyncio
async def test_prepare_returns_then_late_tools_attach(tmp_path, monkeypatch):
    manager = configured_manager(tmp_path, monkeypatch)
    gate = asyncio.Event()

    async def ensure(*a, **k):
        await gate.wait()
        return SimpleNamespace(tools=[SimpleNamespace(name="lookup", description="read", inputSchema={"type": "object", "properties": {}})])

    monkeypatch.setattr(manager.mcp, "ensure", ensure)
    try:
        assert await asyncio.wait_for(manager.prepare_mcp_tools("s"), .6) == []
        engine = manager.get_engine("s")
        gate.set()
        await asyncio.sleep(.02)
        assert "mcp__slow__lookup" in engine.registry.names()
        discovery = ToolDiscovery(engine.registry, lambda: None, lambda: 12000)
        assert discovery.search("mcp__slow__lookup")["total"] == 1
    finally:
        gate.set()
        await manager.aclose()


@pytest.mark.asyncio
async def test_disabled_while_connecting_never_attaches(tmp_path, monkeypatch):
    manager = configured_manager(tmp_path, monkeypatch)
    gate = asyncio.Event()

    async def ensure(*a, **k):
        await gate.wait()
        return SimpleNamespace(tools=[SimpleNamespace(name="lookup", description="read", inputSchema={"type": "object", "properties": {}})])

    monkeypatch.setattr(manager.mcp, "ensure", ensure)
    try:
        assert await asyncio.wait_for(manager.prepare_mcp_tools("s"), .6) == []
        engine = manager.get_engine("s")
        monkeypatch.setattr("coworker.server.manager.load_mcp_servers", lambda *a, **k: [])
        gate.set()
        await asyncio.sleep(.02)
        assert "mcp__slow__lookup" not in engine.registry.names()
    finally:
        gate.set()
        await manager.aclose()


class GreetingProvider(ProviderClient):
    def complete(self, **kwargs):
        return AssistantTurn(text="你好！", finish_reason="stop")

    def capabilities(self, model):
        return ModelCapabilities()


@pytest.mark.parametrize("agent", ["code", "cowork"])
def test_websocket_greeting_completes_while_mcp_still_connecting(tmp_path, monkeypatch, agent):
    manager = configured_manager(tmp_path, monkeypatch)
    manager.provider = GreetingProvider()
    blocked = True

    async def ensure(*a, **k):
        nonlocal blocked
        await asyncio.sleep(30)  # finite safety bound; normal completion cancels this
        blocked = False
        raise TimeoutError("simulated MCP connection timeout")

    monkeypatch.setattr(manager.mcp, "ensure", ensure)
    with TestClient(create_app(manager)) as client:
        with client.websocket_connect(f"/ws/session/hello?agent={agent}") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert blocked, "chat startup waited for the optional MCP server"
            ws.send_json({"type": "user_message", "text": "你好", "model": "deepseek-v4.1-flash"})
            events = []
            while True:
                event = ws.receive_json()
                events.append(event)
                if event["type"] == "turn_done":
                    break
            assert blocked
            assert any(e["type"] == "assistant_message" and e["data"]["text"] == "你好！" for e in events)
            assert manager.session_store.load("hello").model == "deepseek-v4.1-flash"


@pytest.mark.asyncio
async def test_channel_greeting_completes_while_mcp_is_pending(tmp_path, monkeypatch):
    manager = configured_manager(tmp_path, monkeypatch)
    manager.provider = GreetingProvider()

    async def ensure(*a, **k):
        await asyncio.Event().wait()

    monkeypatch.setattr(manager.mcp, "ensure", ensure)
    try:
        await asyncio.wait_for(manager.deliver_to_session("channel", "你好"), 10)
        assert any(m.get("content") == "你好！" for m in manager._engines["channel"].messages)
        assert manager._mcp_preparations
    finally:
        await manager.aclose()
    assert not manager._mcp_preparations


@pytest.mark.asyncio
async def test_connection_status_is_visible_without_waiting(tmp_path, monkeypatch, transports):
    from coworker.mcp.config import put_global_server

    gates, _ = transports
    gates["slow"] = asyncio.Event()
    manager = configured_manager(tmp_path, monkeypatch)
    put_global_server("slow", {"command": "slow", "enabled": True})
    try:
        await manager.prepare_mcp_tools("s")
        assert manager.list_mcp()[0]["status"] == "connecting"
        await manager.reload_mcp()
        assert not manager.mcp._tasks
        assert not manager._mcp_preparations
    finally:
        await manager.aclose()


def test_discovery_metadata_uses_snapshot_during_late_registration():
    from coworker.tools.registry import ToolRegistry

    registry = ToolRegistry()

    def first():
        return "first"

    def late():
        return "late"

    class Metadata:
        @property
        def capabilities(self):
            registry.register(late)
            return ()

    registry.register(first, metadata=Metadata())
    assert [d.name for d in registry.descriptors()] == ["first"]
    assert set(registry.names()) == {"first", "late"}


@pytest.mark.asyncio
async def test_reconfigured_server_cannot_reuse_old_pending_transport(transports):
    gates, _ = transports
    gates["slow"] = asyncio.Event()
    manager = mcp_client.MCPManager()
    pending = asyncio.create_task(manager.ensure(server("slow")))
    await asyncio.sleep(0)
    changed = MCPServerDef(name="slow", transport="stdio", command="new-endpoint")
    try:
        with pytest.raises(ConnectionError, match="配置已变化"):
            await manager.ensure(changed)
        gates["slow"].set()
        await pending
        with pytest.raises(ConnectionError, match="配置已变化"):
            await manager.ensure(changed)
        await manager.aclose()
        assert await manager.ensure(changed)
    finally:
        gates["slow"].set()
        await manager.aclose()
