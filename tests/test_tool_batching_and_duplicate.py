"""Section 65 steps 46–47: batching guidance + conservative duplicate-tool warning."""

from __future__ import annotations

import asyncio
import json

from coworker.agent import build_engine, _TOOL_BATCHING_GUIDANCE
from coworker.agents.chat import chat_agent
from coworker.engine import TurnEngine, _DUPLICATE_TOOL_WARNING, _tool_call_signature
from coworker.events import EventType
from coworker.permissions import PermissionEngine
from coworker.providers import (
    AssistantTurn,
    ModelCapabilities,
    ProviderClient,
    StreamChunk,
    ToolCall,
)
from coworker.tools import ToolRegistry


class _StubProvider(ProviderClient):
    def complete(self, *, model, messages, tools=None, **settings):
        return AssistantTurn(text="ok")

    def capabilities(self, model):
        return ModelCapabilities()

    def stream(self, *, model, messages, tools=None, **settings):
        yield StreamChunk(turn=self.complete(model=model, messages=messages, tools=tools))


def _collect(engine, user_input="go"):
    async def _run():
        return [ev async for ev in engine.run(user_input)]

    return asyncio.run(_run())


def test_batching_guidance_injected_into_system_prompt():
    assert "Tool efficiency" in _TOOL_BATCHING_GUIDANCE
    assert "same assistant tool-call turn" in _TOOL_BATCHING_GUIDANCE
    engine = build_engine(agent=chat_agent(), provider=_StubProvider())
    sys_msg = engine.messages[0]["content"]
    assert "Tool efficiency" in sys_msg
    assert "same assistant tool-call turn" in sys_msg


class _RepeatSameToolProvider(ProviderClient):
    """Returns the identical tool call until hard ceiling, then stops."""

    def __init__(self):
        self.calls = 0
        self.outbound: list[list[dict]] = []

    def complete(self, *, model, messages, tools=None, **settings):
        self.calls += 1
        self.outbound.append(messages)
        if self.calls >= 5:
            return AssistantTurn(text="done", finish_reason="stop")
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
        turn = self.complete(model=model, messages=messages, tools=tools, **settings)
        yield StreamChunk(turn=turn)


def test_duplicate_tool_warning_after_three_identical_calls(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    provider = _RepeatSameToolProvider()
    registry = ToolRegistry()
    import aisuite as ai

    registry.register_all(ai.toolkits.files(root=str(tmp_path), allow_write=True))
    engine = TurnEngine(
        provider=provider,
        registry=registry,
        permissions=PermissionEngine(workspace_root=tmp_path),
        model="gpt-5.5",
        max_iterations=8,
    )
    events = _collect(engine)
    assert any(ev.type is EventType.TURN_END for ev in events)

    warned = [
        msgs
        for msgs in provider.outbound
        if any(
            isinstance(m.get("content"), str) and _DUPLICATE_TOOL_WARNING in m["content"]
            for m in msgs
            if m.get("role") == "user"
        )
    ]
    assert warned, "expected outbound duplicate-tool warning after 3 identical signatures"
    assert "Do not call it again unless" in _DUPLICATE_TOOL_WARNING


def test_duplicate_tool_warning_requires_identical_args(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("y", encoding="utf-8")

    class VaryingProvider(ProviderClient):
        def __init__(self):
            self.calls = 0
            self.outbound: list[list[dict]] = []

        def complete(self, *, model, messages, tools=None, **settings):
            self.calls += 1
            self.outbound.append(messages)
            if self.calls >= 4:
                return AssistantTurn(text="done")
            path = "a.txt" if self.calls % 2 else "b.txt"
            return AssistantTurn(
                tool_calls=[
                    ToolCall(
                        id=f"c{self.calls}",
                        name="read_file",
                        arguments={"path": path},
                    )
                ],
                finish_reason="tool_calls",
            )

        def capabilities(self, model):
            return ModelCapabilities()

        def stream(self, *, model, messages, tools=None, **settings):
            yield StreamChunk(
                turn=self.complete(model=model, messages=messages, tools=tools)
            )

    provider = VaryingProvider()
    registry = ToolRegistry()
    import aisuite as ai

    registry.register_all(ai.toolkits.files(root=str(tmp_path), allow_write=True))
    engine = TurnEngine(
        provider=provider,
        registry=registry,
        permissions=PermissionEngine(workspace_root=tmp_path),
        model="gpt-5.5",
        max_iterations=8,
    )
    _collect(engine)

    for msgs in provider.outbound:
        blob = json.dumps(msgs, ensure_ascii=False, default=str)
        assert _DUPLICATE_TOOL_WARNING not in blob


def test_duplicate_tool_signature_helper_is_stable():
    a = ToolCall(id="1", name="read_file", arguments={"path": "a.txt", "z": 1})
    b = ToolCall(id="2", name="read_file", arguments={"z": 1, "path": "a.txt"})
    assert _tool_call_signature(a) == _tool_call_signature(b)
