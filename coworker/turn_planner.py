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

from .capabilities import CapabilityPlan, CapabilityResolver
from .channels.delivery import (
    CHANNEL_DENIED_TOOLS,
    is_channel_user_source,
)
from .config import Config
from .execution_profile import ExecutionProfile, RequestRoute
from .market_intent import MarketToolSelection, resolve_market_tools
from .request_router import (
    RequestRouter,
    RouteDecision,
    RouterContext,
    decision_to_execution_profile,
)
from .scenarios import (
    ScenarioResolution,
    ScenarioResolver,
    TurnPlanPreview,
    builtin_scenario_registry,
    text_has_deep_research_intent,
)
from .tool_policy import TurnToolPolicy
from .tool_projection import select_agent_tool_names, select_verified_tool_names
from .tools.registry import ToolDescriptor


class PromptProfile(str, Enum):
    LEGACY = "legacy"
    FAST = "fast"
    KNOWLEDGE = "knowledge"
    VERIFIED = "verified"
    VERIFIED_MARKET = "verified_market"
    REPORT_SUMMARY = "report_summary"
    REPORT_CHANNEL = "report_channel"
    AGENT = "agent"
    AGENT_TARGETED = "agent_targeted"
    AGENT_WORKSPACE = "agent_workspace"
    AGENT_VISUAL = "agent_visual"
    DEEP_RESEARCH = "deep_research"


class TurnOrigin(str, Enum):
    """Execution provenance, deliberately separate from the display-only source card."""

    USER = "user"
    RESUME = "resume"
    SCHEDULED = "scheduled"
    SELF_WAKE = "self_wake"
    BACKGROUND = "background"
    SUBAGENT_COMPLETE = "subagent_complete"


_PROMPT_PROFILE_BY_ROUTE = {
    RequestRoute.FAST_CHAT: PromptProfile.FAST,
    RequestRoute.KNOWLEDGE: PromptProfile.KNOWLEDGE,
    RequestRoute.VERIFIED: PromptProfile.VERIFIED,
    RequestRoute.AGENT: PromptProfile.AGENT,
    RequestRoute.DEEP_RESEARCH: PromptProfile.DEEP_RESEARCH,
}

_SUBAGENT_CONTROL_TOOL_NAMES = (
    "start_subagent",
    "background_task_status",
    "background_task_output",
    "background_task_send",
    "background_task_stop",
    "background_task_gather",
)

# Parent synthesis surface for allow_subagent research scenarios (D-184).
# Quote/MCP market tools stay on research children — not merged back to parent.
_RESEARCH_PARENT_SYNTHESIS_TOOL_NAMES = (
    "read_file",
    "list_files",
    "write_file",
    "edit_file",
    "todo_write",
)


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
    market_selection: MarketToolSelection | None
    show_reasoning: bool
    router_elapsed_ms: float | None = None
    scenario_resolution: ScenarioResolution | None = None
    capability_plan: CapabilityPlan | None = None
    scenario_projection_applied: bool = False
    subagent_eligible: bool = False
    subagent_tool_names: tuple[str, ...] = ()

    @classmethod
    def legacy(cls) -> "TurnPlan":
        return cls(
            decision=None,
            execution_profile=None,
            tool_policy=None,
            prompt_profile=PromptProfile.LEGACY,
            skill_names=None,
            market_selection=None,
            show_reasoning=True,
        )

    def preview(self) -> TurnPlanPreview:
        scenario = self.scenario_resolution or ScenarioResolution(
            status="general",
            source="general",
            reason="scenario resolution disabled",
        )
        capability = self.capability_plan or CapabilityPlan()
        route = self.decision.route.value if self.decision is not None else "legacy"
        warnings: list[str] = []
        if scenario.status == "ambiguous":
            warnings.append("需要先澄清 Scenario 或市场口径")
        if capability.resolutions and not capability.required_ready:
            warnings.append("一个或多个必需 Capability 当前不可用")
        selected_tool_names = capability.selected_tool_names
        if self.subagent_tool_names:
            selected_tool_names = tuple(
                dict.fromkeys((*selected_tool_names, *self.subagent_tool_names))
            )
        blocked_tool_names = tuple(
            name
            for name in capability.blocked_tool_names
            if name not in self.subagent_tool_names
        )
        if self.subagent_eligible and not self.subagent_tool_names:
            warnings.append("Subagent Runtime 当前不可用")
        return TurnPlanPreview(
            scenario=scenario,
            route=route,
            capability_readiness=tuple(
                item.model_dump(exclude={"version"}) for item in capability.resolutions
            ),
            selected_tool_names=selected_tool_names,
            blocked_tool_names=blocked_tool_names,
            skill_names=self.skill_names,
            fallback=capability.fallback,
            estimated_model_calls=2 if capability.selected_tool_names else 1,
            subagent_eligible=self.subagent_eligible,
            subagent_started=False,
            warnings=tuple(warnings),
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
        available_tools: Callable[[], Iterable[ToolDescriptor]] | None = None,
        configured_tool_names: Callable[[], Iterable[str]] | None = None,
        context_provider: ContextProvider | None = None,
        skill_selector: SkillSelector | None = None,
        preferred_skill_names: Iterable[str] = (),
        router: RequestRouter | None = None,
        scenario_resolver: ScenarioResolver | None = None,
        capability_resolver: CapabilityResolver | None = None,
    ) -> None:
        self.config = config
        self._available_tool_names = available_tool_names
        self._available_tools = available_tools
        self._configured_tool_names = configured_tool_names or (lambda: ())
        self._context_provider = context_provider or RouterContext
        self._skill_selector = skill_selector
        self._preferred_skill_names = tuple(preferred_skill_names)
        self._router = router or RequestRouter(config=config)
        self._scenario_resolver = scenario_resolver or ScenarioResolver()
        self._capability_resolver = capability_resolver or CapabilityResolver()

    def plan(
        self,
        user_input: str | list,
        *,
        source: dict | None = None,
        origin: TurnOrigin = TurnOrigin.USER,
        display: str | None = None,
        durable_resume: bool = False,
        scenario_id: str | None = None,
    ) -> TurnPlan:
        """Plan the turn; uncertain/unsafe state is forced to the full AGENT path."""
        if not self.config.request_routing_enabled:
            return TurnPlan.legacy()

        started = time.perf_counter()
        text, has_attachment = _text_and_attachment(user_input)
        channel_user = (
            origin is TurnOrigin.USER and is_channel_user_source(source)
        )
        context = self._context_provider()
        guarded_full_agent = bool(
            has_attachment
            or origin is not TurnOrigin.USER
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
        market_selection: MarketToolSelection | None = None
        descriptors: tuple[ToolDescriptor, ...] | None = None
        if self.config.tool_projection_enabled and decision.route in (
            RequestRoute.VERIFIED,
            RequestRoute.AGENT,
            RequestRoute.DEEP_RESEARCH,
        ):
            descriptors = self._tool_descriptors()
            candidate_market = resolve_market_tools(text, descriptors)
            if candidate_market.intent.is_market:
                market_selection = candidate_market
            if (
                not guarded_full_agent
                and decision.route is RequestRoute.AGENT
                and decision.source == "legacy_fallback"
                and candidate_market.intent.is_market
                and not text_has_deep_research_intent(text)
            ):
                # Deterministic market intent outranks the generic classifier fallback.
                # Deep research keeps AGENT/DEEP_RESEARCH so Subagent eligibility survives;
                # pure quote lookups still collapse to VERIFIED.
                market_selection = candidate_market
                decision = replace(
                    decision,
                    route=RequestRoute.VERIFIED,
                    source="market_intent",
                    reason="deterministic market scope requires targeted data tools",
                )
        scenario_resolution: ScenarioResolution | None = None
        capability_plan: CapabilityPlan | None = None
        scenario_projection_applied = False
        subagent_eligible = False
        subagent_tool_names: tuple[str, ...] = ()
        if self.config.scenario_resolution_enabled:
            descriptors = descriptors or self._tool_descriptors()
            scenario_resolution = self._scenario_resolver.resolve(
                text,
                explicit_scenario_id=scenario_id,
                tools=descriptors,
                market_selection=market_selection,
            )
            if scenario_resolution.status == "invalid":
                raise InvalidScenarioError(scenario_resolution.reason)
            capability_plan = self._capability_resolver.resolve(
                scenario_resolution,
                text=text,
                tools=descriptors,
                configured_tool_names=self._configured_tool_names(),
            )
            scenario_spec = (
                builtin_scenario_registry().get(scenario_resolution.scenario_id)
                if scenario_resolution.scenario_id
                else None
            )
            if (
                not guarded_full_agent
                and scenario_spec is not None
                and scenario_spec.output_contract == "staged_market_report"
                and scenario_resolution.status == "matched"
            ):
                decision = replace(
                    decision,
                    route=RequestRoute.VERIFIED,
                    source="scenario_market_report",
                    reason="market report starts with a bounded evidence summary",
                )
            # D-184: matched research scenarios upgrade AGENT → DEEP_RESEARCH so
            # scenario projection narrows the parent tool surface and forces delegation.
            if (
                not guarded_full_agent
                and scenario_spec is not None
                and scenario_spec.allow_subagent
                and scenario_resolution.status == "matched"
                and decision.route is RequestRoute.AGENT
            ):
                decision = replace(
                    decision,
                    route=RequestRoute.DEEP_RESEARCH,
                    source="scenario_research",
                    reason="matched research scenario requires bounded subagent delegation",
                )
            subagent_eligible = bool(
                scenario_spec
                and scenario_spec.allow_subagent
                and scenario_resolution.status == "matched"
                and decision.route in {RequestRoute.AGENT, RequestRoute.DEEP_RESEARCH}
                and not channel_user
            )
            if subagent_eligible:
                live_names = set(self._available_tool_names())
                subagent_tool_names = tuple(
                    name for name in _SUBAGENT_CONTROL_TOOL_NAMES if name in live_names
                )
            scenario_projection_applied = bool(
                not guarded_full_agent
                and self.config.tool_projection_enabled
                and decision.route in {RequestRoute.VERIFIED, RequestRoute.DEEP_RESEARCH}
                and scenario_resolution.status in {"matched", "ambiguous"}
            )
            if scenario_projection_applied:
                selected = capability_plan.selected_tool_names
                if subagent_tool_names:
                    selected = tuple(
                        dict.fromkeys((*selected, *subagent_tool_names))
                    )
                # Research parents keep synthesis + web/subagent only — never re-merge
                # market quote tools that would let the parent serially skip delegation.
                if (
                    scenario_spec is not None
                    and scenario_spec.allow_subagent
                    and scenario_resolution.status == "matched"
                ):
                    live_names = set(self._available_tool_names())
                    synthesis = tuple(
                        name
                        for name in _RESEARCH_PARENT_SYNTHESIS_TOOL_NAMES
                        if name in live_names
                    )
                    selected = tuple(dict.fromkeys((*selected, *synthesis)))
                decision = replace(decision, allowed_tool_names=selected)

        if decision.route is RequestRoute.VERIFIED and not scenario_projection_applied:
            if self.config.tool_projection_enabled:
                descriptors = descriptors or self._tool_descriptors()
                market_selection = market_selection or resolve_market_tools(
                    text, descriptors
                )
                selected = select_verified_tool_names(
                    text,
                    (tool.name for tool in descriptors),
                    market_selection=market_selection,
                )
            else:
                selected = select_verified_tool_names(
                    text, self._available_tool_names()
                )
            decision = replace(decision, allowed_tool_names=selected)
        elif (
            decision.route is RequestRoute.AGENT
            and not guarded_full_agent
            and not scenario_projection_applied
        ):
            selected = select_agent_tool_names(text, self._available_tool_names())
            if selected is not None and subagent_tool_names:
                selected = tuple(dict.fromkeys((*selected, *subagent_tool_names)))
            if (
                selected is not None
                and market_selection is not None
                and market_selection.allowed_tool_names is not None
            ):
                selected = tuple(
                    dict.fromkeys((*selected, *market_selection.allowed_tool_names))
                )
            decision = replace(decision, allowed_tool_names=selected)

        if (
            channel_user
            and not guarded_full_agent
            and decision.route in {RequestRoute.AGENT, RequestRoute.DEEP_RESEARCH}
        ):
            decision = replace(
                decision,
                route=RequestRoute.VERIFIED,
                source="channel_fast",
                reason="channel delivery uses bounded verified surface",
            )

        decision, capability_plan = self._apply_chem_web_fallback(
            decision, capability_plan, market_selection
        )

        profile = decision_to_execution_profile(decision, self.config)
        market_report_channel = (
            channel_user
            and scenario_resolution is not None
            and scenario_resolution.scenario_id == "chemical_market_report"
        )
        if (
            scenario_resolution is not None
            and scenario_resolution.scenario_id == "chemical_market_report"
        ):
            cap = 6 if market_report_channel else 3
            profile = replace(profile, max_iterations=min(cap, profile.max_iterations))
        elif channel_user:
            profile = replace(profile, max_iterations=min(4, profile.max_iterations))
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

        if skill_names and profile.allowed_tool_names is not None and not channel_user:
            live = set(self._available_tool_names())
            expanded = list(profile.allowed_tool_names)
            for name in ("search_skills", "load_skill"):
                if name in live and name not in expanded:
                    expanded.append(name)
            allowed = tuple(expanded)
            decision = replace(decision, allowed_tool_names=allowed)
            profile = replace(profile, allowed_tool_names=allowed)

        if channel_user and profile.allowed_tool_names is not None:
            live = set(self._available_tool_names())
            allowed = [
                name
                for name in profile.allowed_tool_names
                if name not in CHANNEL_DENIED_TOOLS
            ]
            if market_report_channel:
                for name in ("write_file", "edit_file", "read_file", "list_files"):
                    if name in live and name not in allowed:
                        allowed.append(name)
            allowed = tuple(dict.fromkeys(allowed))
            decision = replace(decision, allowed_tool_names=allowed)
            profile = replace(profile, allowed_tool_names=allowed)

        prompt_profile = _PROMPT_PROFILE_BY_ROUTE[decision.route]
        if (
            scenario_resolution is not None
            and scenario_resolution.scenario_id == "chemical_market_report"
        ):
            prompt_profile = (
                PromptProfile.REPORT_CHANNEL
                if market_report_channel
                else PromptProfile.REPORT_SUMMARY
            )
        allowed = profile.allowed_tool_names
        if (
            decision.route is RequestRoute.VERIFIED
            and market_selection is not None
            and market_selection.intent.is_market
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
            market_selection=market_selection,
            # Provider request policy and UI visibility are independent.  A provider
            # that emits reasoning is always surfaced immediately.
            show_reasoning=True,
            router_elapsed_ms=(time.perf_counter() - started) * 1000.0,
            scenario_resolution=scenario_resolution,
            capability_plan=capability_plan,
            scenario_projection_applied=scenario_projection_applied,
            subagent_eligible=subagent_eligible,
            subagent_tool_names=subagent_tool_names,
        )

    def _apply_chem_web_fallback(
        self,
        decision: RouteDecision,
        capability_plan: CapabilityPlan | None,
        market_selection: MarketToolSelection | None,
    ) -> tuple[RouteDecision, CapabilityPlan | None]:
        """D-181: keep scenario-narrow primary tools, but always expose chem Web fallback."""
        if (
            market_selection is None
            or not market_selection.web_is_supplemental
            or decision.allowed_tool_names is None
        ):
            return decision, capability_plan
        web = tuple(
            name
            for name in (market_selection.allowed_tool_names or ())
            if name in {"web_search", "web_fetch"}
        )
        if not web:
            return decision, capability_plan
        allowed = tuple(dict.fromkeys((*decision.allowed_tool_names, *web)))
        decision = replace(decision, allowed_tool_names=allowed)
        if capability_plan is not None:
            selected = tuple(
                dict.fromkeys((*capability_plan.selected_tool_names, *web))
            )
            live = set(self._available_tool_names())
            capability_plan = capability_plan.model_copy(
                update={
                    "selected_tool_names": selected,
                    "blocked_tool_names": tuple(sorted(live - set(selected))),
                }
            )
        return decision, capability_plan

    def _tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        if self._available_tools is not None:
            return tuple(self._available_tools())
        return tuple(
            ToolDescriptor(name=name) for name in self._available_tool_names()
        )


class InvalidScenarioError(ValueError):
    """Raised at the planner boundary so REST/WS can reject invalid explicit IDs."""


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
