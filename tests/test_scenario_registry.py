from __future__ import annotations

import pytest

from coworker.capabilities import CapabilityResolver, builtin_capability_registry
from coworker.scenarios import ScenarioRegistry, ScenarioSpec, builtin_scenario_registry


def test_builtin_scenario_and_capability_references_are_complete() -> None:
    scenarios = builtin_scenario_registry()
    capabilities = builtin_capability_registry()
    assert {item.id for item in scenarios.list()} == {
        "chemical_spot_price",
        "cn_futures_market",
        "chemical_market_report",
        "chemical_identity",
        "chemical_company_research",
        "chemical_market_research",
    }
    CapabilityResolver(capabilities, scenarios).validate_references()


def test_registry_rejects_duplicate_scenario_ids() -> None:
    item = ScenarioSpec(
        id="same",
        category="test",
        title="Same",
        description="same",
    )
    with pytest.raises(ValueError, match="duplicate scenario id"):
        ScenarioRegistry((item, item))


def test_scenario_models_are_frozen_and_forbid_extra_fields() -> None:
    item = builtin_scenario_registry().require("chemical_identity")
    with pytest.raises(Exception):
        item.title = "changed"  # type: ignore[misc]
    with pytest.raises(Exception):
        ScenarioSpec(
            id="bad",
            category="test",
            title="Bad",
            description="bad",
            unexpected=True,  # type: ignore[call-arg]
        )
