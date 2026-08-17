"""Provider-visible tool schema projection (HARD STOP E / Section 65 Steps 34–38).

Filters outbound schemas only — never unregister/rebuild the runtime ToolRegistry.
Built-in default tool_projection_enabled is candidate ON (Step 57); callers may override.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterable, Optional

from .execution_profile import ExecutionProfile, RequestRoute
from .tool_policy import TurnToolPolicy, filter_tool_names, tool_allowed_under_policy

if TYPE_CHECKING:
    from .tools.registry import ToolRegistry


def select_verified_tool_names(
    text: str, available: Iterable[str]
) -> tuple[str, ...] | None:
    """Pick a minimal VERIFIED subset when safe; None → keep full legacy set.

    Conservative: if no targeted match intersects the registry, return None so
    capabilities are not silently emptied.
    """
    avail = set(available)
    t = (text or "").strip()
    low = t.lower()
    candidates: list[str] = []

    if re.search(
        r"(\bcas\b|cas号|cas\s*号|inchi|smiles|分子式|闪点|熔点|沸点|密度|"
        r"什么化学品|是什么化合物|chemical identity|"
        r"\b\d{2,7}-\d{2}-\d\b)",
        t,
        re.I,
    ):
        candidates.append("lookup_chemical_identity")

    if re.search(r"(汇率|fx\b|exchange rate|usd/?cny|欧元汇率)", t, re.I):
        candidates.append("lookup_fx_rate")

    if re.search(r"(\bvat\b|增值税号|eu\s*vat)", t, re.I):
        candidates.append("validate_eu_vat")

    if re.search(
        r"(企业主体|法定主体|gleif|lei\b|公司注册|legal entity|lei code)",
        t,
        re.I,
    ):
        candidates.append("lookup_legal_entity")

    if re.search(r"(维基|wikipedia)", t, re.I):
        candidates.append("lookup_wikipedia")

    if re.search(
        r"(法规|reach|tsca|危险分类|禁限用|regulation|regulatory)",
        t,
        re.I,
    ):
        for name in (
            "lookup_chemical_identity",
            "web_search",
            "web_fetch",
        ):
            if name not in candidates:
                candidates.append(name)

    if re.search(r"(价格|price|产能|current price)", t, re.I) and not candidates:
        for name in ("web_search", "web_fetch", "lookup_fx_rate"):
            if name not in candidates:
                candidates.append(name)

    # Generic "verify current fact" fallback when risk gate fired but no niche match:
    # prefer chemical identity + web_search if present; else None (legacy full).
    if not candidates and (
        re.search(r"(今天|最新|当前|实时|currently|today)", t, re.I)
        or "exact" in low
    ):
        for name in ("web_search", "web_fetch", "lookup_chemical_identity"):
            if name in avail and name not in candidates:
                candidates.append(name)

    selected = tuple(n for n in candidates if n in avail)
    if not selected:
        return None
    # Preserve deterministic order while unique.
    seen: set[str] = set()
    ordered: list[str] = []
    for n in selected:
        if n not in seen:
            seen.add(n)
            ordered.append(n)
    return tuple(ordered)


def project_provider_visible_schemas(
    registry: "ToolRegistry",
    *,
    tool_projection_enabled: bool,
    profile: Optional[ExecutionProfile],
    tool_policy: Optional[TurnToolPolicy] = None,
    mandatory_tool_names: Optional[Iterable[str]] = None,
) -> list[dict] | None:
    """Return provider-visible OpenAI tool schemas, or None for tools=None.

    Kill switch OFF → legacy full registry exposure (still agent/session registered set).
    Does not mutate registry.
    """
    all_schemas = list(registry.schemas())
    if not tool_projection_enabled:
        return all_schemas or None

    if profile is None:
        return all_schemas or None

    policy = tool_policy or TurnToolPolicy()
    mandatory = {n for n in (mandatory_tool_names or ()) if registry.get(n) is not None}

    # Pure FAST_CHAT / KNOWLEDGE: API-level tools=None unless mandatory continuation tools.
    if not profile.tools_enabled or profile.route in (
        RequestRoute.FAST_CHAT,
        RequestRoute.KNOWLEDGE,
    ):
        if not mandatory:
            return None
        names = sorted(mandatory)
        return _schemas_for_names(registry, names) or None

    registered = list(registry.names())

    if profile.allowed_tool_names is None:
        # Conservative AGENT/DEEP (and uncertain VERIFIED): full legacy set.
        candidate_names = list(registered)
    else:
        allowed = set(profile.allowed_tool_names)
        candidate_names = [n for n in registered if n in allowed]

    # Merge mandatory capabilities for this turn.
    for name in mandatory:
        if name not in candidate_names:
            candidate_names.append(name)

    # ToolPolicy final filtering (unified classify_tool / network_scope).
    if policy.no_tools:
        kept = [n for n in candidate_names if n in mandatory]
    else:
        kept = filter_tool_names(candidate_names, policy)
        # Mandatory tools still respect hard no_tools above; otherwise ensure present
        # when policy allows them.
        for name in mandatory:
            if name not in kept and tool_allowed_under_policy(name, policy):
                kept.append(name)

    if not kept:
        return None
    return _schemas_for_names(registry, kept) or None


def _schemas_for_names(registry: "ToolRegistry", names: Iterable[str]) -> list[dict]:
    out: list[dict] = []
    for name in names:
        spec = registry.get(name)
        if spec is not None:
            out.append(spec.schema)
    return out
