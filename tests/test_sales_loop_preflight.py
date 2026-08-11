"""Sales-loop program-side preflight before UI smoke (D-091—D-110 tools on engine)."""

from __future__ import annotations

from coworker.agent import build_engine
from coworker.agents import chat_agent
from coworker.personas.registry import PersonaRegistry
from coworker.providers import AssistantTurn
from coworker.providers.base import ModelCapabilities

SALES_LOBSTERS = (
    "export-sales-lobster",
    "domestic-sales-lobster",
    "opportunity-radar-lobster",
    "export-engagement-lobster",
)

# Platform tools always registered on the default engine (connectors like HubSpot
# are portal-gated and intentionally absent until connected).
REQUIRED_TOOLS = (
    "lookup_chemical_identity",
    "lookup_legal_entity",
    "validate_eu_vat",
    "lookup_fx_rate",
    "lookup_wikipedia",
    "search_huagongshe",
    "lookup_huagongshe_chemical",
    "validate_huagongshe_reaction",
    "create_huagongshe_reaction",
    "calculate_quote",
    "format_lead_list",
    "search_tenders",
    "lookup_trade_flow",
    "search_sam_opportunities",
    "filter_customs_importers",
)


class _Stub:
    def complete(self, **_kw):
        return AssistantTurn()

    def capabilities(self, _model):
        return ModelCapabilities()


def test_four_sales_lobsters_discoverable_and_disabled_by_default(tmp_path):
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")
    assert registry.default_id() == "cowork"
    for pid in SALES_LOBSTERS:
        assert pid in registry.ids(), pid
        assert registry.is_enabled(pid) is False, pid


def test_sales_loop_tools_registered_on_default_engine():
    eng = build_engine(agent=chat_agent(), provider=_Stub())
    names = set(eng.registry.names())
    missing = [n for n in REQUIRED_TOOLS if n not in names]
    assert missing == [], f"missing tools: {missing}"
