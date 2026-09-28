"""MCPManager — our own thin async MCP client over the official `mcp` SDK.

Async-native (no `nest_asyncio`, no second event loop): each server runs in a dedicated
asyncio task that opens the transport + `ClientSession`, keeps them alive until shutdown,
then closes them in the *same* task — required because the SDK's transports use anyio cancel
scopes that must be entered and exited on one task. Tool calls are awaited from any task on
the same loop, which is safe.

Tool execution from the (sync) ToolRegistry bridges back here via
`run_coroutine_threadsafe` — see `coworker/mcp/tools.py`.
"""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from .config import MCPServerDef

MCP_CONNECT_TIMEOUT_SECONDS = 15.0


class _Conn:
    def __init__(self, session: ClientSession, tools: list[Any]) -> None:
        self.session = session
        self.tools = tools  # list[mcp.types.Tool]
        self.shutdown = asyncio.Event()


class MCPManager:
    """Owns persistent MCP connections keyed by server name; lazy-connects on demand."""

    def __init__(self, secrets: Any = None) -> None:
        self._conns: dict[str, _Conn] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._connecting: dict[str, asyncio.Future] = {}
        self._transport_keys: dict[str, tuple] = {}
        # SecretStore for OAuth servers' token persistence (mcp/oauth.py); lazy default
        # so library/CLI construction without secrets keeps working.
        self._secrets = secrets

    async def ensure(self, server: MCPServerDef, *, interactive: bool = False) -> _Conn:
        """Return a live connection for `server`, connecting (once) if needed.

        `interactive=True` (explicit connect actions only) lets an OAuth server run
        the browser sign-in flow; the default refuses it — stored tokens and silent
        refresh still work, but a server that insists on re-authorization raises
        InteractiveAuthRequired instead of hijacking the user's browser.
        """
        transport_key = (
            server.transport, server.command, tuple(server.args), server.cwd,
            tuple(sorted(server.env.items())), server.url,
            tuple(sorted(server.headers.items())), server.auth,
        )
        if server.name in self._transport_keys and self._transport_keys[server.name] != transport_key:
            raise ConnectionError(f"MCP {server.name} 连接配置已变化，请在连接页面重新加载")
        existing = self._conns.get(server.name)
        if existing is not None:
            return existing
        # Creation is atomic on this loop; never hold a cross-server lock over I/O.
        ready = self._connecting.get(server.name)
        if ready is None:
            loop = asyncio.get_running_loop()
            ready = loop.create_future()
            self._connecting[server.name] = ready
            self._transport_keys[server.name] = transport_key
            task = self._tasks[server.name] = asyncio.create_task(
                self._serve(server, ready, interactive=interactive)
            )
            def ended(owner: asyncio.Task) -> None:
                # A task cancelled before its first instruction never enters
                # _serve's finally block, but its waiters still need an outcome.
                if not ready.done():
                    ready.set_exception(ConnectionError(f"MCP {server.name} 连接在就绪前结束"))
                if self._tasks.get(server.name) is owner:
                    self._conns.pop(server.name, None)
                    self._tasks.pop(server.name, None)
                    self._connecting.pop(server.name, None)
                    self._transport_keys.pop(server.name, None)
                if not owner.cancelled():
                    owner.exception()

            task.add_done_callback(ended)
            # A watchdog settles waiters even if transport cleanup itself stalls.
            # Interactive OAuth retains its own browser-flow deadline.
            def expire() -> None:
                if not ready.done():
                    ready.set_exception(TimeoutError(
                        f"MCP {server.name} 连接初始化超过 {MCP_CONNECT_TIMEOUT_SECONDS:g} 秒"
                    ))
                    task.cancel()

            timer = None if interactive else loop.call_later(MCP_CONNECT_TIMEOUT_SECONDS, expire)

            def settled(future: asyncio.Future) -> None:
                if timer is not None:
                    timer.cancel()
                if not future.cancelled():
                    future.exception()  # consume failures even if every view has left

            ready.add_done_callback(settled)
        # Leaving one view must not cancel the shared connection or its other waiters.
        return await asyncio.shield(ready)

    async def tools(self, server: MCPServerDef) -> list[Any]:
        return (await self.ensure(server)).tools

    async def call(
        self, name: str, tool: str, arguments: Optional[dict[str, Any]]
    ) -> Any:
        conn = self._conns.get(name)
        if conn is None:
            raise RuntimeError(f"MCP server not connected: {name}")
        result = await conn.session.call_tool(tool, arguments or {})
        return _result_payload(result)

    async def aclose(self) -> None:
        for ready in self._connecting.values():
            if not ready.done():
                ready.set_exception(ConnectionError("MCP 连接已关闭"))
        for conn in self._conns.values():
            conn.shutdown.set()
        for name, task in self._tasks.items():
            if name not in self._conns:
                task.cancel()
        for task in list(self._tasks.values()):
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=5)
            except asyncio.CancelledError:
                if not task.cancelled():
                    raise
            except Exception:
                task.cancel()
        self._conns.clear()
        self._tasks.clear()
        self._connecting.clear()
        self._transport_keys.clear()

    # -- per-server lifecycle (one task owns enter+exit) ------------------------
    async def _serve(
        self, server: MCPServerDef, ready: asyncio.Future, *, interactive: bool = False
    ) -> None:
        try:
            async with AsyncExitStack() as stack:
                if server.transport == "http":
                    if not server.url:
                        raise ValueError(
                            f"MCP server '{server.name}' is http but has no url"
                        )
                    auth = None
                    if server.auth == "oauth":
                        from ..secrets import SecretStore
                        from .oauth import build_auth

                        if self._secrets is None:
                            self._secrets = SecretStore()
                        auth = build_auth(
                            server.name,
                            server.url,
                            self._secrets,
                            interactive=interactive,
                        )
                    read, write, *_ = await stack.enter_async_context(
                        streamablehttp_client(
                            server.url, headers=server.headers or None, auth=auth
                        )
                    )
                else:
                    if not server.command:
                        raise ValueError(
                            f"MCP server '{server.name}' is stdio but has no command"
                        )
                    params = StdioServerParameters(
                        command=server.command,
                        args=server.args,
                        env=server.env or None,
                        cwd=server.cwd,
                    )
                    read, write = await stack.enter_async_context(stdio_client(params))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                listed = await session.list_tools()
                conn = _Conn(session, list(listed.tools))
                if not ready.done():
                    self._conns[server.name] = conn
                    ready.set_result(conn)
                else:
                    return  # a timeout/close won the race; never publish a late connection
                await conn.shutdown.wait()
        except Exception as exc:  # connection / init failure
            if not ready.done():
                ready.set_exception(exc)
        finally:
            if not ready.done():
                ready.set_exception(ConnectionError(f"MCP {server.name} 连接在就绪前结束"))
            if self._tasks.get(server.name) is asyncio.current_task():
                self._conns.pop(server.name, None)
                self._tasks.pop(server.name, None)
                self._connecting.pop(server.name, None)
                self._transport_keys.pop(server.name, None)


def _result_payload(result: Any) -> Any:
    """Flatten a CallToolResult into something the engine can serialize for the model."""
    texts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text is not None:
            texts.append(text)
        else:  # non-text content (image/resource) — describe it
            texts.append(f"[{getattr(block, 'type', 'content')}]")
    body = "\n".join(texts)
    if getattr(result, "isError", False):
        return {"error": body or "MCP tool error"}
    structured = getattr(result, "structuredContent", None)
    if structured is not None and not body:
        return structured
    return body
