"""MCP integration — our own async client on the official `mcp` SDK.

Public API: config loading/mutation, the connection manager, and tool wrapping.
"""

from __future__ import annotations

from .builtin import is_builtin_config, retire_builtin_mcp, seed_builtin_mcp
from .client import MCPManager
from .config import (
    MCPServerDef,
    assert_mcp_secrets_resolved,
    delete_global_server,
    has_unresolved_refs,
    load_mcp_servers,
    patch_global_server,
    put_global_server,
    read_global,
)
from .errors import format_mcp_connect_error
from .tools import build_callables, tool_name

__all__ = [
    "MCPManager",
    "MCPServerDef",
    "assert_mcp_secrets_resolved",
    "format_mcp_connect_error",
    "has_unresolved_refs",
    "load_mcp_servers",
    "read_global",
    "put_global_server",
    "patch_global_server",
    "delete_global_server",
    "build_callables",
    "tool_name",
    "seed_builtin_mcp",
    "retire_builtin_mcp",
    "is_builtin_config",
]
