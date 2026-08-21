"""Immutable Capability and provider binding contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CapabilityProvider(_FrozenModel):
    version: Literal[1] = 1
    provider_id: str
    binding_kind: Literal["tool", "mcp_metadata"]
    selector: str
    priority: int = 0
    authority: str = "public"
    freshness: str = "unspecified"
    latency_class: str = "normal"
    cost_class: str = "free"
    batchable: bool = False
    parallel_safe: bool = False
    network_scope: str = "none"
    risk: str = "low"
    fallback_for: tuple[str, ...] = ()


class CapabilitySpec(_FrozenModel):
    version: Literal[1] = 1
    id: str
    description: str
    providers: tuple[CapabilityProvider, ...]


class CapabilityResolution(_FrozenModel):
    version: Literal[1] = 1
    capability_id: str
    required: bool
    status: Literal["ready", "configured", "unavailable"]
    provider_id: str | None = None
    tool_names: tuple[str, ...] = ()
    fallback_used: bool = False
    reason: str = ""


class CapabilityPlan(_FrozenModel):
    version: Literal[1] = 1
    resolutions: tuple[CapabilityResolution, ...] = ()
    selected_tool_names: tuple[str, ...] = ()
    blocked_tool_names: tuple[str, ...] = ()
    fallback: tuple[str, ...] = ()
    required_ready: bool = True
