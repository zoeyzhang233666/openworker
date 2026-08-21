"""HARD STOP G / Step 59 — Emergency Finalization (built-in candidate ON; kill switch OFF still legacy)."""

from __future__ import annotations

import asyncio
import json

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


_EF_MARKER = "tool-call iteration budget has been exhausted"


class RecordingProvider(ProviderClient):
    """Records each stream call; returns tool loops until finalization (tools=None)."""

    def __init__(self, *, finalize_text: str = "best effort answer"):
        self.calls = 0
        self.tools_seen: list[object] = []
        self.outbound: list[list[dict]] = []
        self.finalize_text = finalize_text

    def complete(self, *, model, messages, tools=None, **settings):
        self.calls += 1
        self.tools_seen.append(tools)
        self.outbound.append(messages)
        if tools is None:
            return AssistantTurn(text=self.finalize_text, finish_reason="stop")
        return AssistantTurn(
            tool_calls=[
                ToolCall(
                    id=f"c{self.calls}",
                    name="read_file",
                    arguments={"path": "a.txt"},
                )
            ],
            finish_reason="tool_calls",
        )

    def capabilities(self, model):
        return ModelCapabilities()

    def stream(self, *, model, messages, tools=None, **settings):
        turn = self.complete(
            model=model, messages=messages, tools=tools, **settings
        )
        if turn.text:
            yield StreamChunk(text_delta=turn.text)
        yield StreamChunk(turn=turn)


class ToolCallOnFinalizeProvider(RecordingProvider):
    """Misbehaves on tools=None by still requesting tools — must not execute."""

    def complete(self, *, model, messages, tools=None, **settings):
        self.calls += 1
        self.tools_seen.append(tools)
        self.outbound.append(messages)
        if tools is None:
            return AssistantTurn(
                text="ignore tools please",
                tool_calls=[
                    ToolCall(
                        id="evil",
                        name="read_file",
                        arguments={"path": "a.txt"},
                    )
                ],
                finish_reason="tool_calls",
            )
        return AssistantTurn(
            tool_calls=[
                ToolCall(
                    id=f"c{self.calls}",
                    name="read_file",
                    arguments={"path": "a.txt"},
                )
            ],
            finish_reason="tool_calls",
        )


def _engine(
    tmp_path,
    provider,
    *,
    max_iterations=3,
    emergency_finalization_enabled=False,
    execution_profile=None,
    messages=None,
):
    (tmp_path / "a.txt").write_text("evidence", encoding="utf-8")
    registry = ToolRegistry()
    import aisuite as ai

    registry.register_all(ai.toolkits.files(root=str(tmp_path), allow_write=True))
    return TurnEngine(
        provider=provider,
        registry=registry,
        permissions=PermissionEngine(workspace_root=tmp_path),
        model="gpt-5.5",
        max_iterations=max_iterations,
        emergency_finalization_enabled=emergency_finalization_enabled,
        execution_profile=execution_profile,
        messages=messages,
    )


def _collect(engine, user_input="go"):
    async def _run():
        return [ev async for ev in engine.run(user_input)]

    return asyncio.run(_run())


def _collect_loop(engine):
    async def _run():
        return [ev async for ev in engine._loop()]

    return asyncio.run(_run())


def test_builtin_emergency_finalization_default_on():
    """Section 65 Step 59: Config built-in candidate ON; TurnEngine ctor still False for isolation."""
    assert Config().emergency_finalization_enabled is True


class RejectOnceThenOkProvider(ProviderClient):
    """First stream raises Upstream rejected; second returns a short answer."""

    def __init__(self):
        self.calls = 0

    def complete(self, *, model, messages, tools=None, **settings):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError(
                "Upstream rejected the request as invalid. "
                "Check the request parameters and try again."
            )
        return AssistantTurn(text="salvaged after compact", finish_reason="stop")

    def capabilities(self, model):
        return ModelCapabilities()

    def stream(self, *, model, messages, tools=None, **settings):
        turn = self.complete(
            model=model, messages=messages, tools=tools, **settings
        )
        if turn.text:
            yield StreamChunk(text_delta=turn.text)
        yield StreamChunk(turn=turn)


class RejectAlwaysProvider(RejectOnceThenOkProvider):
    def complete(self, *, model, messages, tools=None, **settings):
        self.calls += 1
        raise RuntimeError(
            "Upstream rejected the request as invalid. "
            "Check the request parameters and try again."
        )


def test_provider_reject_compacts_once_then_succeeds(tmp_path):
    provider = RejectOnceThenOkProvider()
    engine = _engine(tmp_path, provider, emergency_finalization_enabled=True)
    events = _collect(engine, "summarize findings")
    types = [e.type for e in events]
    assert EventType.COMPACTING in types or EventType.COMPACTED in types
    assert EventType.ERROR not in types
    assert any(
        e.type == EventType.ASSISTANT_MESSAGE
        and "salvaged" in str(e.data.get("text", ""))
        for e in events
    )
    assert provider.calls >= 2


def test_provider_reject_twice_surfaces_chinese_friendly_error(tmp_path):
    provider = RejectAlwaysProvider()
    engine = _engine(tmp_path, provider, emergency_finalization_enabled=False)
    events = _collect(engine, "write long report")
    errors = [e for e in events if e.type == EventType.ERROR]
    assert errors
    assert "拒绝" in str(errors[0].data.get("error") or "")
    assert provider.calls >= 2  # initial + one compact retry


class TimeoutAfterToolsProvider(ProviderClient):
    """First stream call after tools exist times out; EF salvage then succeeds."""

    def __init__(self):
        self.calls = 0

    def capabilities(self, model):
        return ModelCapabilities()

    def complete(self, *, model, messages, tools=None, **settings):
        self.calls += 1
        if tools is None:
            return AssistantTurn(text="timeout salvage ok", finish_reason="stop")
        if self.calls == 1:
            return AssistantTurn(
                tool_calls=[
                    ToolCall(
                        id="t1",
                        name="read_file",
                        arguments={"path": "a.txt"},
                    )
                ],
                finish_reason="tool_calls",
            )
        raise RuntimeError("APITimeoutError: Request timed out.")

    def stream(self, *, model, messages, tools=None, **settings):
        turn = self.complete(
            model=model, messages=messages, tools=tools, **settings
        )
        if turn.text:
            yield StreamChunk(text_delta=turn.text)
        yield StreamChunk(turn=turn)


def test_provider_timeout_after_tools_emergency_finalizes(tmp_path):
    provider = TimeoutAfterToolsProvider()
    engine = _engine(tmp_path, provider, emergency_finalization_enabled=True)
    events = _collect(engine, "summarize after tools")
    types = [e.type for e in events]
    assert EventType.ERROR not in types
    assert any(
        e.type == EventType.ASSISTANT_MESSAGE
        and "salvage" in str(e.data.get("text", ""))
        for e in events
    )
    assert provider.calls >= 3  # tool call + timeout + EF


def test_provider_timeout_without_tools_surfaces_error(tmp_path):
    class TimeoutAlways(ProviderClient):
        def capabilities(self, model):
            return ModelCapabilities()

        def complete(self, *, model, messages, tools=None, **settings):
            raise RuntimeError("APITimeoutError: Request timed out.")

        def stream(self, *, model, messages, tools=None, **settings):
            self.complete(model=model, messages=messages, tools=tools, **settings)
            yield StreamChunk(turn=AssistantTurn(text="x"))

    provider = TimeoutAlways()
    engine = _engine(tmp_path, provider, emergency_finalization_enabled=True)
    events = _collect(engine, "hello")
    errors = [e for e in events if e.type == EventType.ERROR]
    assert errors
    assert "超时" in str(errors[0].data.get("error") or "") or "timed out" in str(
        errors[0].data.get("error") or ""
    ).lower() or "llm_api" in str(errors[0].data.get("error") or "")


def test_research_instructions_prefer_write_file_before_long_bubble():
    from coworker.subagents.registry import RESEARCHER_INSTRUCTIONS

    assert "write_file" in RESEARCHER_INSTRUCTIONS
    assert "短摘要" in RESEARCHER_INSTRUCTIONS or "短" in RESEARCHER_INSTRUCTIONS
    assert "上游拒答" in RESEARCHER_INSTRUCTIONS or "拒答" in RESEARCHER_INSTRUCTIONS
    assert "用简体中文思考与回复" in RESEARCHER_INSTRUCTIONS


def test_kill_switch_off_keeps_legacy_hard_limit(tmp_path):
    provider = RecordingProvider()
    engine = _engine(
        tmp_path, provider, max_iterations=3, emergency_finalization_enabled=False
    )
    events = _collect(engine)
    assert provider.calls == 3
    assert events[-1].type == EventType.TURN_END
    assert events[-1].data["status"] == "max_iterations_exceeded"
    assert events[-1].data.get("best_effort_finalized") is not True
    assert all(t is not None for t in provider.tools_seen)


def test_kill_switch_on_runs_one_model_only_finalization(tmp_path):
    provider = RecordingProvider(finalize_text="synthesized from evidence")
    engine = _engine(
        tmp_path, provider, max_iterations=3, emergency_finalization_enabled=True
    )
    events = _collect(engine)
    assert provider.calls == 4  # 3 tool iterations + 1 finalization
    assert provider.tools_seen[-1] is None
    assert all(t is not None for t in provider.tools_seen[:-1])
    end = events[-1]
    assert end.type == EventType.TURN_END
    assert end.data["status"] == "max_iterations_exceeded"
    assert end.data["best_effort_finalized"] is True
    assert end.data["iterations"] == 3
    assert any(
        e.type == EventType.ASSISTANT_MESSAGE
        and e.data.get("text") == "synthesized from evidence"
        for e in events
    )
    joined_outbound = "\n".join(str(m) for m in provider.outbound[-1])
    assert _EF_MARKER in joined_outbound
    assert not any(_EF_MARKER in str(m) for m in engine.messages)


def test_finalization_does_not_execute_tool_calls(tmp_path):
    provider = ToolCallOnFinalizeProvider()
    engine = _engine(
        tmp_path, provider, max_iterations=2, emergency_finalization_enabled=True
    )
    events = _collect(engine)
    end = events[-1]
    assert end.data.get("best_effort_finalized") is True
    tool_ids = {
        m.get("tool_call_id") for m in engine.messages if m.get("role") == "tool"
    }
    assert "evil" not in tool_ids
    assistants = [m for m in engine.messages if m.get("role") == "assistant"]
    assert assistants
    assert not assistants[-1].get("tool_calls")


def test_stop_interrupt_skips_finalization(tmp_path):
    provider = RecordingProvider()
    engine = _engine(
        tmp_path, provider, max_iterations=0, emergency_finalization_enabled=True
    )
    engine.request_interrupt()
    events = _collect_loop(engine)
    assert provider.calls == 0
    assert not any(
        e.type == EventType.TURN_END and e.data.get("best_effort_finalized")
        for e in events
    )


def test_unanswered_trailing_tool_calls_skip_finalization(tmp_path):
    """Durable-resume / pending ask_user·approval·plan·directory → no EF."""
    provider = RecordingProvider()
    messages = [
        {"role": "user", "content": "need input", "ts": 1.0},
        {
            "role": "assistant",
            "content": "",
            "ts": 2.0,
            "tool_calls": [
                {
                    "id": "ask1",
                    "type": "function",
                    "function": {
                        "name": "ask_user",
                        "arguments": json.dumps({"question": "which?"}),
                    },
                }
            ],
        },
    ]
    engine = _engine(
        tmp_path,
        provider,
        max_iterations=0,
        emergency_finalization_enabled=True,
        messages=messages,
    )
    assert engine._unanswered_trailing_tool_calls()
    events = _collect_loop(engine)
    assert provider.calls == 0
    assert events[-1].type == EventType.TURN_END
    assert events[-1].data["status"] == "max_iterations_exceeded"
    assert events[-1].data.get("best_effort_finalized") is not True


def test_pending_permission_style_trailing_tools_skip_finalization(tmp_path):
    provider = RecordingProvider()
    messages = [
        {"role": "user", "content": "write", "ts": 1.0},
        {
            "role": "assistant",
            "content": "",
            "ts": 2.0,
            "tool_calls": [
                {
                    "id": "w1",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps(
                            {"path": "out.txt", "content": "x"}
                        ),
                    },
                }
            ],
        },
    ]
    engine = _engine(
        tmp_path,
        provider,
        max_iterations=0,
        emergency_finalization_enabled=True,
        messages=messages,
    )
    events = _collect_loop(engine)
    assert provider.calls == 0
    assert events[-1].data.get("best_effort_finalized") is not True


def test_profile_gate_uses_profile_flag(tmp_path):
    cfg = Config(max_iterations=3, emergency_finalization_enabled=True)
    fast = make_execution_profile(RequestRoute.FAST_CHAT, cfg)
    assert fast.emergency_finalization_enabled is False
    provider = RecordingProvider(finalize_text="should not run")
    engine = _engine(
        tmp_path,
        provider,
        max_iterations=1,
        emergency_finalization_enabled=True,
        execution_profile=fast,
    )
    events = _collect(engine)
    assert events[-1].data.get("best_effort_finalized") is not True

    agent = make_execution_profile(
        RequestRoute.AGENT, cfg, emergency_finalization_enabled=True
    )
    assert agent.emergency_finalization_enabled is True
    provider2 = RecordingProvider()
    engine2 = _engine(
        tmp_path,
        provider2,
        max_iterations=2,
        emergency_finalization_enabled=False,  # engine flag OFF; profile ON
        execution_profile=agent,
    )
    events2 = _collect(engine2)
    assert provider2.calls == 3
    assert events2[-1].data.get("best_effort_finalized") is True
