"""Built-in Scenario catalog and deterministic per-turn resolution (D-169)."""

from .matcher import (
    ScenarioMatcher,
    ScenarioResolver,
    text_has_deep_research_intent,
    text_has_market_report_intent,
)
from .models import ScenarioResolution, ScenarioSpec, TurnPlanPreview
from .registry import ScenarioRegistry, builtin_scenario_registry

__all__ = [
    "ScenarioMatcher",
    "ScenarioRegistry",
    "ScenarioResolution",
    "ScenarioResolver",
    "ScenarioSpec",
    "TurnPlanPreview",
    "builtin_scenario_registry",
    "text_has_deep_research_intent",
    "text_has_market_report_intent",
]
