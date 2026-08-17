"""Safe performance / routing instrumentation (Section 65 step 48).

Records route, guards, budget, and stream-mode signals without secrets, full prompts,
or sensitive tool results. Does not change product semantics.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping, Optional

_log = logging.getLogger(__name__)

FORBIDDEN_INSTRUMENTATION_KEYS = frozenset(
    {
        "api_key",
        "apiKey",
        "authorization",
        "Authorization",
        "prompt",
        "messages",
        "content",
        "tool_result",
        "tool_results",
        "email",
        "body",
        "password",
        "secret",
        "token",
        "raw",
        "text",
    }
)


def _safe_copy(payload: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key in FORBIDDEN_INSTRUMENTATION_KEYS:
            continue
        if isinstance(key, str) and key.lower() in {
            "api_key",
            "apikey",
            "authorization",
            "password",
            "secret",
            "token",
        }:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        elif isinstance(value, (list, tuple)):
            # Counts / short enums only — never nested message bodies.
            if all(isinstance(x, (str, int, float, bool)) or x is None for x in value):
                out[key] = list(value)
            else:
                out[key] = len(value)
        else:
            out[key] = str(type(value).__name__)
    return out


def emit_instrumentation(event: str, payload: Mapping[str, Any]) -> None:
    """Best-effort structured log. Never raises into the agent loop."""
    try:
        safe = _safe_copy(payload)
        _log.info("chemclaw.perf %s %s", event, json.dumps(safe, ensure_ascii=False, default=str))
    except Exception:
        pass


def snapshot_from_route_decision(decision: Any | None) -> dict[str, Any]:
    """Derive turn-level router fields from a RouteDecision (or None when OFF)."""
    if decision is None:
        return {
            "route": None,
            "route_source": None,
            "route_reason": None,
            "classifier_used": False,
            "pending_state_guard_hit": False,
            "product_action_gate_hit": False,
            "forced_skill_guard_hit": False,
            "selected_persona_guard_hit": False,
            "tool_policy_no_tools": False,
            "tool_policy_no_search": False,
            "tool_policy_no_external_network": False,
            "legacy_fallback_used": False,
            "allowed_tool_count": None,
            "mandatory_tool_count": None,
        }
    source = getattr(decision, "source", None) or ""
    reason = getattr(decision, "reason", None) or ""
    policy = getattr(decision, "tool_policy", None)
    allowed = getattr(decision, "allowed_tool_names", None)
    classifier_calls = int(getattr(decision, "classifier_calls", 0) or 0)
    route = getattr(decision, "route", None)
    route_value = getattr(route, "value", None) if route is not None else None
    # Persona/skill guard shares source="override" in the router.
    override_hit = source == "override"
    forced = override_hit and (
        "forced" in reason.lower() or "skill" in reason.lower()
    )
    persona = override_hit and (
        "persona" in reason.lower() or "selected" in reason.lower()
    )
    if override_hit and not forced and not persona:
        # Broad override: count both so smoke can see the guard fired.
        forced = True
        persona = True
    return {
        "route": route_value,
        "route_source": source or None,
        "route_reason": reason or None,
        "classifier_used": classifier_calls > 0 or source == "classifier",
        "pending_state_guard_hit": source == "pending_state",
        "product_action_gate_hit": source == "product_action",
        "forced_skill_guard_hit": forced,
        "selected_persona_guard_hit": persona,
        "tool_policy_no_tools": bool(getattr(policy, "no_tools", False)),
        "tool_policy_no_search": bool(getattr(policy, "no_search", False)),
        "tool_policy_no_external_network": bool(
            getattr(policy, "no_external_network", False)
        ),
        "legacy_fallback_used": source == "legacy_fallback",
        "allowed_tool_count": None if allowed is None else len(allowed),
        "mandatory_tool_count": None,
    }


def build_turn_snapshot(
    *,
    route_decision: Any | None = None,
    execution_profile: Any | None = None,
    tool_projection_enabled: bool = False,
    tools_enabled: Optional[bool] = None,
    allowed_tool_count: Optional[int] = None,
    reasoning_mode: Optional[str] = None,
    router_elapsed_ms: Optional[float] = None,
    mandatory_tool_count: Optional[int] = None,
) -> dict[str, Any]:
    base = snapshot_from_route_decision(route_decision)
    if execution_profile is not None:
        base["profile_max_iterations"] = getattr(
            execution_profile, "max_iterations", None
        )
        if reasoning_mode is None:
            reasoning_mode = getattr(execution_profile, "reasoning_mode", None)
        if allowed_tool_count is None:
            names = getattr(execution_profile, "allowed_tool_names", None)
            if names is not None:
                allowed_tool_count = len(names)
            route = getattr(execution_profile, "route", None)
            # Pure FAST/KNOWLEDGE with projection ON → tools disabled.
            if tools_enabled is None and route is not None:
                rv = getattr(route, "value", str(route))
                if rv in ("fast_chat", "knowledge") and tool_projection_enabled:
                    tools_enabled = False
                    allowed_tool_count = 0
    if tools_enabled is not None:
        base["tools_enabled"] = bool(tools_enabled)
    if allowed_tool_count is not None:
        base["allowed_tool_count"] = allowed_tool_count
    if reasoning_mode is not None:
        base["reasoning_mode"] = reasoning_mode
    if router_elapsed_ms is not None:
        base["router_elapsed_ms"] = float(router_elapsed_ms)
    if mandatory_tool_count is not None:
        base["mandatory_tool_count"] = int(mandatory_tool_count)
    base["tool_projection_mode"] = (
        "projected" if tool_projection_enabled else "legacy_full"
    )
    return base


def build_model_call_snapshot(
    *,
    iteration: int,
    budget_phase: Optional[str] = None,
    elapsed_ms: Optional[float] = None,
    first_visible_delta_ms: Optional[float] = None,
    stream_attempts: Optional[int] = None,
    tool_count: Optional[int] = None,
    finish_reason: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "iteration": iteration,
        "budget_phase": budget_phase,
        "elapsed_ms": elapsed_ms,
        "first_visible_delta_ms": first_visible_delta_ms,
        "stream_attempts": stream_attempts,
        "tool_count": tool_count,
        "finish_reason": finish_reason,
    }


def build_provider_stream_snapshot(
    *,
    stream_attempt: int,
    stream_mode: str,
    provider_progress_seen: bool = False,
    visible_output_seen: bool = False,
    tool_progress_seen: bool = False,
    transport_failure_type: Optional[str] = None,
    retried: bool = False,
    fallback_used: bool = False,
    textual_tool_salvage_used: bool = False,
) -> dict[str, Any]:
    return {
        "stream_attempt": stream_attempt,
        "stream_mode": stream_mode,
        "provider_progress_seen": provider_progress_seen,
        "visible_output_seen": visible_output_seen,
        "tool_progress_seen": tool_progress_seen,
        "transport_failure_type": transport_failure_type,
        "retried": retried,
        "fallback_used": fallback_used,
        "textual_tool_salvage_used": textual_tool_salvage_used,
    }
