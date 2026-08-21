"""Immutable public contracts for Scenario resolution and dry-run previews."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ScenarioSpec(_FrozenModel):
    version: Literal[1] = 1
    id: str
    category: str
    title: str
    description: str
    examples: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    optional_capabilities: tuple[str, ...] = ()
    output_contract: str = "answer"
    fallback_policy: tuple[str, ...] = ()
    allow_subagent: bool = False
    priority: int = 0


class ScenarioCandidate(_FrozenModel):
    version: Literal[1] = 1
    scenario_id: str
    title: str
    confidence: float = Field(ge=0.0, le=1.0)


class ClarificationOption(_FrozenModel):
    version: Literal[1] = 1
    label: str
    description: str
    scenario_id: str | None = None


class ScenarioResolution(_FrozenModel):
    version: Literal[1] = 1
    status: Literal["matched", "ambiguous", "general", "invalid"]
    scenario_id: str | None = None
    source: Literal["explicit", "domain_adapter", "matcher", "general", "invalid"]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    candidates: tuple[ScenarioCandidate, ...] = ()
    clarification_options: tuple[ClarificationOption, ...] = ()
    reason: str = ""


class TurnPlanPreview(_FrozenModel):
    """Content-safe planner projection returned by REST and attached to trace events."""

    version: Literal[1] = 1
    scenario: ScenarioResolution
    route: str
    capability_readiness: tuple[dict[str, object], ...] = ()
    selected_tool_names: tuple[str, ...] = ()
    blocked_tool_names: tuple[str, ...] = ()
    skill_names: tuple[str, ...] | None = None
    fallback: tuple[str, ...] = ()
    estimated_model_calls: int = 1
    subagent_eligible: bool = False
    subagent_started: bool = False
    warnings: tuple[str, ...] = ()
