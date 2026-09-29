"""Offline latency attribution through the real SDK, engine, and trace store."""
from functools import partial
import asyncio
import json
import threading

import httpx
from openai import OpenAI
import pytest

from coworker.events import Event, EventType
from coworker.provider_timing import CallTiming, timing_scope, on_http_request, on_http_response
from coworker.providers import AssistantTurn, StreamChunk
from coworker.providers.openai_provider import OpenAIProvider
from coworker.tracing import TurnTrace, TurnTraceRecorder, TurnTraceStore
from tests.test_engine import _engine, _collect, _text_turn, _tool_turn
from tests.test_providers import _chunk, _StreamClient, _tools_read_file


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_sdk_http_and_engine_timestamps_and_usage(tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr("coworker.engine.TurnTraceRecorder", partial(TurnTraceRecorder, clock=clock))
    captured = []

    class Body(httpx.SyncByteStream):
        def __iter__(self):
            for at, delta, finish in [(.06, {"reasoning_content": "secret reasoning"}, None),
                                      (.10, {"content": "答案"}, None), (.14, {}, "stop")]:
                clock.now = at
                yield ("data: " + json.dumps({"choices": [{"index": 0, "delta": delta,
                       "finish_reason": finish}]}) + "\n\n").encode()
            yield b'data: {"choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 3, "prompt_tokens_details": {"cached_tokens": 4}}}\n\n'
            yield b"data: [DONE]\n\n"

    def handle(request):
        captured.append(json.loads(request.content))
        clock.now = .04
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=Body())

    client = OpenAI(api_key="secret-key", base_url="https://unit.test/v1", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle),
                    event_hooks={"request": [on_http_request], "response": [on_http_response]}))
    try:
        engine, _ = _engine(tmp_path, [])
        engine.provider = OpenAIProvider(client=client)
        stream = engine._astream_timed
        async def prepare(timing):
            clock.now = .01
            async for chunk in stream(timing):
                yield chunk
        engine._astream_timed = prepare
        traces = []
        engine.trace_sink = traces.append
        events = _collect(engine, "secret user question")
        trace = traces[0]
        call = trace.model_call_timings[0]
        assert call.provider_start_ms == 10
        assert call.http_requests[0].request_ms == 10
        assert call.http_requests[0].headers_ms == 40
        assert call.upstream_first_reasoning_ms == 60
        assert call.upstream_first_content_ms == 100
        assert call.provider_first_text_ms == 100
        assert 100 <= call.engine_first_text_ms <= 140
        assert call.elapsed_ms == 140 and call.status == "completed"
        assert trace.stage_elapsed_ms["first_engine_text"] == call.engine_first_text_ms
        assert trace.input_tokens == 12 and trace.cache_read_tokens == 4
        assert trace.output_tokens == 3 and trace.usage_reported_calls == 1
        assert trace.model_calls == 1
        assert any(e.type is EventType.ASSISTANT_DELTA for e in events)
        assert "secret" not in trace.model_dump_json()
        assert not any("timing" in key for key in captured[0])
        store = TurnTraceStore(tmp_path / "trace.db")
        store.append(trace)
        assert store.get(trace.trace_id) == trace
        store.close()
    finally:
        client.close()


def test_http_retry_has_separate_header_waits():
    clock = Clock()
    timing = CallTiming(clock=clock)
    tries = []
    def handle(request):
        tries.append(request)
        clock.now += .02
        if len(tries) == 1:
            return httpx.Response(400, json={"error": {"message": "Unsupported parameter: stream_options", "type": "invalid_request_error", "param": "stream_options", "code": "unsupported_parameter"}})
        return httpx.Response(200, headers={"content-type": "text/event-stream"},
                             content=b'data: {"choices":[{"index":0,"delta":{"content":"ok"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
    with OpenAI(api_key="test", base_url="https://unit.test/v1", max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(handle),
                event_hooks={"request": [on_http_request], "response": [on_http_response]})) as client:
        with timing_scope(timing):
            out = list(OpenAIProvider(client=client).stream(model="custom", messages=[]))
    snap = timing.finish("completed")
    assert out[-1].turn.text == "ok"
    assert snap["http_request_count"] == 2
    assert snap["http_requests"] == [{"request_ms": 0, "headers_ms": 20}, {"request_ms": 20, "headers_ms": 40}]


def test_compat_buffer_is_distinct_from_raw_upstream_content(tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr("coworker.engine.TurnTraceRecorder", partial(TurnTraceRecorder, clock=clock))
    def chunks():
        clock.now = .01
        yield _chunk(content='{"analysis":')
        clock.now = .08
        yield _chunk(content='"plain JSON"}')
        clock.now = .10
        yield _chunk(finish="stop")
    engine, _ = _engine(tmp_path, [])
    engine.provider = OpenAIProvider(client=_StreamClient(chunks()))
    traces = []
    engine.trace_sink = traces.append
    _collect(engine, "summarize")
    call = traces[0].model_call_timings[0]
    assert call.upstream_first_content_ms == 10
    assert call.provider_first_text_ms > call.upstream_first_content_ms
    assert call.http_requests == ()  # An injected fake client is not an HTTP measurement.


def test_phase_wall_clock_and_missing_usage_are_not_guessed():
    clock = Clock()
    recorder = TurnTraceRecorder(session_id="s", model="m", plan=None, clock=clock)
    recorder.observe(Event(EventType.MODEL_REQUEST))
    recorder.observe(Event(EventType.ASSISTANT_MESSAGE, {"text": "progress"}))
    clock.now = .01
    recorder.observe(Event(EventType.TOOL_PROPOSED, {"name": "web_search"}))
    clock.now = .02
    recorder.observe(Event(EventType.TOOL_PROPOSED, {"name": "web_search"}))
    clock.now = .08
    recorder.observe(Event(EventType.TOOL_FINISHED, {"name": "web_search", "status": "ok"}))
    recorder.observe(Event(EventType.TOOL_FINISHED, {"name": "web_search", "status": "ok"}))
    recorder.observe(Event(EventType.ITERATION_END))
    clock.now = .09
    recorder.observe(Event(EventType.COMPACTING))
    clock.now = .12
    recorder.observe(Event(EventType.COMPACTED))
    recorder.observe(Event(EventType.TURN_END, {"status": "completed"}))
    trace = recorder.finish()
    assert trace.stage_elapsed_ms["tools_and_approval"] == 70  # union, not 70+60
    assert trace.stage_elapsed_ms["compaction"] == 30
    assert trace.usage_reported_calls == 0


def test_failed_provider_call_is_saved_and_retry_gets_new_trace(tmp_path):
    engine, provider = _engine(tmp_path, [])
    def fail(**kwargs):
        raise ValueError("secret backend failure")
    provider.stream = fail
    traces = []
    engine.trace_sink = traces.append
    _collect(engine, "question")
    assert traces[0].model_call_timings[0].status == "failed"
    provider.stream = lambda **kwargs: iter([StreamChunk(turn=AssistantTurn(text="done"))])
    async def retry():
        return [e async for e in engine.retry()]
    asyncio.run(retry())
    assert len(traces) == 2
    assert len(traces[1].model_call_timings) == 1
    assert traces[1].parent_trace_id == traces[0].trace_id
    assert "secret" not in traces[0].model_dump_json()


def test_scopes_are_thread_local_and_stop_freezes_late_updates():
    clock = Clock()
    a, b = CallTiming(clock=clock), CallTiming(clock=clock)
    with timing_scope(a):
        on_http_request(None)
        def other():
            on_http_request(None)  # outer thread context is not inherited
            with timing_scope(b):
                on_http_request(None)
                on_http_response(None)
        thread = threading.Thread(target=other)
        thread.start()
        thread.join()
        frozen = a.finish("interrupted")
        clock.now = 10
        on_http_response(None)
        on_http_request(None)
    assert a.finish("completed") == frozen
    assert frozen["http_request_count"] == 1
    assert "headers_ms" not in frozen["http_requests"][0]
    assert b.finish("completed")["http_request_count"] == 1


def test_old_trace_without_timings_still_loads():
    old = TurnTraceRecorder(session_id="s", model="m", plan=None).finish().model_dump()
    for key in ("model_call_timings", "cache_read_tokens", "cache_write_tokens", "usage_reported_calls"):
        old.pop(key)
    restored = TurnTrace.model_validate(old)
    assert restored.model_call_timings == ()
    assert restored.usage_reported_calls == 0


def test_production_client_uses_header_hooks_without_payload_changes():
    provider = OpenAIProvider(api_key="test", base_url="https://unit.test/v1")
    client = provider._make_sdk_client(streaming_retry_owned=True)
    try:
        assert client._client.event_hooks["request"] == [on_http_request]
        assert client._client.event_hooks["response"] == [on_http_response]
        assert client.max_retries == 0
        assert client.timeout.read == 300
    finally:
        client.close()


def test_stop_before_first_chunk_does_not_pollute_next_turn(tmp_path):
    engine, provider = _engine(tmp_path, [])
    ready, release = threading.Event(), threading.Event()
    def stalled(**kwargs):
        on_http_request(None)
        ready.set()
        assert release.wait(5)
        on_http_response(None)
        yield StreamChunk(text_delta="late")
    provider.stream = stalled
    traces = []
    engine.trace_sink = traces.append
    async def run():
        task = asyncio.create_task(_run())
        assert await asyncio.to_thread(ready.wait, 5)
        engine.request_interrupt()
        await asyncio.wait_for(task, 2)
        assert traces[0].model_call_timings[0].status == "interrupted"
        saved = traces[0].model_dump_json()
        provider.stream = lambda **kwargs: iter([StreamChunk(turn=AssistantTurn(text="done"))])
        await _run()
        release.set()
        assert traces[0].model_dump_json() == saved
    async def _run():
        return [e async for e in engine.run("go")]
    try:
        asyncio.run(run())
    finally:
        release.set()
    assert len(traces) == 2
    assert traces[0].model_call_timings[0].http_requests[0].headers_ms is None
    assert traces[1].model_call_timings[0].http_requests == ()


def test_benchmark_keeps_missing_quality_and_usage_distinct_from_zero():
    from scripts.summarize_answer_benchmark import summarize, distribution
    trace = TurnTraceRecorder(session_id="s", model="m", plan=None).finish().model_dump()
    trace["stage_elapsed_ms"] = {"total": 100}
    row = {"case_id": "sci99_overview", "variant": "baseline", "configuration_id": "same-model",
           "measurement_kind": "offline", "trace": trace}
    groups = summarize([row, {**row, "measurement_kind": "live", "quality": {"factuality": 0}}])["groups"]
    assert len(groups) == 2
    live, offline = groups
    assert offline["metrics"]["input_tokens"]["median"] is None
    assert offline["metrics"]["first_engine_text_ms"]["median"] is None
    assert offline["quality"]["factuality"]["median"] is None
    assert live["quality"]["factuality"]["median"] == 0
    assert offline["metrics"]["total_ms"]["p95"] is None
    assert distribution(list(range(1, 21)))["p95"] == 19
    assert distribution([float("nan"), float("inf"), True, -1, None])["n"] == 0
    with pytest.raises(ValueError):
        summarize([{**row, "measurement_kind": "unknown"}])
