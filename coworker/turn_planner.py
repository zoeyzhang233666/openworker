"""Per-turn routing and context/tool projection plan (D-165).

``TurnPlanner.plan`` is the single seam between request classification and the
engine loop.  The returned ``TurnPlan`` is immutable so retries can reuse exactly
the same route, prompt profile, skill menu and provider-visible tool policy.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from enum import Enum
from typing import Callable, Iterable

from .config import Config
from .execution_profile import ExecutionProfile, RequestRoute
from .request_router import (
    RequestRouter,
    RouteDecision,
    RouterContext,
    decision_to_execution_profile,
)
from .tool_policy import TurnToolPolicy
from .tool_projection import select_agent_tool_names, select_verified_tool_names


class PromptProfile(str, Enum):
    LEGACY = "legacy"
    FAST = "fast"
    KNOWLEDGE = "knowledge"
    VERIFIED = "verified"
    VERIFIED_MARKET = "verified_market"
    AGENT = "agent"
    AGENT_TARGETED = "agent_targeted"
    AGENT_WORKSPACE = "agent_workspace"
    AGENT_VISUAL = "agent_visual"
    DEEP_RESEARCH = "deep_research"


_PROMPT_PROFILE_BY_ROUTE = {
    RequestRoute.FAST_CHAT: PromptProfile.FAST,
    RequestRoute.KNOWLEDGE: PromptProfile.KNOWLEDGE,
    RequestRoute.VERIFIED: PromptProfile.VERIFIED,
    RequestRoute.AGENT: PromptProfile.AGENT,
    RequestRoute.DEEP_RESEARCH: PromptProfile.DEEP_RESEARCH,
}


@dataclass(frozen=True)
class TurnPlan:
    """Everything in the engine that may vary for one user turn.

    ``skill_names=None`` means the legacy/full live catalog.  An empty tuple
    means no catalog.  This distinction is deliberately parallel to
    ``ExecutionProfile.allowed_tool_names``.
    """

    decision: RouteDecision | None
    execution_profile: ExecutionProfile | None
    tool_policy: TurnToolPolicy | None
    prompt_profile: PromptProfile
    skill_names: tuple[str, ...] | None
    show_reasoning: bool
    router_elapsed_ms: float | None = None

    @classmethod
    def legacy(cls) -> "TurnPlan":
        return cls(
            decision=None,
            execution_profile=None,
            tool_policy=None,
            prompt_profile=PromptProfile.LEGACY,
            skill_names=None,
            show_reasoning=True,
        )


ContextProvider = Callable[[], RouterContext]
SkillSelector = Callable[[str, Iterable[str]], tuple[str, ...]]


class TurnPlanner:
    """Build one conservative, immutable plan from current request state."""

    def __init__(
        self,
        *,
        config: Config,
        available_tool_names: Callable[[], Iterable[str]],
        context_provider: ContextProvider | None = None,
        skill_selector: SkillSelector | None = None,
        preferred_skill_names: Iterable[str] = (),
        router: RequestRouter | None = None,
    ) -> None:
        self.config = config
        self._available_tool_names = available_tool_names
        self._context_provider = context_provider or RouterContext
        self._skill_selector = skill_selector
        self._preferred_skill_names = tuple(preferred_skill_names)
        self._router = router or RequestRouter(config=config)

    def plan(
        self,
        user_input: str | list,
        *,
        source: dict | None = None,
        display: str | None = None,
        durable_resume: bool = False,
    ) -> TurnPlan:
        """Plan the turn; uncertain/unsafe state is forced to the full AGENT path."""
        if not self.config.request_routing_enabled:
            return TurnPlan.legacy()

        started = time.perf_counter()
        text, has_attachment = _text_and_attachment(user_input)
        context = self._context_provider()
        guarded_full_agent = bool(
            has_attachment
            or source is not None
            or display is not None
            or durable_resume
            or context.pending_ask_user
            or context.pending_approval
            or context.pending_plan
            or context.pending_request_directory
            or context.durable_resume
            or context.unanswered_trailing_tool_calls
            or context.stop_requested
            or context.forced_skill_ids
            or context.default_skill_active
            or (context.selected_persona_id and not context.is_default_persona)
            or text.lstrip().startswith(("⏰ Scheduled run", "⏰ Wake"))
        )

        # Attachments, connector/background deliveries, force-run skills and durable
        # resume must retain the full execution surface.  Reusing the router's pending
        # guard keeps the conservative fallback and instrumentation semantics aligned.
        if guarded_full_agent:
            context = replace(context, durable_resume=True)

        decision = self._router.route(text, context=context)
        if decision is None:
            return TurnPlan.legacy()

        # The request router has a small static VERIFIED universe for pure tests.  At
        # the production seam, re-select against the actual live registry so CN market,
        # Yahoo and newly registered known tools can be projected correctly.
        if decision.route is RequestRoute.VERIFIED:
            selected = select_verified_tool_names(text, self._available_tool_names())
            decision = replace(decision, allowed_tool_names=selected)
        elif decision.route is RequestRoute.AGENT and not guarded_full_agent:
            selected = select_agent_tool_names(text, self._available_tool_names())
            decision = replace(decision, allowed_tool_names=selected)

        profile = decision_to_execution_profile(decision, self.config)
        skill_names: tuple[str, ...] | None
        if decision.route in (
            RequestRoute.FAST_CHAT,
            RequestRoute.KNOWLEDGE,
            RequestRoute.VERIFIED,
        ):
            skill_names = ()
        elif self._skill_selector is None:
            skill_names = None
        else:
            preferred = list(self._preferred_skill_names)
            if display:
                preferred.extend(_forced_skill_names(display))
            skill_names = self._skill_selector(text, preferred)

        if skill_names and profile.allowed_tool_names is not None:
            live = set(self._available_tool_names())
            expanded = list(profile.allowed_tool_names)
            for name in ("search_skills", "load_skill"):
                if name in live and name not in expanded:
                    expanded.append(name)
            allowed = tuple(expanded)
            decision = replace(decision, allowed_tool_names=allowed)
            profile = replace(profile, allowed_tool_names=allowed)

        prompt_profile = _PROMPT_PROFILE_BY_ROUTE[decision.route]
        allowed = profile.allowed_tool_names
        if decision.route is RequestRoute.VERIFIED and allowed is not None:
            if any(
                name.startswith("lookup_cn_") or name == "lookup_yahoo_ohlc"
                for name in allowed
            ):
                prompt_profile = PromptProfile.VERIFIED_MARKET
        elif decision.route is RequestRoute.AGENT and allowed is not None:
            workspace_names = {
                "read_file",
                "write_file",
                "edit_file",
                "apply_patch",
                "run_shell",
                "run_terminal_cmd",
                "git_status",
            }
            if workspace_names.intersection(allowed):
                prompt_profile = (
                    PromptProfile.AGENT_VISUAL
                    if _visual_delivery_requested(text)
                    else PromptProfile.AGENT_WORKSPACE
                )
            else:
                prompt_profile = PromptProfile.AGENT_TARGETED

        return TurnPlan(
            decision=decision,
            execution_profile=profile,
            tool_policy=decision.tool_policy,
            prompt_profile=prompt_profile,
            skill_names=skill_names,
            # Provider request policy and UI visibility are independent.  A provider
            # that emits reasoning is always surfaced immediately.
            show_reasoning=True,
            router_elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )


def _text_and_attachment(user_input: str | list) -> tuple[str, bool]:
    if isinstance(user_input, str):
        return user_input, False
    texts: list[str] = []
    has_attachment = False
    for part in user_input:
        if not isinstance(part, dict):
            has_attachment = True
            continue
        kind = part.get("type")
        if kind in ("text", "input_text") and isinstance(part.get("text"), str):
            texts.append(part["text"])
        else:
            has_attachment = True
    return "\n".join(texts).strip(), has_attachment


def _forced_skill_names(display: str) -> tuple[str, ...]:
    raw = (display or "").strip()
    if not raw.lower().startswith("/skill"):
        return ()
    bits = raw.split()
    return (bits[1],) if len(bits) > 1 else ()


def _visual_delivery_requested(text: str) -> bool:
    low = (text or "").lower()
    return any(
        marker in low
        for marker in (
            "mermaid",
            "流程图",
            "架构图",
            "关系图",
            "图表",
            "趋势图",
            "k线",
            "candlestick",
            "chart",
        )
    )
