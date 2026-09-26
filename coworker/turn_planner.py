"""Per-turn routing and context/tool projection plan (D-165).

``TurnPlanner.plan`` is the single seam between request classification and the
engine loop.  The returned ``TurnPlan`` is immutable so retries can reuse exactly
the same route, prompt profile, skill menu and provider-visible tool policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable

from .capabilities import CapabilityPlan, CapabilityResolver
from .config import Config
from .execution_profile import ExecutionProfile, RequestRoute
from .market_intent import MarketToolSelection
from .request_router import (
    RequestRouter,
    RouteDecision,
    RouterContext,
)
from .scenarios import (
    ScenarioResolution,
    ScenarioResolver,
    TurnPlanPreview,
)
from .tool_policy import TurnToolPolicy, filter_tool_names
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
        """Use one general execution contract; workflows live in Skills.

        Source/origin influence delivery and identity, never tool authorization.
        The registry and PermissionEngine remain authoritative.
        """
        from .request_router import _detect_tool_policy
        text, _ = _text_and_attachment(user_input)
        policy = _detect_tool_policy(text)
        names = tuple(filter_tool_names(self._available_tool_names(), policy))
        return TurnPlan(
            decision=RouteDecision(RequestRoute.AGENT, "general", "通用执行引擎", tool_policy=policy),
            execution_profile=ExecutionProfile(
                route=RequestRoute.AGENT, max_iterations=self.config.max_iterations,
                target_iterations=None, tools_enabled=not policy.no_tools,
                allowed_tool_names=None, budget_guidance_enabled=False,
                emergency_finalization_enabled=False, reasoning_mode="default",
            ),
            tool_policy=policy, prompt_profile=PromptProfile.AGENT,
            skill_names=None, market_selection=None, show_reasoning=True,
            capability_plan=CapabilityPlan(selected_tool_names=names),
        )

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
