"""P2 gate tests — turn engine + event bus (scripted provider, no network)."""

from __future__ import annotations

import asyncio
import threading
import time

import aisuite as ai
from coworker.config import Config
from coworker.engine import ApprovalOutcome, PermissionRequest, TurnEngine
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
from coworker.turn_planner import TurnPlanner


def _text_turn(text):
    return AssistantTurn(text=text, finish_reason="stop")


def _tool_turn(name, args, call_id="call_1"):
    return AssistantTurn(
        tool_calls=[ToolCall(id=call_id, name=name, arguments=args)],
        finish_reason="tool_calls",
    )


class ScriptedProvider(ProviderClient):
    """Returns queued AssistantTurns; streams via the base default (one final chunk)."""

    def __init__(self, turns, *, loop=False):
        self._turns = list(turns)
        self._loop = loop
        self.calls = 0

    def complete(self, *, model, messages, tools=None, **settings):
        self.calls += 1
        return self._turns[0] if self._loop else self._turns.pop(0)

    def capabilities(self, model):
        return ModelCapabilities()


def _engine(tmp_path, turns, *, approver=None, loop=False, max_iterations=12):
    provider = ScriptedProvider(turns, loop=loop)
    registry = ToolRegistry()
    registry.register_all(ai.toolkits.files(root=str(tmp_path), allow_write=True))
    permissions = PermissionEngine(workspace_root=tmp_path)
    engine = TurnEngine(
        provider=provider,
        registry=registry,
        permissions=permissions,
        model="gpt-5.5",
        approver=approver,
        max_iterations=max_iterations,
    )
    return engine, provider


def _collect(engine, user_input):
    async def _run():
        return [ev async for ev in engine.run(user_input)]

    return asyncio.run(_run())


def _types(events):
    return [ev.type for ev in events]


# -- tests ----------------------------------------------------------------------


def test_no_tool_turn(tmp_path):
    engine, _ = _engine(tmp_path, [_text_turn("all done")])
    events = _collect(engine, "hi")
    assert _types(events) == [
        EventType.TURN_START,
        EventType.ASSISTANT_MESSAGE,
        EventType.TURN_END,
    ]
    assert events[1].data["text"] == "all done"
    assert events[-1].data["status"] == "completed"


def test_tool_turn_order_and_execution(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    engine, _ = _engine(
        tmp_path,
        [_tool_turn("read_file", {"path": "a.txt"}), _text_turn("it says hello")],
    )
    events = _collect(engine, "read a.txt")
    assert EventType.PERMISSION_REQUIRED not in _types(events)
    assert _types(events) == [
        EventType.TURN_START,
        EventType.ASSISTANT_MESSAGE,
        EventType.TOOL_PROPOSED,
        EventType.TOOL_STARTED,
        EventType.TOOL_FINISHED,
        EventType.ITERATION_END,
        EventType.ASSISTANT_MESSAGE,
        EventType.TURN_END,
    ]
    finished = next(e for e in events if e.type == EventType.TOOL_FINISHED)
    assert finished.data["status"] == "ok"
    assert any(
        m.get("role") == "tool" and "hello" in m["content"] for m in engine.messages
    )


def test_write_requires_approval_then_approved(tmp_path):
    async def approve_once(_req: PermissionRequest):
        return ApprovalOutcome.ONCE

    engine, _ = _engine(
        tmp_path,
        [
            _tool_turn("write_file", {"path": "new.py", "content": "print(1)\n"}),
            _text_turn("wrote new.py"),
        ],
        approver=approve_once,
    )
    events = _collect(engine, "create new.py")
    assert EventType.PERMISSION_REQUIRED in _types(events)
    assert (tmp_path / "new.py").read_text() == "print(1)\n"


def test_denied_tool_yields_error_and_continues(tmp_path):
    async def deny(_req: PermissionRequest):
        return ApprovalOutcome.DENY

    engine, _ = _engine(
        tmp_path,
        [
            _tool_turn("write_file", {"path": "new.py", "content": "x"}),
            _text_turn("ok, skipped it"),
        ],
        approver=deny,
    )
    events = _collect(engine, "create new.py")
    assert not (tmp_path / "new.py").exists()
    finished = next(e for e in events if e.type == EventType.TOOL_FINISHED)
    assert finished.data["status"] == "denied"
    assert _types(events)[-1] == EventType.TURN_END
    assert any(
        m.get("role") == "tool" and "not executed" in m["content"]
        for m in engine.messages
    )


def test_max_iterations_rail(tmp_path):
    engine, provider = _engine(
        tmp_path, [_tool_turn("list_files", {})], loop=True, max_iterations=3
    )
    events = _collect(engine, "loop forever")
    end = events[-1]
    assert end.type == EventType.TURN_END
    assert end.data["status"] == "max_iterations_exceeded"
    assert provider.calls == 3


def test_interrupt_between_iterations(tmp_path):
    engine_holder = {}

    async def approve_and_interrupt(_req: PermissionRequest):
        engine_holder["engine"].request_interrupt()
        return ApprovalOutcome.ONCE

    engine, provider = _engine(
        tmp_path,
        [
            _tool_turn("write_file", {"path": "x.py", "content": "x"}),
            _text_turn("should not be reached"),
        ],
        approver=approve_and_interrupt,
    )
    engine_holder["engine"] = engine
    events = _collect(engine, "do a thing")
    assert events[-1].type == EventType.INTERRUPTED
    assert provider.calls == 1


def test_steering_injects_next_turn(tmp_path):
    engine, provider = _engine(tmp_path, [_text_turn("first"), _text_turn("second")])
    engine.queue_steering("actually, also do this")
    events = _collect(engine, "do the first thing")
    assert provider.calls == 2
    assert any(
        m.get("role") == "user" and m["content"] == "actually, also do this"
        for m in engine.messages
    )
    assert events[-1].data["status"] == "completed"


# -- parallel tool execution ------------------------------------------------------


def _multi_tool_turn(calls):
    return AssistantTurn(
        tool_calls=[
            ToolCall(id=f"call_{i}", name=name, arguments=args)
            for i, (name, args) in enumerate(calls)
        ],
        finish_reason="tool_calls",
    )


def _bare_engine(tmp_path, turns):
    provider = ScriptedProvider(turns)
    registry = ToolRegistry()
    permissions = PermissionEngine(workspace_root=tmp_path)
    engine = TurnEngine(
        provider=provider,
        registry=registry,
        permissions=permissions,
        model="gpt-5.5",
    )
    return engine, registry


def test_low_risk_tool_calls_run_concurrently(tmp_path):
    # Both tools block on a 2-party barrier: the turn only completes if the engine
    # really runs them at the same time (sequential execution would trip the timeout
    # and surface as an error result).
    barrier = threading.Barrier(2, timeout=5)
    low = ai.ToolMetadata(category="search", risk_level="low", requires_approval=False)

    def side_a():
        """Wait for side_b."""
        barrier.wait()
        return {"side": "a"}

    def side_b():
        """Wait for side_a."""
        barrier.wait()
        return {"side": "b"}

    engine, registry = _bare_engine(
        tmp_path,
        [_multi_tool_turn([("side_a", {}), ("side_b", {})]), _text_turn("done")],
    )
    registry.register(side_a, metadata=low)
    registry.register(side_b, metadata=low)

    events = _collect(engine, "go")
    finished = [e for e in events if e.type == EventType.TOOL_FINISHED]
    assert len(finished) == 2
    assert all(e.data["status"] == "ok" for e in finished)
    # a tool result message exists for every call id
    tool_ids = {
        m.get("tool_call_id") for m in engine.messages if m.get("role") == "tool"
    }
    assert tool_ids == {"call_0", "call_1"}


def test_non_low_risk_tool_calls_stay_sequential(tmp_path):
    order = []
    medium = ai.ToolMetadata(
        category="filesystem", risk_level="medium", requires_approval=False
    )

    def first():
        """Record start/end with a delay."""
        order.append("first-start")
        time.sleep(0.2)
        order.append("first-end")
        return "ok"

    def second():
        """Record start/end."""
        order.append("second-start")
        order.append("second-end")
        return "ok"

    engine, registry = _bare_engine(
        tmp_path,
        [_multi_tool_turn([("first", {}), ("second", {})]), _text_turn("done")],
    )
    registry.register(first, metadata=medium)
    registry.register(second, metadata=medium)

    _collect(engine, "go")
    assert order == ["first-start", "first-end", "second-start", "second-end"]


class StreamingProvider(ProviderClient):
    def complete(self, **kwargs):  # pragma: no cover - streamed instead
        raise NotImplementedError

    def capabilities(self, model):
        return ModelCapabilities()

    def stream(self, *, model, messages, tools=None, **settings):
        for piece in ["Hel", "lo, ", "world"]:
            yield StreamChunk(text_delta=piece)
        yield StreamChunk(turn=AssistantTurn(text="Hello, world", finish_reason="stop"))


def test_streaming_emits_deltas(tmp_path):
    registry = ToolRegistry()
    permissions = PermissionEngine(workspace_root=tmp_path)
    engine = TurnEngine(
        provider=StreamingProvider(),
        registry=registry,
        permissions=permissions,
        model="gpt-5.5",
    )
    events = _collect(engine, "say hi")
    deltas = [e.data["text"] for e in events if e.type == EventType.ASSISTANT_DELTA]
    assert deltas == ["Hel", "lo, ", "world"]
    final = next(e for e in events if e.type == EventType.ASSISTANT_MESSAGE)
    assert final.data["text"] == "Hello, world"
    assert events[-1].type == EventType.TURN_END


class EmptyStreamProvider(ProviderClient):
    """Compat gateways with a wrong base_url often yield zero chunks and no turn."""

    def complete(self, **kwargs):  # pragma: no cover - streamed instead
        raise NotImplementedError

    def capabilities(self, model):
        return ModelCapabilities()

    def stream(self, *, model, messages, tools=None, **settings):
        return
        yield  # pragma: no cover — make this a generator


def test_empty_stream_surfaces_error_instead_of_blank_assistant(tmp_path):
    registry = ToolRegistry()
    permissions = PermissionEngine(workspace_root=tmp_path)
    engine = TurnEngine(
        provider=EmptyStreamProvider(),
        registry=registry,
        permissions=permissions,
        model="gpt-5.5",
    )
    events = _collect(engine, "hi")
    assert EventType.ERROR in _types(events)
    assert EventType.ASSISTANT_MESSAGE not in _types(events)
    assert events[-1].type == EventType.ERROR
    assert "empty" in events[-1].data["error"].lower()
    assert any(
        m.get("role") == "notice" and m.get("kind") == "error" for m in engine.messages
    )


def _pdf_file_part():
    import base64
    import io

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    url = "data:application/pdf;base64," + base64.b64encode(buf.getvalue()).decode()
    return {"type": "file", "file": {"filename": "d.pdf", "file_data": url}}


def test_outbound_adapts_pdf_for_non_pdf_models(tmp_path):
    # ScriptedProvider reports default caps (pdf=False) → the file part must be
    # replaced at send time while the stored history keeps the real document.
    engine, _ = _engine(tmp_path, [_text_turn("ok")])
    engine.messages.append(
        {
            "role": "user",
            "content": [{"type": "text", "text": "read this"}, _pdf_file_part()],
        }
    )
    parts = engine._outbound_messages()[-1]["content"]
    assert all(p["type"] != "file" for p in parts)
    assert "d.pdf" in parts[-1]["text"]
    assert engine.messages[-1]["content"][1]["type"] == "file"  # history untouched


def test_outbound_keeps_pdf_for_native_models(tmp_path):
    class NativeProvider(ScriptedProvider):
        def capabilities(self, model):
            return ModelCapabilities(vision=True, pdf=True)

    engine, _ = _engine(tmp_path, [_text_turn("ok")])
    engine.provider = NativeProvider([_text_turn("ok")])
    message = {
        "role": "user",
        "content": [{"type": "text", "text": "read this"}, _pdf_file_part()],
    }
    engine.messages.append(message)
    assert engine._outbound_messages()[-1]["content"][1]["type"] == "file"


def test_provider_extras_persist_on_message_and_survive_outbound(tmp_path):
    """A turn's provider-private sidecar (`extras`, e.g. Gemini thought signatures) rides
    the persisted assistant message and is NOT stripped by _outbound_messages — the owning
    provider needs it back; foreign providers strip it themselves."""
    turn = AssistantTurn(
        text="ok",
        finish_reason="stop",
        extras={"_gemini": {"text_sig": "c2ln", "call_sigs": []}},
    )
    engine, _ = _engine(tmp_path, [turn])
    _collect(engine, "hi")

    persisted = engine.messages[-1]
    assert persisted["_gemini"] == {"text_sig": "c2ln", "call_sigs": []}
    outbound = engine._outbound_messages()[-1]
    assert outbound["_gemini"] == {"text_sig": "c2ln", "call_sigs": []}
    assert "ts" not in outbound  # display sidecars still stripped


def test_switch_model_appends_notice_only_midsession(tmp_path):
    engine, _ = _engine(tmp_path, [_text_turn("ok")])
    # Fresh session: first bind is silent.
    assert engine.switch_model("zai:glm-5.2") is None
    assert engine.model == "zai:glm-5.2"
    _collect(engine, "hi")
    # Same model: no-op.
    assert engine.switch_model("zai:glm-5.2") is None
    # Real mid-session switch: persisted marker with the matrix label.
    text = engine.switch_model("kimi:kimi-k2.6")
    assert "Kimi K2.6" in text and engine.model == "kimi:kimi-k2.6"
    notice = engine.messages[-1]
    assert notice["role"] == "notice" and notice["kind"] == "model_switch"
    assert all(m.get("role") != "notice" for m in engine._outbound_messages())


def test_switch_model_warns_when_images_meet_text_only_model(tmp_path):
    class NoVisionProvider(ScriptedProvider):
        def capabilities(self, model):
            return ModelCapabilities(vision=False)

    engine, _ = _engine(tmp_path, [_text_turn("ok")])
    engine.provider = NoVisionProvider([_text_turn("ok")])
    engine.messages.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "look"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
            ],
        }
    )
    text = engine.switch_model("zai:glm-5.2")
    assert "images" in text  # degradation is called out in the marker


def test_outbound_replaces_images_for_non_vision_models(tmp_path):
    class NoVisionProvider(ScriptedProvider):
        def capabilities(self, model):
            return ModelCapabilities(vision=False)

    engine, _ = _engine(tmp_path, [_text_turn("ok")])
    engine.provider = NoVisionProvider([_text_turn("ok")])
    engine.messages.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "look"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
            ],
        }
    )
    parts = engine._outbound_messages()[-1]["content"]
    assert all(p["type"] != "image_url" for p in parts)
    assert "not viewable" in parts[-1]["text"]
    assert engine.messages[-1]["content"][1]["type"] == "image_url"  # history untouched


def test_chart_finished_sidecar_extracts_chart_spec_not_full_ohlc_dump():
    from coworker.engine import chart_finished_sidecar

    spec = {
        "version": 1,
        "type": "candlestick",
        "labels": ["2026-01-01", "2026-01-02"],
        "ohlc": [{"o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5}, {"o": 1.5, "h": 2.2, "l": 1.4, "c": 2.0}],
    }
    extra = chart_finished_sidecar(
        {
            "status": "ok",
            "symbol": "GC=F",
            "name": "Gold",
            "aliases": ["gold"],
            "labels": ["2026-01-01"] * 200,
            "ohlc": [{"o": 1, "h": 2, "l": 0, "c": 1}] * 200,
            "chart_spec": spec,
        }
    )
    assert extra["chart_spec"] == spec
    assert extra["symbol"] == "GC=F"
    assert extra["plot_status"] == "ok"
    assert extra["series_name"] == "Gold"
    assert "name" not in extra
    assert extra["aliases"] == ["gold"]
    assert "labels" not in extra
    assert "ohlc" not in extra


def test_tool_finished_keeps_tool_name_when_ohlc_has_product_name():
    """D-179: product label must not overwrite TOOL_FINISHED.data['name']."""
    from coworker.engine import chart_finished_sidecar

    result = {
        "status": "ok",
        "symbol": "MA2609.DCE",
        "name": "甲醇",
        "aliases": ["甲醇", "郑醇"],
        "chart_spec": {
            "version": 1,
            "type": "candlestick",
            "labels": ["2026-01-01"],
            "ohlc": [{"o": 1, "h": 2, "l": 0, "c": 1}],
        },
    }
    sidecar = chart_finished_sidecar(result)
    merged = {
        "name": "lookup_cn_futures_ohlc",
        "status": "success",
        **sidecar,
    }
    assert merged["name"] == "lookup_cn_futures_ohlc"
    assert merged["series_name"] == "甲醇"
    assert "甲醇" != merged["name"]


def test_chart_finished_sidecar_empty_without_spec_or_error():
    from coworker.engine import chart_finished_sidecar

    assert chart_finished_sidecar({"ok": True}) == {}
    assert chart_finished_sidecar("not a dict") == {}


# -- D-166 market-scope execution guard ----------------------------------------


def _market_engine(tmp_path, turns, *, answer="化工现货"):
    provider = ScriptedProvider(turns)
    registry = ToolRegistry()
    calls: dict[str, int] = {}

    for name, category, capabilities in (
        ("ask_user", "interaction", ["ask_user"]),
        (
            "mcp__chem-data-hub__get_price_trend",
            "mcp",
            ["chem-data-hub"],
        ),
        ("lookup_cn_futures_quote", "market", ["cn_market"]),
        ("lookup_cn_futures_ohlc", "market", ["cn_market"]),
        ("lookup_yahoo_ohlc", "market", ["yahoo"]),
        ("lookup_chemical_identity", "chemistry", ["chem_identity"]),
        ("web_search", "search", ["web"]),
    ):

        def _tool(_name=name, **_kwargs):
            calls[_name] = calls.get(_name, 0) + 1
            return {"status": "ok", "tool": _name}

        _tool.__name__ = name
        registry.register(
            _tool,
            schema={
                "type": "function",
                "function": {
                    "name": name,
                    "description": "D-166 market guard fixture",
                    "parameters": {"type": "object", "additionalProperties": True},
                },
            },
            metadata=ai.ToolMetadata(
                name=name,
                category=category,
                capabilities=capabilities,
                risk_level="low",
                requires_approval=False,
            ),
        )

    async def question_asker(_args, _tool_call_id):
        return {"answer": answer}

    planner = TurnPlanner(
        config=Config(),
        available_tool_names=registry.names,
        available_tools=registry.descriptors,
    )
    engine = TurnEngine(
        provider=provider,
        registry=registry,
        permissions=PermissionEngine(workspace_root=tmp_path),
        model="gpt-5.5",
        turn_planner=planner,
        question_asker=question_asker,
    )
    return engine, calls


def test_turn_plan_allowlist_guard_blocks_undeclared_capability_tool(tmp_path):
    engine, calls = _market_engine(
        tmp_path,
        [
            _tool_turn("web_search", {"query": "CAS 67-56-1"}),
            _text_turn("未使用未声明的网页替代源"),
        ],
    )

    events = _collect(engine, "查询 CAS 67-56-1")

    assert calls.get("web_search", 0) == 0
    denied = [
        event
        for event in events
        if event.type is EventType.TOOL_FINISHED
        and event.data.get("name") == "web_search"
    ]
    assert denied and denied[0].data["status"] == "denied"
    assert denied[0].data["outcome"]["status"] == "denied"
    assert "Scenario/Capability" in denied[0].data["reason"]


def test_market_guard_rejects_price_tool_before_clarification(tmp_path):
    engine, calls = _market_engine(
        tmp_path,
        [
            _tool_turn("lookup_cn_futures_ohlc", {"symbol": "MA2509"}),
            _text_turn("需要先确认口径"),
        ],
    )
    events = _collect(engine, "查甲醇价格")
    denied = [
        event
        for event in events
        if event.type is EventType.TOOL_FINISHED
        and event.data.get("name") == "lookup_cn_futures_ohlc"
    ]
    assert denied and denied[0].data["status"] == "denied"
    assert calls.get("lookup_cn_futures_ohlc", 0) == 0
    assert "市场口径尚未确认" in denied[0].data["reason"]


def test_market_guard_allows_selected_spot_after_ask_user(tmp_path):
    engine, calls = _market_engine(
        tmp_path,
        [
            _multi_tool_turn(
                [
                    ("ask_user", {"question": "请选择行情口径"}),
                    (
                        "mcp__chem-data-hub__get_price_trend",
                        {"chemical": "甲醇"},
                    ),
                ]
            ),
            _text_turn("现货结果"),
        ],
    )
    events = _collect(engine, "查甲醇价格")
    assert calls.get("mcp__chem-data-hub__get_price_trend", 0) == 1
    spot_finished = [
        event
        for event in events
        if event.type is EventType.TOOL_FINISHED
        and event.data.get("name") == "mcp__chem-data-hub__get_price_trend"
    ]
    assert spot_finished and spot_finished[0].data["status"] == "ok"


def test_market_guard_rejects_futures_after_spot_was_selected(tmp_path):
    engine, calls = _market_engine(
        tmp_path,
        [
            _multi_tool_turn(
                [
                    ("ask_user", {"question": "请选择行情口径"}),
                    ("lookup_cn_futures_quote", {"symbol": "MA2509"}),
                ]
            ),
            _text_turn("已按现货口径处理"),
        ],
    )
    events = _collect(engine, "查甲醇价格")
    assert calls.get("lookup_cn_futures_quote", 0) == 0
    rejected = [
        event
        for event in events
        if event.type is EventType.TOOL_FINISHED
        and event.data.get("name") == "lookup_cn_futures_quote"
    ]
    assert rejected and rejected[0].data["status"] == "denied"
    assert "市场口径不一致" in rejected[0].data["reason"]


def test_market_guard_allows_spot_and_futures_for_basis_arb(tmp_path):
    engine, calls = _market_engine(
        tmp_path,
        [
            _multi_tool_turn(
                [
                    (
                        "mcp__chem-data-hub__get_price_trend",
                        {"product_name": "甲醇", "limit": 90},
                    ),
                    ("lookup_cn_futures_ohlc", {"symbol": "MA2509"}),
                ]
            ),
            _text_turn("期现对照完成"),
        ],
    )
    events = _collect(engine, "甲醇期货产业链上下游套利")
    assert calls.get("mcp__chem-data-hub__get_price_trend", 0) == 1
    assert calls.get("lookup_cn_futures_ohlc", 0) == 1
    finished = {
        event.data["name"]: event.data["status"]
        for event in events
        if event.type is EventType.TOOL_FINISHED
        and event.data.get("name")
        in {
            "mcp__chem-data-hub__get_price_trend",
            "lookup_cn_futures_ohlc",
        }
    }
    assert finished["mcp__chem-data-hub__get_price_trend"] == "ok"
    assert finished["lookup_cn_futures_ohlc"] == "ok"


def test_market_guard_survives_durable_resume_of_pending_clarification(tmp_path):
    engine, calls = _market_engine(
        tmp_path,
        [
            _tool_turn("lookup_cn_futures_quote", {"symbol": "MA2509"}),
            _text_turn("恢复后仍按现货口径"),
        ],
    )
    engine.messages.extend(
        [
            {"role": "user", "content": "查甲醇价格"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "pending-market-ask",
                        "type": "function",
                        "function": {
                            "name": "ask_user",
                            "arguments": '{"question":"请选择行情口径"}',
                        },
                    }
                ],
            },
        ]
    )

    async def resume():
        return [event async for event in engine.resume()]

    events = asyncio.run(resume())
    assert calls.get("lookup_cn_futures_quote", 0) == 0
    rejected = [
        event
        for event in events
        if event.type is EventType.TOOL_FINISHED
        and event.data.get("name") == "lookup_cn_futures_quote"
    ]
    assert rejected and rejected[0].data["status"] == "denied"
