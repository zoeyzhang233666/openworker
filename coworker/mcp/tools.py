"""Turn MCP tools into ToolRegistry-ready callables.

Each MCP tool becomes a sync callable (so it fits the registry's `execute` contract, which
the engine already runs via `asyncio.to_thread`). The callable bridges back to the live
async session on the server loop via `run_coroutine_threadsafe`. We attach `ToolMetadata`
(category="mcp", `requires_approval` per config) so the PermissionEngine gates it, and an
explicit OpenAI schema built straight from the MCP `inputSchema` for fidelity.
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Awaitable, Callable

import aisuite as ai

from .config import MCPServerDef

CallAsync = Callable[[str, dict[str, Any]], Awaitable[Any]]

_NAME_OK = re.compile(r"[^a-zA-Z0-9_-]")
_MAX_NAME = 64  # OpenAI function-name limit

# Read-only name tokens → risk_level=low so the engine can parallelize after approval.
# Write/mutate tokens win when both match (fail closed → medium).
_READ_TOKENS = (
    "search",
    "get_",
    "get-",
    "list_",
    "list-",
    "find_",
    "find-",
    "read_",
    "read-",
    "fetch",
    "query",
    "lookup",
    "explore",
    "describe",
    "show_",
    "show-",
    "price",
    "trend",
    "info",
    "stat",
)
_WRITE_TOKENS = (
    "write",
    "create",
    "update",
    "delete",
    "remove",
    "put_",
    "put-",
    "post_",
    "post-",
    "patch",
    "set_",
    "set-",
    "send",
    "exec",
    "run_",
    "run-",
    "mutate",
    "upload",
    "install",
)

# Default MCP bridge wait; slow tools (name match) keep the historic 120s ceiling.
_DEFAULT_TIMEOUT = 30.0
_SLOW_TIMEOUT = 120.0
_SLOW_TOKENS = ("batch", "export", "download", "crawl", "index", "embed", "sync")


def tool_name(server: str, tool: str) -> str:
    """`mcp__<server>__<tool>`, sanitized to OpenAI's `[A-Za-z0-9_-]{1,64}` rule."""
    base = f"mcp__{_NAME_OK.sub('_', server)}__{_NAME_OK.sub('_', tool)}"
    if len(base) > _MAX_NAME:
        base = base[:_MAX_NAME]
    return base


def is_readonly_mcp_tool(remote_name: str) -> bool:
    """Heuristic: likely side-effect-free MCP tools (search/get/explore/…)."""
    lowered = (remote_name or "").lower()
    if any(tok in lowered for tok in _WRITE_TOKENS):
        return False
    return any(tok in lowered for tok in _READ_TOKENS)


def _mcp_timeout(remote_name: str, *, default: float | None = None) -> float:
    """Per-call wait: env override, then slow-tool whitelist, else short default."""
    env = os.environ.get("CHEMCLAW_MCP_TOOL_TIMEOUT") or os.environ.get(
        "COWORKER_MCP_TOOL_TIMEOUT"
    )
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    if default is not None:
        return default
    lowered = (remote_name or "").lower()
    if any(tok in lowered for tok in _SLOW_TOKENS):
        return _SLOW_TIMEOUT
    return _DEFAULT_TIMEOUT


def _openai_schema(name: str, mcp_tool: Any) -> dict[str, Any]:
    params = getattr(mcp_tool, "inputSchema", None) or {
        "type": "object",
        "properties": {},
    }
    description = (getattr(mcp_tool, "description", None) or "")[:1024]
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": params},
    }


def _filtered(mcp_tools: list[Any], server: MCPServerDef) -> list[Any]:
    out = mcp_tools
    if server.include_tools is not None:
        allow = set(server.include_tools)
        out = [t for t in out if t.name in allow]
    if server.exclude_tools:
        block = set(server.exclude_tools)
        out = [t for t in out if t.name not in block]
    return out


def build_callables(
    server: MCPServerDef,
    mcp_tools: list[Any],
    call_async: CallAsync,
    loop: asyncio.AbstractEventLoop,
    *,
    timeout: float | None = None,
) -> list[Callable[..., Any]]:
    """Wrap a server's (filtered) MCP tools as registry-ready callables.

    Read-only tools (name heuristic) get ``risk_level=low`` so the engine can run them
    concurrently after the authorize pass. Approval still follows ``server.requires_approval``
    (and connector per-tool overrides) — we never skip the permission gate.
    """
    callables: list[Callable[..., Any]] = []
    for mcp_tool in _filtered(mcp_tools, server):
        name = tool_name(server.name, mcp_tool.name)
        remote = mcp_tool.name
        call_timeout = _mcp_timeout(remote, default=timeout)
        readonly = is_readonly_mcp_tool(remote)

        def _invoke(
            _remote: str = remote,
            _timeout: float = call_timeout,
            **kwargs: Any,
        ) -> Any:
            future = asyncio.run_coroutine_threadsafe(call_async(_remote, kwargs), loop)
            return future.result(_timeout)

        # We attach the schema + metadata explicitly (rather than via `ai.tool`, which would
        # try to derive a schema from this `**kwargs` wrapper): the registry reads both attrs.
        _invoke.__name__ = name
        _invoke.__doc__ = (
            getattr(mcp_tool, "description", None)
            or f"MCP tool {remote} from {server.name}"
        )
        _invoke.__aisuite_tool_metadata__ = ai.ToolMetadata(
            name=name,
            category="mcp",
            risk_level="low" if readonly else "medium",
            capabilities=[server.name],
            requires_approval=server.requires_approval,
        )
        _invoke.__coworker_schema__ = _openai_schema(name, mcp_tool)
        callables.append(_invoke)
    return callables
