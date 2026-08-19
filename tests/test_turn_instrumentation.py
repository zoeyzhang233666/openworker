"""Section 65 step 48: turn/provider instrumentation (no secrets / no full prompts)."""

from __future__ import annotations

import json
import logging

from coworker.config import Config
from coworker.execution_profile import RequestRoute, make_execution_profile
from coworker.request_router import RouteDecision, RouterContext, route_request
from coworker.tool_policy import TurnToolPolicy
from coworker.turn_instrumentation import (
    FORBIDDEN_INSTRUMENTATION_KEYS,
    build_model_call_snapshot,
    build_provider_call_shape_snapshot,
    build_provider_stream_snapshot,
    build_turn_snapshot,
    emit_instrumentation,
    snapshot_from_route_decision,
)


def test_turn_snapshot_from_route_decision_includes_guard_flags():
    decision = RouteDecision(
        route=RequestRoute.AGENT,
        source="pending_state",
        reason="pending interaction / durable resume / stop outranks router",
        tool_policy=TurnToolPolicy(no_tools=True, no_search=True, no_external_network=True),
        classifier_calls=0,
        allowed_tool_names=("read_file",),
    )
    snap = snapshot_from_route_decision(decision)
    assert snap["route"] == "agent"
    assert snap["route_source"] == "pending_state"
    assert snap["pending_state_guard_hit"] is True
    assert snap["product_action_gate_hit"] is False
    assert snap["legacy_fallback_used"] is False
    assert snap["tool_policy_no_tools"] is True
    assert snap["tool_policy_no_search"] is True
    assert snap["tool_policy_no_external_network"] is True
    assert snap["classifier_used"] is False
    assert snap["allowed_tool_count"] == 1


def test_turn_snapshot_marks_legacy_fallback_and_product_action():
    fb = RouteDecision(
        route=RequestRoute.AGENT,
        source="legacy_fallback",
        reason="uncertain; preserve legacy tool capability",
    )
    assert snapshot_from_route_decision(fb)["legacy_fallback_used"] is True

    pa = RouteDecision(
        route=RequestRoute.AGENT,
        source="product_action",
        reason="product action detected",
    )
    assert snapshot_from_route_decision(pa)["product_action_gate_hit"] is True


def test_build_turn_snapshot_with_profile_and_projection_mode():
    cfg = Config()
    profile = make_execution_profile(RequestRoute.VERIFIED, cfg)
    snap = build_turn_snapshot(
        route_decision=None,
        execution_profile=profile,
        tool_projection_enabled=False,
        tools_enabled=True,
        allowed_tool_count=3,
        reasoning_mode=profile.reasoning_mode,
        router_elapsed_ms=12.5,
    )
    assert snap["profile_max_iterations"] == profile.max_iterations
    assert snap["tools_enabled"] is True
    assert snap["allowed_tool_count"] == 3
    assert snap["tool_projection_mode"] == "legacy_full"
    assert snap["router_elapsed_ms"] == 12.5


def test_model_and_provider_snapshots_are_compact():
    model = build_model_call_snapshot(
        iteration=2,
        budget_phase="converge",
        elapsed_ms=40.0,
        first_visible_delta_ms=8.0,
        stream_attempts=1,
        tool_count=2,
        finish_reason="tool_calls",
    )
    assert model["iteration"] == 2
    assert model["budget_phase"] == "converge"
    assert model["tool_count"] == 2

    prov = build_provider_stream_snapshot(
        stream_attempt=1,
        stream_mode="compat_buffered",
        provider_progress_seen=True,
        visible_output_seen=False,
        tool_progress_seen=True,
        transport_failure_type=None,
        retried=False,
        fallback_used=False,
        textual_tool_salvage_used=True,
    )
    assert prov["stream_mode"] == "compat_buffered"
    assert prov["textual_tool_salvage_used"] is True

    shape = build_provider_call_shape_snapshot(
        prompt_profile="fast",
        prompt_char_count=900,
        prompt_token_estimate=300,
        prompt_section_count=3,
        schema_count=0,
        schema_bytes=0,
        skill_count=0,
        reasoning_mode="off",
        show_reasoning=True,
        projected_session=True,
    )
    assert shape["prompt_profile"] == "fast"
    assert shape["schema_count"] == 0
    assert shape["skill_count"] == 0
    assert shape["show_reasoning"] is True


def test_emit_instrumentation_redacts_forbidden_keys(caplog):
    payload = {
        "route": "fast_chat",
        "api_key": "sk-secret",
        "prompt": "full user prompt must never appear",
        "messages": [{"role": "user", "content": "secret"}],
        "tool_result": {"body": "huge"},
    }
    with caplog.at_level(logging.INFO, logger="coworker.turn_instrumentation"):
        emit_instrumentation("turn", payload)
    assert "chemclaw.perf" in caplog.text
    assert "sk-secret" not in caplog.text
    assert "full user prompt" not in caplog.text
    logged = None
    for rec in caplog.records:
        if "chemclaw.perf" in rec.getMessage():
            # message format: chemclaw.perf <event> <json>
            parts = rec.getMessage().split(" ", 2)
            logged = json.loads(parts[2])
            break
    assert logged is not None
    for bad in FORBIDDEN_INSTRUMENTATION_KEYS:
        assert bad not in logged
    assert logged["route"] == "fast_chat"


def test_router_off_snapshot_is_emptyish():
    cfg = Config(request_routing_enabled=False)
    decision = route_request("你好", config=cfg, context=RouterContext())
    assert decision is None
    snap = snapshot_from_route_decision(decision)
    assert snap["route"] is None
    assert snap["classifier_used"] is False
