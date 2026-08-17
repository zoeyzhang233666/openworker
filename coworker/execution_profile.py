"""Optional route execution profile + soft-budget phase plumbing (HARD STOP C).

Activation rule (legacy-inert):
  Without an explicit ExecutionProfile on the TurnEngine, none of this module's
  soft targets, Converge/Deliver guidance, or reasoning-mode defaults apply.
  Legacy sessions remain governed solely by config.max_iterations / model_settings
  and the existing state machine. Route-specific behavior is activated only when a
  caller (future Router, or tests) constructs and attaches a profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .config import Config


class RequestRoute(str, Enum):
    FAST_CHAT = "fast_chat"
    KNOWLEDGE = "knowledge"
    VERIFIED = "verified"
    AGENT = "agent"
    DEEP_RESEARCH = "deep_research"


class BudgetPhase(str, Enum):
    EXPLORE = "explore"
    CONVERGE = "converge"
    DELIVER = "deliver"
    EXTENDED = "extended"


@dataclass(frozen=True)
class ExecutionProfile:
    route: RequestRoute
    max_iterations: int  # hard ceiling for this profile
    target_iterations: int | None  # soft target; None for FAST/KNOWLEDGE/VERIFIED
    tools_enabled: bool
    allowed_tool_names: tuple[str, ...] | None
    budget_guidance_enabled: bool
    emergency_finalization_enabled: bool
    reasoning_mode: str  # "off" | "low" | "default" | "high"


_CONVERGE_NOTICE = """Iteration budget notice:

You are in the convergence phase.

Stop broad exploratory research.
Only perform additional searches or reads when they fill a material evidence gap
that could change the conclusion.

Batch independent low-risk reads/searches into the same tool-call turn whenever possible.

Start consolidating evidence, resolving contradictions, and preparing the final deliverable."""

_DELIVER_NOTICE = """Iteration budget notice:

You are in the delivery phase.

Stop broad exploration now.

Use the evidence already collected.
Only perform a new tool call if it is strictly necessary to complete or verify
the final deliverable.

Prioritize:
1. resolve critical remaining contradictions;
2. complete/update the deliverable;
3. verify coherence;
4. answer the user.

Do not start a new research branch."""

_EXTENDED_NOTICE = """Iteration budget notice:

You are past the soft delivery target and in extended delivery.

Do not restart broad exploration.
Only fill critical remaining gaps needed to finish the deliverable."""

_HARD_CEILING_WARN = """Only 2 hard-ceiling model iterations remain.
Finish the deliverable now.
Do not initiate new exploratory work."""


def effective_soft_target(
    configured_target: int | None, hard: int
) -> int | None:
    if configured_target is None:
        return None
    return min(int(configured_target), int(hard))


def budget_thresholds(*, hard: int, target: int) -> tuple[int, int]:
    """Return (converge_at, deliver_at) inclusive phase start iterations."""
    hard = max(1, int(hard))
    target = min(max(1, int(target)), hard)
    converge_at = max(1, int(target * 0.75))
    deliver_at = max(converge_at + 1, target - 4)
    converge_at = min(converge_at, hard)
    deliver_at = min(max(deliver_at, converge_at), hard)
    return converge_at, deliver_at


def budget_phase_for_iteration(
    iteration: int, *, hard: int, target: int | None
) -> BudgetPhase:
    """Map 1-based iteration index onto Explore / Converge / Deliver / Extended."""
    if target is None:
        return BudgetPhase.EXPLORE
    converge_at, deliver_at = budget_thresholds(hard=hard, target=target)
    effective_target = min(target, hard)
    if iteration < converge_at:
        return BudgetPhase.EXPLORE
    if iteration < deliver_at:
        return BudgetPhase.CONVERGE
    if iteration <= effective_target:
        return BudgetPhase.DELIVER
    return BudgetPhase.EXTENDED


def budget_guidance_text(
    phase: BudgetPhase,
    *,
    iteration: int | None = None,
    hard: int | None = None,
) -> str | None:
    if phase is BudgetPhase.EXPLORE:
        return None
    if phase is BudgetPhase.CONVERGE:
        body = _CONVERGE_NOTICE
    elif phase is BudgetPhase.DELIVER:
        body = _DELIVER_NOTICE
    else:
        body = _EXTENDED_NOTICE
    if (
        iteration is not None
        and hard is not None
        and hard >= 2
        and iteration >= hard - 1
    ):
        return f"{body}\n\n{_HARD_CEILING_WARN}"
    return body


def apply_reasoning_mode_settings(
    settings: dict[str, Any],
    reasoning_mode: str,
    *,
    supports_disable_reasoning: bool = False,
) -> dict[str, Any]:
    """Return a copy of settings with optional reasoning_effort for FAST_CHAT-style off.

    Never invent unsupported parameters when the provider/model cannot disable reasoning.
    """
    out = dict(settings)
    if reasoning_mode == "off" and supports_disable_reasoning:
        out.setdefault("reasoning_effort", "none")
    return out


def make_execution_profile(
    route: RequestRoute,
    config: "Config",
    *,
    allowed_tool_names: tuple[str, ...] | None = None,
    emergency_finalization_enabled: bool | None = None,
) -> ExecutionProfile:
    """Build a route profile from Config. Does not attach itself to any engine."""
    hard = int(config.max_iterations)
    ef = (
        bool(config.emergency_finalization_enabled)
        if emergency_finalization_enabled is None
        else bool(emergency_finalization_enabled)
    )
    # FAST/KNOWLEDGE never emergency-finalize; AGENT/DEEP/VERIFIED mirror Config/override.
    if route is RequestRoute.FAST_CHAT:
        return ExecutionProfile(
            route=route,
            max_iterations=1,
            target_iterations=None,
            tools_enabled=False,
            allowed_tool_names=(),
            budget_guidance_enabled=False,
            emergency_finalization_enabled=False,
            reasoning_mode="off",
        )
    if route is RequestRoute.KNOWLEDGE:
        return ExecutionProfile(
            route=route,
            max_iterations=1,
            target_iterations=None,
            tools_enabled=False,
            allowed_tool_names=(),
            budget_guidance_enabled=False,
            emergency_finalization_enabled=False,
            reasoning_mode="low",
        )
    if route is RequestRoute.VERIFIED:
        verified_hard = min(int(config.verified_max_iterations), hard)
        return ExecutionProfile(
            route=route,
            max_iterations=verified_hard,
            target_iterations=None,
            tools_enabled=True,
            allowed_tool_names=allowed_tool_names,
            budget_guidance_enabled=False,
            emergency_finalization_enabled=ef,
            reasoning_mode="low",
        )
    if route is RequestRoute.AGENT:
        target = effective_soft_target(config.agent_target_iterations, hard)
        return ExecutionProfile(
            route=route,
            max_iterations=hard,
            target_iterations=target,
            tools_enabled=True,
            allowed_tool_names=None,
            budget_guidance_enabled=True,
            emergency_finalization_enabled=ef,
            reasoning_mode="default",
        )
    if route is RequestRoute.DEEP_RESEARCH:
        target = effective_soft_target(config.deep_research_target_iterations, hard)
        return ExecutionProfile(
            route=route,
            max_iterations=hard,
            target_iterations=target,
            tools_enabled=True,
            allowed_tool_names=None,
            budget_guidance_enabled=True,
            emergency_finalization_enabled=ef,
            reasoning_mode="default",
        )
    raise ValueError(f"unsupported route: {route!r}")


def profile_is_active(profile: Optional[ExecutionProfile]) -> bool:
    return profile is not None
