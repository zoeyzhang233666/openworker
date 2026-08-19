"""MCP integration — our own async client on the official `mcp` SDK.

Public API: config loading/mutation, the connection manager, and tool wrapping.
"""

from __future__ import annotations

from .builtin import is_builtin_config, seed_builtin_mcp
from .client import MCPManager
from .config import (
    MCPServerDef,
    delete_global_server,
    load_mcp_servers,
    patch_global_server,
    put_global_server,
    read_global,
)
from .tools import build_callables, tool_name

__all__ = [
    "MCPManager",
    "MCPServerDef",
    "load_mcp_servers",
    "read_global",
    "put_global_server",
    "patch_global_server",
    "delete_global_server",
    "build_callables",
    "tool_name",
    "seed_builtin_mcp",
    "is_builtin_config",
]
