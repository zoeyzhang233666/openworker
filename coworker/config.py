"""Configuration — layered TOML: built-in defaults < global < per-workspace.

Global:    <state-dir>/config.toml   (see `secrets.state_dir`; platform-native)
Workspace: <workspace>/.coworker/config.toml   (overrides global)

Workspace command allowances apply only after the user trusts that exact canonical
workspace path. Other permission grants remain global-only.
"""

from __future__ import annotations

try:
    import tomllib  # stdlib since 3.11
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .secrets import state_dir

# Commands auto-run WITHOUT an approval prompt. There is no generally safe executable:
# nominally read-only programs can read secrets outside the workspace, expand environment
# variables, load project-controlled config/plugins, or execute helpers (for example
# `find -exec` and pytest collection). Keep the built-in list empty. A user may explicitly
# opt into command prefixes in their user-owned global config, accepting that authority.
DEFAULT_ALLOWED_COMMANDS: list[str] = []


@dataclass
class Config:
    model: str = "apihub-cn:deepseek-v4-flash"
    mode: str = "interactive"
    max_iterations: int = 150  # legacy hard ceiling (not a soft target)
    # Soft targets / route budgets — only applied when an explicit ExecutionProfile
    # is attached (future Router or tests). Legacy sessions ignore these fields.
    agent_target_iterations: int = 32
    deep_research_target_iterations: int = 50
    verified_max_iterations: int = 6
    # Risky kill switches. Section 65 Step 56–59: request_routing + tool_projection
    # + structured-tools true streaming (known-safe only) + Emergency Finalization
    # all candidate ON (post-regression independent rollouts).
    request_routing_enabled: bool = True
    tool_projection_enabled: bool = True
    # D-169: declarative Scenario/Capability resolution. Independent kill switch;
    # False restores the D-165/D-166 planner and Tool Projection behavior.
    scenario_resolution_enabled: bool = True
    # D-165: outbound-only prompt/skill projection for new policy-v1 sessions.
    # Existing sessions without the policy marker keep their original system prompt.
    prompt_projection_enabled: bool = True
    # Step 58: ON + known-safe provider/model → tools-enabled true streaming;
    # unknown/custom compat endpoints stay compat-buffered + salvage-safe.
    structured_tools_true_streaming_enabled: bool = True
    # Step 59: hard-ceiling best-effort model-only finalization (guards still apply;
    # FAST/KNOWLEDGE profiles force OFF; kill switch False restores legacy hard-limit).
    emergency_finalization_enabled: bool = True
    allowed_commands: list[str] = field(
        default_factory=lambda: list(DEFAULT_ALLOWED_COMMANDS)
    )
    # In "custom" permission mode, these tools are auto-approved (e.g. file edits)
    # while everything else still asks.
    auto_allow: list[str] = field(default_factory=list)
    host: str = "127.0.0.1"
    port: int = 8765
    # Web search provider: "duckduckgo" (keyless default) | "tavily" | "brave" (need a key).
    web_search_provider: str = "duckduckgo"
    # OpenWorker Cloud (sign-in + managed connectors). Config, never constants:
    # dev/staging/BYO-VPC deployments point these at their own instances.
    cloud_base_url: str = "https://api.openworker.com"
    # Auth0 tenant + API audience are registered identifiers, not branding: the
    # tenant name can never be renamed, and the audience must match the API
    # identifier registered in Auth0 — both keep the legacy value on purpose.
    cloud_auth_domain: str = "opencoworker.us.auth0.com"
    cloud_client_id: str = "g1l4Q1lhYWmyS03qPSf4KEJGrgq02Qam"
    cloud_audience: str = "https://api.opencoworker.app"
    # Managed relay WebSocket endpoint (Slack/GitHub inbound). Defaults to the
    # PRODUCTION relay so a fresh install relays out of the box — an empty
    # default shipped once as "connected but relay OFF" on every machine
    # without a hand-edited config.toml. Empty override ⇒ relay disabled
    # (manual Socket Mode still works); dev/BYO deployments point elsewhere.
    cloud_relay_ws_url: str = (
        "wss://l4z1paxb83.execute-api.us-east-1.amazonaws.com/ocw-connect"
    )


_FIELDS = {
    "model",
    "mode",
    "max_iterations",
    "agent_target_iterations",
    "deep_research_target_iterations",
    "verified_max_iterations",
    "request_routing_enabled",
    "tool_projection_enabled",
    "scenario_resolution_enabled",
    "prompt_projection_enabled",
    "structured_tools_true_streaming_enabled",
    "emergency_finalization_enabled",
    "allowed_commands",
    "auto_allow",
    "host",
    "port",
    "web_search_provider",
    "cloud_base_url",
    "cloud_auth_domain",
    "cloud_client_id",
    "cloud_audience",
    "cloud_relay_ws_url",
}

# These fields change what consequential actions can run without a prompt, so the normal
# workspace override pass never applies them. `allowed_commands` is added separately only
# for a canonically trusted workspace; `auto_allow` remains user-global only.
_GLOBAL_ONLY_FIELDS = {"allowed_commands", "auto_allow"}
_WORKSPACE_FIELDS = _FIELDS - _GLOBAL_ONLY_FIELDS


def global_config_path() -> Path:
    return state_dir() / "config.toml"


def _read(path: Path) -> dict[str, Any]:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def workspace_allowed_commands(workspace: str | Path) -> list[str]:
    """Command prefixes requested by repository config; advisory until workspace trust."""
    path = Path(workspace).expanduser() / ".coworker" / "config.toml"
    value = _read(path).get("allowed_commands", [])
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(v.strip() for v in value if isinstance(v, str) and v.strip()))


def load_config(
    workspace: Optional[str | Path] = None,
    *,
    global_path: Optional[Path] = None,
    workspace_trusted: bool = False,
) -> Config:
    cfg = Config()

    g = Path(global_path) if global_path is not None else global_config_path()
    if g.is_file():
        for key, value in _read(g).items():
            if key in _FIELDS:
                setattr(cfg, key, value)
    if workspace:
        w = Path(workspace).expanduser() / ".coworker" / "config.toml"
        if w.is_file():
            for key, value in _read(w).items():
                if key in _WORKSPACE_FIELDS:
                    setattr(cfg, key, value)
            if workspace_trusted:
                cfg.allowed_commands = list(
                    dict.fromkeys(
                        [*cfg.allowed_commands, *workspace_allowed_commands(workspace)]
                    )
                )
    return cfg
