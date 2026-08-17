"""HARD STOP C — TurnEngine soft-budget activation vs legacy-inert path."""

from __future__ import annotations

import asyncio

from coworker.config import Config
from coworker.engine import TurnEngine
from coworker.events import EventType
from coworker.execution_profile import RequestRoute, make_execution_profile
from coworker.permissions import PermissionEngine
from coworker.providers import (
    AssistantTurn,
    ModelCapabilities,
    ProviderClient,
    StreamChunk,
    ToolCall,
)
from coworker.tools import ToolRegistry


class RecordingProvider(ProviderClient):
    """Loops tool turns until hard ceiling; records outbound messages + settings."""

    def __init__(self, *, tool_name: str = "read_file"):
        self.calls = 0
        self.outbound: list[list[dict]] = []
        self.settings_seen: list[dict] = []
        self._tool_name = tool_name

    def complete(self, *, model, messages, tools=None, **settings):
        self.calls += 1
        self.outbound.append(messages)
        self.settings_seen.append(dict(settings))
        return AssistantTurn(
            tool_calls=[
                ToolCall(
                    id=f"c{self.calls}",
                    name=self._tool_name,
                    arguments={"path": "a.txt"},
                )
            ],
            finish_reason="tool_calls",
            reasoning="secret thought",
        )

    def capabilities(self, model):
        return ModelCapabilities()

    def stream(self, *, model, messages, tools=None, **settings):
        turn = self.complete(
            model=model, messages=messages, tools=tools, **settings
        )
        yield StreamChunk(reasoning_delta="secret thought")
        yield StreamChunk(turn=turn)


def _engine(tmp_path, provider, *, max_iterations=12, execution_profile=None):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    registry = ToolRegistry()
    import aisuite as ai

    registry.register_all(ai.toolkits.files(root=str(tmp_path), allow_write=True))
    return TurnEngine(
        provider=provider,
        registry=registry,
        permissions=PermissionEngine(workspace_root=tmp_path),
        model="gpt-5.5",
        max_iterations=max_iterations,
        execution_profile=execution_profile,
    )


def _collect(engine, user_input="go"):
    async def _run():
        return [ev async for ev in engine.run(user_input)]

    return asyncio.run(_run())


def test_legacy_path_inert_without_execution_profile(tmp_path):
    """No attached ExecutionProfile → no soft target or phase guidance.

    Explicit routing OFF still proves kill-switch inertness; Step 56 default ON
    does not auto-attach a profile on this engine construction path.
    """
    cfg = Config(request_routing_enabled=False)
    assert cfg.request_routing_enabled is False
    provider = RecordingProvider()
    engine = _engine(tmp_path, provider, max_iterations=3, execution_profile=None)
    events = _collect(engine)
    assert engine.execution_profile is None
    assert engine.target_iterations is None
    assert provider.calls == 3
    assert events[-1].data["status"] == "max_iterations_exceeded"
    joined = "\n".join(str(m) for batch in provider.outbound for m in batch)
    assert "Iteration budget notice" not in joined
    assert "convergence phase" not in joined
    assert "delivery phase" not in joined
    assert any(e.type == EventType.REASONING_DELTA for e in events)


def test_legacy_path_does_not_auto_apply_agent_soft_target(tmp_path):
    cfg = Config()  # agent_target_iterations=32 present but must stay inert
    provider = RecordingProvider()
    engine = _engine(tmp_path, provider, max_iterations=cfg.max_iterations)
    assert engine.max_iterations == 150
    assert engine.target_iterations is None

    class OnceThenStop(RecordingProvider):
        def complete(self, *, model, messages, tools=None, **settings):
            self.calls += 1
            self.outbound.append(messages)
            self.settings_seen.append(dict(settings))
            return AssistantTurn(text="done", finish_reason="stop")

        def stream(self, *, model, messages, tools=None, **settings):
            turn = self.complete(
                model=model, messages=messages, tools=tools, **settings
            )
            yield StreamChunk(turn=turn)

    engine2 = _engine(tmp_path, OnceThenStop(), max_iterations=150)
    _collect(engine2)
    joined = "\n".join(str(m) for batch in engine2.provider.outbound for m in batch)
    assert "Iteration budget notice" not in joined


def test_agent_profile_soft_target_injects_phases_without_early_hard_stop(tmp_path):
    cfg = Config(max_iterations=6, agent_target_iterations=3)
    profile = make_execution_profile(RequestRoute.AGENT, cfg)
    assert profile.target_iterations == 3
    assert profile.max_iterations == 6
    assert profile.emergency_finalization_enabled is True  # Step 59 Config ON
    provider = RecordingProvider()
    engine = _engine(
        tmp_path,
        provider,
        max_iterations=profile.max_iterations,
        execution_profile=profile,
    )
    events = _collect(engine)
    # Soft target is NOT hard stop: run all 6 tool iterations, then one EF call.
    assert provider.calls == 7
    end = events[-1]
    assert end.data["status"] == "max_iterations_exceeded"
    assert end.data["iterations"] == 6
    assert end.data["best_effort_finalized"] is True
    # Converge starts at int(3*0.75)=2; deliver at max(3, 3-4)=2 → both notices appear
    # before hard ceiling.
    noticed = [
        batch
        for batch in provider.outbound
        if any("Iteration budget notice" in str(m) for m in batch)
    ]
    assert noticed, "expected soft-target phase guidance on outbound"
    assert not any(
        "Iteration budget notice" in str(m) for m in engine.messages
    ), "budget guidance must not pollute canonical history"


def test_deep_profile_soft_target_phases(tmp_path):
    cfg = Config(max_iterations=7, deep_research_target_iterations=4)
    profile = make_execution_profile(RequestRoute.DEEP_RESEARCH, cfg)
    assert profile.emergency_finalization_enabled is True  # Step 59 Config ON
    provider = RecordingProvider()
    engine = _engine(
        tmp_path,
        provider,
        max_iterations=profile.max_iterations,
        execution_profile=profile,
    )
    events = _collect(engine)
    assert provider.calls == 8  # 7 hard + 1 emergency finalization
    end = events[-1]
    assert end.data["status"] == "max_iterations_exceeded"
    assert end.data["iterations"] == 7
    assert end.data["best_effort_finalized"] is True
    assert any(
        "Iteration budget notice" in str(m)
        for batch in provider.outbound
        for m in batch
    )


def test_verified_profile_hard_budget_independent(tmp_path):
    cfg = Config(max_iterations=150, verified_max_iterations=3)
    profile = make_execution_profile(RequestRoute.VERIFIED, cfg)
    assert profile.max_iterations == 3
    assert profile.emergency_finalization_enabled is True  # Step 59 Config ON
    provider = RecordingProvider()
    engine = _engine(
        tmp_path,
        provider,
        max_iterations=profile.max_iterations,
        execution_profile=profile,
    )
    events = _collect(engine)
    assert provider.calls == 4  # 3 hard + 1 emergency finalization
    end = events[-1]
    assert end.data["status"] == "max_iterations_exceeded"
    assert end.data["iterations"] == 3
    assert end.data["best_effort_finalized"] is True
    # VERIFIED has no soft-target phase guidance
    assert not any(
        "Iteration budget notice" in str(m)
        for batch in provider.outbound
        for m in batch
    )


def test_fast_chat_profile_suppresses_reasoning_delta(tmp_path):
    cfg = Config()
    profile = make_execution_profile(RequestRoute.FAST_CHAT, cfg)
    assert profile.reasoning_mode == "off"

    class ReasonThenStop(RecordingProvider):
        def complete(self, *, model, messages, tools=None, **settings):
            self.calls += 1
            self.outbound.append(messages)
            self.settings_seen.append(dict(settings))
            return AssistantTurn(
                text="hi", finish_reason="stop", reasoning="hidden"
            )

        def stream(self, *, model, messages, tools=None, **settings):
            turn = self.complete(
                model=model, messages=messages, tools=tools, **settings
            )
            yield StreamChunk(reasoning_delta="hidden")
            yield StreamChunk(text_delta="hi")
            yield StreamChunk(turn=turn)

    provider = ReasonThenStop()
    engine = _engine(
        tmp_path,
        provider,
        max_iterations=profile.max_iterations,
        execution_profile=profile,
    )
    events = _collect(engine)
    assert EventType.REASONING_DELTA not in [e.type for e in events]
    assert any(e.type == EventType.ASSISTANT_DELTA for e in events)
