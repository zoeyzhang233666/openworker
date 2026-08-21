"""Resolve Scenario requirements into the smallest live Tool allowlist."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..scenarios.models import ScenarioResolution
from ..scenarios.registry import ScenarioRegistry, builtin_scenario_registry
from ..tools.registry import ToolDescriptor
from .models import CapabilityPlan, CapabilityProvider, CapabilityResolution
from .registry import CapabilityRegistry, builtin_capability_registry


class CapabilityResolver:
    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        scenarios: ScenarioRegistry | None = None,
    ) -> None:
        self.registry = registry or builtin_capability_registry()
        self.scenarios = scenarios or builtin_scenario_registry()
        self.validate_references()

    def validate_references(self) -> None:
        for scenario in self.scenarios.list():
            for capability_id in (*scenario.required_capabilities, *scenario.optional_capabilities):
                if self.registry.get(capability_id) is None:
                    raise ValueError(
                        f"scenario {scenario.id} references unknown capability {capability_id}"
                    )

    def resolve(
        self,
        resolution: ScenarioResolution,
        *,
        text: str,
        tools: Iterable[ToolDescriptor],
        configured_tool_names: Iterable[str] = (),
    ) -> CapabilityPlan:
        descriptors = tuple(tools)
        live_names = {tool.name for tool in descriptors}
        configured = set(configured_tool_names)
        if resolution.status == "ambiguous":
            result = self._resolve_one(
                "interaction.clarify", True, descriptors, live_names, configured
            )
            return CapabilityPlan(
                resolutions=(result,),
                selected_tool_names=result.tool_names,
                blocked_tool_names=tuple(sorted(live_names - set(result.tool_names))),
                required_ready=result.status == "ready",
            )
        if resolution.status != "matched" or not resolution.scenario_id:
            return CapabilityPlan()

        scenario = self.scenarios.require(resolution.scenario_id)
        required_ids = list(scenario.required_capabilities)
        optional_ids = list(scenario.optional_capabilities)
        if scenario.id == "cn_futures_market" and _wants_ohlc(text):
            required_ids = ["market.ohlc.cn_futures"]
            optional_ids = []
        elif scenario.id == "cn_futures_market":
            # A quote request must expose one target Tool. OHLC is an alternative
            # contract chosen only when the user asks for a trend or chart.
            optional_ids = []

        items: list[CapabilityResolution] = []
        for capability_id in required_ids:
            items.append(
                self._resolve_one(capability_id, True, descriptors, live_names, configured)
            )
        for capability_id in optional_ids:
            item = self._resolve_one(
                capability_id, False, descriptors, live_names, configured
            )
            if item.status != "unavailable":
                items.append(item)
        required_ready = all(not item.required or item.status == "ready" for item in items)
        selected = tuple(
            dict.fromkeys(name for item in items for name in item.tool_names)
        ) if required_ready else ()
        return CapabilityPlan(
            resolutions=tuple(items),
            selected_tool_names=selected,
            blocked_tool_names=tuple(sorted(live_names - set(selected))) if required_ready else tuple(sorted(live_names)),
            fallback=scenario.fallback_policy if not required_ready else (),
            required_ready=required_ready,
        )

    def _resolve_one(
        self,
        capability_id: str,
        required: bool,
        tools: tuple[ToolDescriptor, ...],
        live_names: set[str],
        configured: set[str],
    ) -> CapabilityResolution:
        spec = self.registry.require(capability_id)
        for provider in sorted(spec.providers, key=lambda item: -item.priority):
            names = _provider_tools(provider, tools)
            if names:
                return CapabilityResolution(
                    capability_id=capability_id,
                    required=required,
                    status="ready",
                    provider_id=provider.provider_id,
                    tool_names=names,
                    reason="provider tool is registered",
                )
            configured_match = _configured_match(provider, configured)
            if configured_match:
                return CapabilityResolution(
                    capability_id=capability_id,
                    required=required,
                    status="configured",
                    provider_id=provider.provider_id,
                    reason="provider is configured but not connected",
                )
        return CapabilityResolution(
            capability_id=capability_id,
            required=required,
            status="unavailable",
            reason="no matching provider tool is available",
        )


def _provider_tools(
    provider: CapabilityProvider, tools: tuple[ToolDescriptor, ...]
) -> tuple[str, ...]:
    if provider.binding_kind == "tool":
        return tuple(tool.name for tool in tools if tool.name == provider.selector)
    server, remote = provider.selector.split(":", 1)
    normalized_server = re.sub(r"[-.\s]+", "_", server.lower())
    matches: list[str] = []
    for tool in tools:
        if not tool.name.startswith("mcp__") or "__" not in tool.name[5:]:
            continue
        tool_server, tool_remote = tool.name[5:].rsplit("__", 1)
        server_match = re.sub(r"[-.\s]+", "_", tool_server.lower()) == normalized_server
        capability_match = any(
            re.sub(r"[-.\s]+", "_", value.lower()) == normalized_server
            for value in tool.capabilities
        )
        if tool_remote.lower() == remote.lower() and (server_match or capability_match):
            matches.append(tool.name)
    return tuple(dict.fromkeys(matches))


def _configured_match(provider: CapabilityProvider, configured: set[str]) -> bool:
    if provider.binding_kind == "tool":
        return provider.selector in configured
    server = provider.selector.split(":", 1)[0].lower().replace("-", "_")
    return any(server in name.lower().replace("-", "_") for name in configured)


def _wants_ohlc(text: str) -> bool:
    return bool(re.search(r"(走势|日线|周线|月线|K\s*线|蜡烛|OHLC|trend|chart)", text, re.I))
