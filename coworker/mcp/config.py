"""MCP server config — the standard `mcpServers` JSON, layered global + workspace.

Global:    ~/.config/coworker/mcp.json
Workspace: <workspace>/.coworker/mcp.json   (overrides global on name clash,
           but only after the user trusts that workspace — same gate as
           repository `allowed_commands`)

Paste-compatible with Claude Desktop / Cursor / Codex. `${VAR}` refs in command/args/env/
url/headers are resolved at load time via the SecretStore (env + local `.env`). REST edits
target the **global** file.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..secrets import SecretStore, state_dir

_HTTP_TYPES = {"http", "https", "sse", "streamable-http", "streamable_http"}
# Unresolved ${VAR} left intact by SecretStore.resolve — must not be sent as auth.
_UNRESOLVED_REF = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}")


@dataclass
class MCPServerDef:
    name: str
    transport: str  # "stdio" | "http"
    command: Optional[str] = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    url: Optional[str] = None
    headers: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    include_tools: Optional[list[str]] = None
    exclude_tools: Optional[list[str]] = None
    requires_approval: bool = True
    # "oauth" → browser OAuth 2.1 + PKCE with Dynamic Client Registration (mcp/oauth.py).
    # HTTP transport only; tokens live in the SecretStore, never in this file.
    auth: Optional[str] = None


def global_mcp_path() -> Path:
    return state_dir() / "mcp.json"


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _config_paths(
    workspace: Optional[str | Path], *, workspace_trusted: bool
) -> list[Path]:
    """Config files to merge. Workspace MCP is executable provenance (stdio spawn),
    so an untrusted repo's `.coworker/mcp.json` is never read — cloning alone must
    not be enough to define processes that run at session open.
    """
    paths = [global_mcp_path()]
    if workspace and workspace_trusted:
        paths.append(Path(workspace).expanduser() / ".coworker" / "mcp.json")
    return paths


def has_unresolved_refs(value: Any) -> bool:
    """True if ``value`` still contains a literal ``${VAR}`` after resolve."""
    if isinstance(value, str):
        return bool(_UNRESOLVED_REF.search(value))
    if isinstance(value, dict):
        return any(has_unresolved_refs(v) for v in value.values())
    if isinstance(value, list):
        return any(has_unresolved_refs(v) for v in value)
    return False


def unresolved_ref_fields(server: MCPServerDef) -> list[str]:
    """Human-readable field names that still contain unresolved ``${VAR}``."""
    bad: list[str] = []
    if server.url and has_unresolved_refs(server.url):
        bad.append("url")
    for key, val in (server.headers or {}).items():
        if has_unresolved_refs(val):
            bad.append(f"headers.{key}")
    for key, val in (server.env or {}).items():
        if has_unresolved_refs(val):
            bad.append(f"env.{key}")
    if server.command and has_unresolved_refs(server.command):
        bad.append("command")
    for i, arg in enumerate(server.args or []):
        if has_unresolved_refs(arg):
            bad.append(f"args[{i}]")
    return bad


def assert_mcp_secrets_resolved(server: MCPServerDef) -> None:
    """Raise before connect when Authorization/url/env still contain ``${VAR}``."""
    bad = unresolved_ref_fields(server)
    if not bad:
        return
    raise RuntimeError(
        f"MCP server '{server.name}' has unresolved ${{VAR}} in {', '.join(bad)} "
        f"— check state-dir .env or environment"
    )


def _parse(name: str, raw: dict[str, Any], secrets: SecretStore) -> MCPServerDef:
    raw = secrets.resolve(raw)  # resolve ${VAR} everywhere before building the def
    declared = str(raw.get("type", "")).lower()
    is_http = declared in _HTTP_TYPES or bool(raw.get("url"))
    return MCPServerDef(
        name=name,
        transport="http" if is_http else "stdio",
        command=raw.get("command"),
        args=list(raw.get("args", []) or []),
        env={str(k): str(v) for k, v in (raw.get("env") or {}).items()},
        cwd=raw.get("cwd"),
        url=raw.get("url"),
        headers={str(k): str(v) for k, v in (raw.get("headers") or {}).items()},
        enabled=bool(raw.get("enabled", True)),
        include_tools=raw.get("include_tools"),
        exclude_tools=raw.get("exclude_tools"),
        requires_approval=bool(raw.get("requires_approval", True)),
        auth=(str(raw["auth"]).lower() if raw.get("auth") else None),
    )


def load_mcp_servers(
    workspace: Optional[str | Path] = None,
    *,
    secrets: Optional[SecretStore] = None,
    workspace_trusted: bool = False,
) -> list[MCPServerDef]:
    """Merge global + (when trusted) workspace `mcpServers` into parsed server defs.

    Only trusted workspaces contribute — the same consent boundary as repository
    ``allowed_commands`` — and **global wins on name clash**, so even a trusted repo
    cannot silently redefine a global server by reusing its name. ``${VAR}`` refs in
    a workspace def are resolved from the user's env, which is acceptable only because
    the workspace is trusted; untrusted workspaces are never read.
    """
    secrets = secrets or SecretStore()
    merged: dict[str, dict[str, Any]] = {}
    for path in _config_paths(workspace, workspace_trusted=workspace_trusted):
        for name, raw in (_read(path).get("mcpServers") or {}).items():
            if isinstance(raw, dict):
                merged.setdefault(name, raw)  # global first → global wins on clash
    return [_parse(name, raw, secrets) for name, raw in merged.items()]


# -- raw global-file mutation (REST) -------------------------------------------
def read_global() -> dict[str, dict[str, Any]]:
    """Raw `mcpServers` map from the global file (no `${VAR}` resolution)."""
    return dict(_read(global_mcp_path()).get("mcpServers") or {})


def _write_global(servers: dict[str, dict[str, Any]]) -> None:
    path = global_mcp_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"mcpServers": servers}, indent=2), encoding="utf-8")
    tmp.replace(path)


def put_global_server(name: str, config: dict[str, Any]) -> None:
    servers = read_global()
    servers[name] = config
    _write_global(servers)


def patch_global_server(name: str, changes: dict[str, Any]) -> bool:
    servers = read_global()
    if name not in servers:
        return False
    servers[name] = {**servers[name], **changes}
    _write_global(servers)
    return True


def delete_global_server(name: str) -> bool:
    servers = read_global()
    if name not in servers:
        return False
    del servers[name]
    _write_global(servers)
    return True
