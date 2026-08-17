"""HARD STOP C — reasoning / soft-budget plumbing + legacy-inert guarantees."""

from __future__ import annotations

from coworker.config import Config, load_config
from coworker.execution_profile import (
    BudgetPhase,
    RequestRoute,
    apply_reasoning_mode_settings,
    budget_guidance_text,
    budget_phase_for_iteration,
    budget_thresholds,
    make_execution_profile,
)


def test_config_keeps_max_iterations_hard_ceiling_and_soft_targets():
    cfg = Config()
    assert cfg.max_iterations == 150
    assert cfg.agent_target_iterations == 32
    assert cfg.deep_research_target_iterations == 50
    assert cfg.verified_max_iterations == 6
    assert cfg.request_routing_enabled is True  # Section 65 Step 56 candidate ON
    assert cfg.emergency_finalization_enabled is True  # Section 65 Step 59 candidate ON


def test_config_loads_budget_overrides_from_toml(tmp_path):
    g = tmp_path / "global.toml"
    g.write_text(
        "max_iterations = 60\n"
        "agent_target_iterations = 40\n"
        "deep_research_target_iterations = 55\n"
        "verified_max_iterations = 8\n"
    )
    cfg = load_config(global_path=g)
    assert cfg.max_iterations == 60
    assert cfg.agent_target_iterations == 40
    assert cfg.deep_research_target_iterations == 55
    assert cfg.verified_max_iterations == 8


def test_soft_targets_cap_to_user_max_iterations():
    cfg = Config(max_iterations=24)
    agent = make_execution_profile(RequestRoute.AGENT, cfg)
    deep = make_execution_profile(RequestRoute.DEEP_RESEARCH, cfg)
    assert agent.max_iterations == 24
    assert agent.target_iterations == 24
    assert deep.max_iterations == 24
    assert deep.target_iterations == 24


def test_agent_and_deep_soft_targets_do_not_replace_hard_ceiling():
    cfg = Config()
    agent = make_execution_profile(RequestRoute.AGENT, cfg)
    deep = make_execution_profile(RequestRoute.DEEP_RESEARCH, cfg)
    assert agent.max_iterations == 150
    assert agent.target_iterations == 32
    assert deep.max_iterations == 150
    assert deep.target_iterations == 50
    assert agent.emergency_finalization_enabled is True  # mirrors Config Step 59 ON
    assert deep.emergency_finalization_enabled is True


def test_verified_uses_independent_hard_budget():
    cfg = Config()
    verified = make_execution_profile(RequestRoute.VERIFIED, cfg)
    assert verified.max_iterations == 6
    assert verified.target_iterations is None
    assert verified.budget_guidance_enabled is False

    cfg2 = Config(max_iterations=4, verified_max_iterations=8)
    verified2 = make_execution_profile(RequestRoute.VERIFIED, cfg2)
    assert verified2.max_iterations == 4


def test_budget_phases_driven_by_soft_target_not_hard_ceiling():
    converge_at, deliver_at = budget_thresholds(hard=150, target=32)
    assert converge_at == 24
    assert deliver_at == 28
    assert budget_phase_for_iteration(1, hard=150, target=32) == BudgetPhase.EXPLORE
    assert budget_phase_for_iteration(24, hard=150, target=32) == BudgetPhase.CONVERGE
    assert budget_phase_for_iteration(28, hard=150, target=32) == BudgetPhase.DELIVER
    assert budget_phase_for_iteration(33, hard=150, target=32) == BudgetPhase.EXTENDED

    converge_at, deliver_at = budget_thresholds(hard=150, target=50)
    assert converge_at == 37
    assert deliver_at == 46


def test_budget_guidance_text_only_for_converge_deliver_extended():
    assert budget_guidance_text(BudgetPhase.EXPLORE) is None
    converge = budget_guidance_text(BudgetPhase.CONVERGE)
    deliver = budget_guidance_text(BudgetPhase.DELIVER)
    assert converge and "convergence phase" in converge
    assert deliver and "delivery phase" in deliver
    assert "Iteration budget notice" in converge
    hard_warn = budget_guidance_text(
        BudgetPhase.DELIVER, iteration=149, hard=150
    )
    assert hard_warn and "hard-ceiling" in hard_warn


def test_reasoning_mode_off_sets_effort_none_when_supported():
    patched = apply_reasoning_mode_settings(
        {"temperature": 0.2},
        "off",
        supports_disable_reasoning=True,
    )
    assert patched["reasoning_effort"] == "none"
    untouched = apply_reasoning_mode_settings(
        {"temperature": 0.2},
        "off",
        supports_disable_reasoning=False,
    )
    assert "reasoning_effort" not in untouched
