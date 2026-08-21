"""Deterministic Scenario matching with D-166 as the high-authority adapter."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..market_intent import MarketIntentKind, MarketToolSelection, resolve_market_tools
from ..tools.registry import ToolDescriptor
from .models import ClarificationOption, ScenarioCandidate, ScenarioResolution
from .registry import ScenarioRegistry, builtin_scenario_registry

_CAS_RE = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
_IDENTITY_RE = re.compile(r"(CAS|分子式|化学标识|chemical\s+identity|identify)", re.I)
_RESEARCH_RE = re.compile(r"(深度研究|研究|调研|分析|未来|供需|产业链|research)", re.I)
# Narrower than _RESEARCH_RE: outranks D-166 spot/futures quote scenarios without
# stealing pure price lookups such as "甲醇期货现在多少钱".
_DEEP_RESEARCH_INTENT_RE = re.compile(
    r"(深度研究|周报|调研报告|全面调研|尽职调查|尽调|产业链|上下游|供需分析|"
    r"套利怎么做|研究.{0,20}套利|套利.{0,20}(研究|策略|方法)|"
    r"deep\s+research|industry\s+report|weekly\s+report)",
    re.I,
)
_COMPANY_RE = re.compile(r"(公司|企业|集团|股份|化学|化工|万华|巴斯夫|陶氏|company|corp)", re.I)
_MARKET_RESEARCH_RE = re.compile(r"(市场|供需|产业链|价格驱动|未来半年|market)", re.I)
_COMPANY_SUBJECT_RE = re.compile(r"(万华|巴斯夫|陶氏|公司|企业)", re.I)


def text_has_deep_research_intent(text: str) -> bool:
    """True when the user asked for research rather than a single market quote."""
    return bool(_DEEP_RESEARCH_INTENT_RE.search(text or ""))


def _research_scenario_for_text(text: str, *, confidence: float) -> ScenarioResolution:
    if _COMPANY_RE.search(text) and not _MARKET_RESEARCH_RE.search(text):
        return _adapter_match("chemical_company_research", confidence=confidence)
    if _MARKET_RESEARCH_RE.search(text) and _COMPANY_SUBJECT_RE.search(text):
        return _adapter_match("chemical_company_research", confidence=confidence)
    if _COMPANY_SUBJECT_RE.search(text) and not _MARKET_RESEARCH_RE.search(text):
        return _adapter_match("chemical_company_research", confidence=confidence)
    return _adapter_match("chemical_market_research", confidence=confidence)


class ScenarioMatcher:
    def __init__(self, registry: ScenarioRegistry | None = None) -> None:
        self.registry = registry or builtin_scenario_registry()

    def match(self, text: str) -> ScenarioResolution:
        scored: list[ScenarioCandidate] = []
        for spec in self.registry.list():
            score = _score(text, (*spec.examples, *spec.aliases))
            if score:
                scored.append(
                    ScenarioCandidate(
                        scenario_id=spec.id, title=spec.title, confidence=score
                    )
                )
        scored.sort(key=lambda item: (-item.confidence, item.scenario_id))
        top = scored[0] if scored else None
        second = scored[1] if len(scored) > 1 else None
        if top and top.confidence >= 0.80 and (
            second is None or top.confidence - second.confidence >= 0.15
        ):
            return ScenarioResolution(
                status="matched",
                scenario_id=top.scenario_id,
                source="matcher",
                confidence=top.confidence,
                candidates=tuple(scored[:3]),
                reason="high-confidence built-in scenario match",
            )
        if top and top.confidence >= 0.50:
            return ScenarioResolution(
                status="ambiguous",
                source="matcher",
                confidence=top.confidence,
                candidates=tuple(scored[:3]),
                clarification_options=tuple(
                    ClarificationOption(
                        label=item.title,
                        description=self.registry.require(item.scenario_id).description,
                        scenario_id=item.scenario_id,
                    )
                    for item in scored[:3]
                ),
                reason="scenario candidates require clarification",
            )
        return ScenarioResolution(
            status="general",
            source="general",
            confidence=top.confidence if top else 0.0,
            candidates=tuple(scored[:3]),
            reason="no scenario met the matching threshold",
        )


class ScenarioResolver:
    def __init__(
        self,
        registry: ScenarioRegistry | None = None,
        matcher: ScenarioMatcher | None = None,
    ) -> None:
        self.registry = registry or builtin_scenario_registry()
        self.matcher = matcher or ScenarioMatcher(self.registry)

    def resolve(
        self,
        text: str,
        *,
        explicit_scenario_id: str | None = None,
        tools: Iterable[ToolDescriptor] = (),
        market_selection: MarketToolSelection | None = None,
    ) -> ScenarioResolution:
        if explicit_scenario_id is not None:
            spec = self.registry.get(explicit_scenario_id)
            if spec is None:
                return ScenarioResolution(
                    status="invalid",
                    source="invalid",
                    confidence=1.0,
                    reason=f"unknown scenario id: {explicit_scenario_id}",
                )
            return ScenarioResolution(
                status="matched",
                scenario_id=spec.id,
                source="explicit",
                confidence=1.0,
                reason="explicit scenario id",
            )

        market = market_selection or resolve_market_tools(text, tools)
        # Deep research outranks spot/futures quote adapters so Subagent eligibility
        # is not killed by cn_futures_market / chemical_spot_price (allow_subagent=false).
        if text_has_deep_research_intent(text) and (
            market.needs_clarification
            or market.intent.kind
            in {
                MarketIntentKind.CHEMICAL_SPOT,
                MarketIntentKind.CN_FUTURES,
                MarketIntentKind.CN_SPOT_FUTURES,
            }
            or market.intent.is_market
        ):
            return _research_scenario_for_text(text, confidence=0.92)
        if market.needs_clarification:
            return ScenarioResolution(
                status="ambiguous",
                source="domain_adapter",
                confidence=0.99,
                candidates=(
                    ScenarioCandidate(
                        scenario_id="chemical_spot_price",
                        title=self.registry.require("chemical_spot_price").title,
                        confidence=0.99,
                    ),
                    ScenarioCandidate(
                        scenario_id="cn_futures_market",
                        title=self.registry.require("cn_futures_market").title,
                        confidence=0.99,
                    ),
                ),
                clarification_options=tuple(
                    ClarificationOption(
                        label=item.label,
                        description=item.description,
                        scenario_id=(
                            "chemical_spot_price"
                            if item.scope.value == "chemical_spot"
                            else "cn_futures_market"
                        ),
                    )
                    for item in market.clarification_options
                ),
                reason=market.intent.reason or "market scope is ambiguous",
            )
        if market.intent.kind is MarketIntentKind.CHEMICAL_SPOT:
            return _adapter_match("chemical_spot_price")
        if market.intent.kind is MarketIntentKind.CN_FUTURES:
            return _adapter_match("cn_futures_market")
        if market.intent.is_market:
            # Other authoritative market scopes (WTI/Brent, A shares, options, etc.)
            # remain owned by D-166 and the existing capability packs in Phase 1.
            return ScenarioResolution(
                status="general",
                source="general",
                reason="market scope is outside the Phase 1 scenario catalog",
            )
        if _CAS_RE.search(text) or _IDENTITY_RE.search(text):
            return _adapter_match("chemical_identity", confidence=0.96)
        if _RESEARCH_RE.search(text):
            if _COMPANY_RE.search(text) and not _MARKET_RESEARCH_RE.search(text):
                return _adapter_match("chemical_company_research", confidence=0.90)
            if _MARKET_RESEARCH_RE.search(text):
                scenario_id = (
                    "chemical_company_research"
                    if _COMPANY_RE.search(text) and _COMPANY_SUBJECT_RE.search(text)
                    else "chemical_market_research"
                )
                return _adapter_match(scenario_id, confidence=0.88)
            if text_has_deep_research_intent(text):
                return _research_scenario_for_text(text, confidence=0.88)
        return self.matcher.match(text)


def _adapter_match(scenario_id: str, confidence: float = 0.99) -> ScenarioResolution:
    return ScenarioResolution(
        status="matched",
        scenario_id=scenario_id,
        source="domain_adapter",
        confidence=confidence,
        reason="deterministic domain adapter",
    )


def _score(text: str, examples: tuple[str, ...]) -> float:
    normalized = re.sub(r"\s+", "", text.lower())
    if not normalized:
        return 0.0
    best = 0.0
    for example in examples:
        candidate = re.sub(r"\s+", "", example.lower())
        if not candidate:
            continue
        if candidate in normalized or normalized in candidate:
            best = max(best, 0.90)
            continue
        text_pairs = {normalized[i : i + 2] for i in range(max(1, len(normalized) - 1))}
        example_pairs = {candidate[i : i + 2] for i in range(max(1, len(candidate) - 1))}
        overlap = len(text_pairs & example_pairs) / max(1, len(example_pairs))
        best = max(best, min(0.85, overlap))
    return round(best, 4)
