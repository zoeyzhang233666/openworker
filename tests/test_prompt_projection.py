from __future__ import annotations

import asyncio

import aisuite as ai
from coworker.agent import build_engine
from coworker.compaction import estimate_tokens
from coworker.engine import ApprovalOutcome
from coworker.agents import cowork_agent
from coworker.config import Config
from coworker.events import EventType
from coworker.execution_profile import RequestRoute
from coworker.memory import SQLiteMemoryStore
from coworker.providers import (
    AssistantTurn,
    ModelCapabilities,
    ProviderClient,
    StreamChunk,
    ToolCall,
)
from coworker.permissions import Mode
from coworker.providers.base import TokenUsage
from coworker.server import SessionManager, create_app


class RecordingProvider(ProviderClient):
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete(self, **kwargs):  # pragma: no cover - stream is the contract under test
        raise AssertionError("buffered completion must not be used")

    def capabilities(self, model):
        return ModelCapabilities(
            tools=True,
            streaming=True,
            supports_disable_reasoning=False,
        )

    def stream(self, *, model, messages, tools=None, **settings):
        self.calls.append(
            {"model": model, "messages": messages, "tools": tools, "settings": settings}
        )
        turn = AssistantTurn(
            text="你好！",
            reasoning="先友好回应。",
            finish_reason="stop",
            usage=TokenUsage(input=321, output=12),
        )
        yield StreamChunk(reasoning_delta="先友好")
        yield StreamChunk(reasoning_delta="回应。")
        yield StreamChunk(text_delta="你好")
        yield StreamChunk(text_delta="！")
        yield StreamChunk(turn=turn)


def _collect(engine, text="你好"):
    async def run():
        return [event async for event in engine.run(text)]

    return asyncio.run(run())


def test_fresh_default_session_projects_fast_prompt_tools_and_skills(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())
    provider = RecordingProvider()
    engine = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=provider,
        skill_dirs=[tmp_path / "skills"],
    )

    canonical = engine.messages[0]
    assert canonical["_prompt_policy_version"] == 1
    assert "every edge MUST have a semantic label" in canonical["content"]

    events = _collect(engine)
    assert engine._last_turn_plan is not None
    assert engine._last_turn_plan.decision is not None
    assert engine._last_turn_plan.decision.route is RequestRoute.FAST_CHAT
    assert engine._last_turn_plan.skill_names == ()
    assert EventType.REASONING_DELTA in [event.type for event in events]

    call = provider.calls[0]
    assert call["tools"] is None
    assert "reasoning_effort" not in call["settings"]
    system = call["messages"][0]["content"]
    outbound = "\n".join(str(message.get("content", "")) for message in call["messages"])
    assert "You are ChemClaw" in system
    assert len(system) < 4_000
    assert "Mermaid" not in outbound
    assert "Available skills" not in outbound
    assert str(tmp_path) not in outbound
    assert "long-running" not in outbound.lower()
    assert estimate_tokens(call["messages"]) <= 4_000
    final = next(event for event in events if event.type is EventType.ASSISTANT_MESSAGE)
    assert final.data["usage"]["input"] == 321


def _spot_mcp_tool():
    def get_price_trend(**_kwargs):
        return {"status": "ok", "rows": []}

    get_price_trend.__name__ = "mcp__chem_data_hub__get_price_trend"
    get_price_trend.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name=get_price_trend.__name__,
        category="mcp",
        capabilities=["chem-data-hub"],
        risk_level="low",
        requires_approval=False,
    )
    get_price_trend.__coworker_schema__ = {
        "type": "function",
        "function": {
            "name": get_price_trend.__name__,
            "description": "Chemical spot price trend",
            "parameters": {"type": "object", "additionalProperties": True},
        },
    }
    return get_price_trend


def test_production_engine_projects_explicit_spot_to_dynamic_mcp_only(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())
    provider = RecordingProvider()
    engine = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=provider,
        skill_dirs=[tmp_path / "skills"],
        extra_tools=[_spot_mcp_tool()],
    )
    _collect(engine, "查甲醇现货价格")
    call = provider.calls[0]
    assert [item["function"]["name"] for item in call["tools"]] == [
        "mcp__chem_data_hub__get_price_trend"
    ]
    outbound = "\n".join(str(item.get("content", "")) for item in call["messages"])
    assert "CHEMICAL SPOT" in outbound
    assert "Do not call CN futures, Yahoo, or Web to substitute" in outbound


def test_production_engine_reports_spot_unavailable_without_fallback_schema(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())
    provider = RecordingProvider()
    engine = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=provider,
        skill_dirs=[tmp_path / "skills"],
    )
    _collect(engine, "查甲醇现货价格")
    call = provider.calls[0]
    assert call["tools"] is None
    outbound = "\n".join(str(item.get("content", "")) for item in call["messages"])
    assert "get_price_trend` is not available" in outbound
    assert "report unavailable in Chinese" in outbound


def test_existing_session_without_policy_marker_stays_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())
    provider = RecordingProvider()
    old_system = "LEGACY SYSTEM WITH Mermaid AND WORKSPACE RULES"
    engine = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=provider,
        skill_dirs=[tmp_path / "skills"],
        messages=[{"role": "system", "content": old_system}],
    )
    _collect(engine)
    call = provider.calls[0]
    assert call["messages"][0]["content"] == old_system
    assert call["tools"] is not None
    assert engine._last_turn_plan is not None
    assert engine._last_turn_plan.execution_profile is None


def test_policy_v1_marker_survives_session_reload(tmp_path, monkeypatch):
    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())
    first = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=RecordingProvider(),
        skill_dirs=[tmp_path / "skills"],
    )
    reloaded_provider = RecordingProvider()
    reloaded = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=reloaded_provider,
        skill_dirs=[tmp_path / "skills"],
        messages=[dict(message) for message in first.messages],
    )
    _collect(reloaded)
    assert reloaded_provider.calls[0]["tools"] is None
    assert "You are ChemClaw" in reloaded_provider.calls[0]["messages"][0]["content"]
    assert "Mermaid" not in reloaded_provider.calls[0]["messages"][0]["content"]


def test_retry_reuses_the_same_turn_plan(tmp_path, monkeypatch):
    class Flaky(RecordingProvider):
        def stream(self, *, model, messages, tools=None, **settings):
            self.calls.append(
                {"model": model, "messages": messages, "tools": tools, "settings": settings}
            )
            if len(self.calls) == 1:
                raise RuntimeError("transient")
            yield StreamChunk(text_delta="好了")
            yield StreamChunk(turn=AssistantTurn(text="好了", finish_reason="stop"))

    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())
    provider = Flaky()
    engine = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=provider,
        skill_dirs=[tmp_path / "skills"],
    )
    first_events = _collect(engine)
    assert EventType.ERROR in [event.type for event in first_events]
    original_plan = engine._last_turn_plan

    async def retry():
        return [event async for event in engine.retry()]

    retried = asyncio.run(retry())
    assert EventType.TURN_END in [event.type for event in retried]
    assert engine._last_turn_plan is original_plan
    assert [call["tools"] for call in provider.calls] == [None, None]


def test_live_unanswered_control_call_forces_full_agent_plan(tmp_path, monkeypatch):
    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())
    engine = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=RecordingProvider(),
        skill_dirs=[tmp_path / "skills"],
    )
    engine.messages.append(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "ask-pending",
                    "type": "function",
                    "function": {
                        "name": "ask_user",
                        "arguments": '{"question":"继续吗？"}',
                    },
                }
            ],
        }
    )
    plan = engine.turn_planner.plan("好")
    assert plan.decision.route is RequestRoute.AGENT
    assert plan.execution_profile.allowed_tool_names is None
    assert plan.prompt_profile.value == "agent"


def test_prompt_projection_kill_switch_restores_full_prompt_but_keeps_router(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "coworker.agent.load_config",
        lambda *a, **k: Config(prompt_projection_enabled=False),
    )
    provider = RecordingProvider()
    engine = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=provider,
        skill_dirs=[tmp_path / "skills"],
    )
    _collect(engine)
    call = provider.calls[0]
    assert "every edge MUST have a semantic label" in call["messages"][0]["content"]
    assert call["tools"] is None


def test_gui_websocket_receives_live_reasoning_and_text_on_fast_path(
    tmp_path, monkeypatch
):
    from fastapi.testclient import TestClient

    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())
    provider = RecordingProvider()
    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "state",
        provider=provider,
    )
    client = TestClient(create_app(manager))
    events = []
    with client.websocket_connect("/ws/session/d165?agent=cowork") as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "user_message", "text": "你好"})
        while True:
            event = ws.receive_json()
            events.append(event)
            if event["type"] == "turn_done":
                break

    types = [event["type"] for event in events]
    assert "reasoning_delta" in types
    assert "assistant_delta" in types
    assert types.index("reasoning_delta") < types.index("assistant_message")
    assert provider.calls[0]["tools"] is None
    engine = manager.get_engine("d165", agent="cowork")
    assert engine is not None
    assert engine._last_turn_plan is not None
    assert engine._last_turn_plan.decision.route is RequestRoute.FAST_CHAT


def test_gui_websocket_market_matrix_uses_expected_actual_tools(
    tmp_path, monkeypatch
):
    from fastapi.testclient import TestClient

    class MarketProvider(ProviderClient):
        def __init__(self, turns):
            self.turns = list(turns)

        def capabilities(self, model):
            return ModelCapabilities(tools=True)

        def complete(self, *, model, messages, tools=None, **settings):
            return self.turns.pop(0)

    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())

    def run_case(session_id, query, turns, *, answer=None):
        case_dir = tmp_path / session_id
        case_dir.mkdir()
        provider = MarketProvider(turns)
        manager = SessionManager(
            workspace=case_dir,
            data_dir=case_dir / "state",
            provider=provider,
        )

        async def prepare_mcp_tools(*_args, **_kwargs):
            return [_spot_mcp_tool()]

        manager.prepare_mcp_tools = prepare_mcp_tools
        client = TestClient(create_app(manager))
        events = []
        with client.websocket_connect(
            f"/ws/session/{session_id}?agent=cowork"
        ) as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json({"type": "user_message", "text": query})
            while True:
                event = ws.receive_json()
                events.append(event)
                if event["type"] == "question_requested" and answer is not None:
                    ws.send_json({"type": "question_response", "answer": answer})
                if event["type"] == "turn_done":
                    break
        return events

    spot_name = "mcp__chem_data_hub__get_price_trend"
    for session_id, query in (
        ("d166-crude-spot", "查原油现货价格"),
        ("d166-methanol-spot", "查甲醇现货价格"),
    ):
        events = run_case(
            session_id,
            query,
            [
                AssistantTurn(
                    tool_calls=[
                        ToolCall(
                            id=f"{session_id}-tool",
                            name=spot_name,
                            arguments={"chemical": query},
                        )
                    ],
                    finish_reason="tool_calls",
                ),
                AssistantTurn(text="现货结果", finish_reason="stop"),
            ],
        )
        proposed = [
            event["data"]["name"]
            for event in events
            if event["type"] == "tool_proposed"
        ]
        finished = [
            event["data"]["name"]
            for event in events
            if event["type"] == "tool_finished"
        ]
        assert proposed == [spot_name]
        assert finished == [spot_name]

    futures = run_case(
        "d166-methanol-futures",
        "查甲醇期货价格",
        [
            AssistantTurn(
                tool_calls=[
                    ToolCall(
                        id="methanol-futures-tool",
                        name="lookup_cn_futures_quote",
                        arguments={"symbol": "MA2509"},
                    )
                ],
                finish_reason="tool_calls",
            ),
            AssistantTurn(text="期货结果", finish_reason="stop"),
        ],
    )
    assert [
        event["data"]["name"]
        for event in futures
        if event["type"] == "tool_finished"
    ] == ["lookup_cn_futures_quote"]

    clarified = run_case(
        "d166-methanol-clarify",
        "查甲醇价格",
        [
            AssistantTurn(
                tool_calls=[
                    ToolCall(
                        id="methanol-ask",
                        name="ask_user",
                        arguments={
                            "question": "请选择行情口径",
                            "header": "行情口径",
                            "allow_text": False,
                            "options": ["化工现货", "国内期货"],
                        },
                    )
                ],
                finish_reason="tool_calls",
            ),
            AssistantTurn(
                tool_calls=[
                    ToolCall(
                        id="methanol-after-ask",
                        name="lookup_cn_futures_quote",
                        arguments={"symbol": "MA2509"},
                    )
                ],
                finish_reason="tool_calls",
            ),
            AssistantTurn(text="已按国内期货口径查询", finish_reason="stop"),
        ],
        answer="国内期货",
    )
    assert "question_requested" in [event["type"] for event in clarified]
    assert [
        event["data"]["name"]
        for event in clarified
        if event["type"] == "tool_finished"
    ] == ["ask_user", "lookup_cn_futures_quote"]


def test_projected_workspace_pack_keeps_standard_permission_approval(
    tmp_path, monkeypatch
):
    class WriteThenStop(ProviderClient):
        def __init__(self):
            self.turns = [
                AssistantTurn(
                    tool_calls=[
                        ToolCall(
                            id="write-1",
                            name="write_file",
                            arguments={"path": "result.txt", "content": "ok\n"},
                        )
                    ],
                    finish_reason="tool_calls",
                ),
                AssistantTurn(text="done", finish_reason="stop"),
            ]
            self.tool_names: list[set[str]] = []

        def capabilities(self, model):
            return ModelCapabilities(tools=True)

        def complete(self, *, model, messages, tools=None, **settings):
            self.tool_names.append(
                {
                    schema["function"]["name"]
                    for schema in (tools or [])
                }
            )
            return self.turns.pop(0)

    async def approve(_request):
        return ApprovalOutcome.ONCE

    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())
    provider = WriteThenStop()
    engine = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=provider,
        mode=Mode.INTERACTIVE,
        approver=approve,
        skill_dirs=[tmp_path / "skills"],
    )
    events = _collect(engine, "请写入文件 result.txt")
    assert EventType.PERMISSION_REQUIRED in [event.type for event in events]
    assert "write_file" in provider.tool_names[0]
    assert "memory_read" not in provider.tool_names[0]
    assert (tmp_path / "result.txt").read_text(encoding="utf-8") == "ok\n"


def test_targeted_and_workspace_prompts_only_add_relevant_sections(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())

    targeted_provider = RecordingProvider()
    targeted = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=targeted_provider,
        memory_store=SQLiteMemoryStore(tmp_path / "memory.db"),
        skill_dirs=[tmp_path / "skills"],
    )
    _collect(targeted, "记住我偏好简体中文")
    targeted_outbound = "\n".join(
        str(message.get("content", ""))
        for message in targeted_provider.calls[0]["messages"]
    )
    assert targeted._last_turn_plan.prompt_profile.value == "agent_targeted"
    assert "Memory:" in targeted_outbound
    assert "Mermaid" not in targeted_outbound
    assert "chart" not in targeted_outbound.lower()
    assert str(tmp_path) not in targeted_outbound

    workspace_provider = RecordingProvider()
    workspace = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=workspace_provider,
        skill_dirs=[tmp_path / "skills"],
    )
    _collect(workspace, "读取并修改这个 Python 文件，然后运行测试")
    workspace_outbound = "\n".join(
        str(message.get("content", ""))
        for message in workspace_provider.calls[0]["messages"]
    )
    assert workspace._last_turn_plan.prompt_profile.value == "agent_workspace"
    assert str(tmp_path) in workspace_outbound
    assert "Mermaid" not in workspace_outbound
    assert "```chart" not in workspace_outbound


def test_visual_workspace_prompt_adds_diagram_and_chart_sections(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("coworker.agent.load_config", lambda *a, **k: Config())
    provider = RecordingProvider()
    engine = build_engine(
        agent=cowork_agent(),
        workspace=tmp_path,
        provider=provider,
        skill_dirs=[tmp_path / "skills"],
    )
    _collect(engine, "读取文件 data.csv 并制作趋势图")
    outbound = "\n".join(
        str(message.get("content", "")) for message in provider.calls[0]["messages"]
    )
    assert engine._last_turn_plan.prompt_profile.value == "agent_visual"
    assert "Mermaid" in outbound
    assert "```chart" in outbound
