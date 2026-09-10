"""P0 gate tests — provider layer. SDK-free (inject a fake OpenAI client)."""

from __future__ import annotations

import json
from types import SimpleNamespace

from coworker.providers import (
    AssistantTurn,
    ModelCapabilities,
    OpenAIProvider,
    ToolCall,
    capabilities_for,
)


class _FakeCompletions:
    def __init__(self, response):
        self._response = response
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class _FakeClient:
    def __init__(self, response):
        self.chat = SimpleNamespace(completions=_FakeCompletions(response))


def _response(content=None, tool_calls=None, finish_reason="stop"):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice])


def test_complete_returns_text():
    client = _FakeClient(_response(content="hello there"))
    provider = OpenAIProvider(client=client)

    turn = provider.complete(
        model="gpt-5.5", messages=[{"role": "user", "content": "hi"}]
    )

    assert isinstance(turn, AssistantTurn)
    assert turn.text == "hello there"
    assert turn.tool_calls == []
    assert turn.has_tool_calls is False
    assert turn.finish_reason == "stop"


def test_complete_parses_tool_calls():
    tc = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(
            name="read_file", arguments=json.dumps({"path": "a.py"})
        ),
    )
    client = _FakeClient(_response(tool_calls=[tc], finish_reason="tool_calls"))
    provider = OpenAIProvider(client=client)

    turn = provider.complete(
        model="gpt-5.5",
        messages=[],
        tools=[{"type": "function", "function": {"name": "read_file"}}],
    )

    assert turn.has_tool_calls
    assert turn.tool_calls[0] == ToolCall(
        id="call_1", name="read_file", arguments={"path": "a.py"}
    )
    # tools forwarded to the API
    assert "tools" in client.chat.completions.calls[0]


def test_complete_tolerates_bad_tool_args():
    tc = SimpleNamespace(
        id="call_2", function=SimpleNamespace(name="x", arguments="{not json")
    )
    client = _FakeClient(_response(tool_calls=[tc]))
    provider = OpenAIProvider(client=client)

    turn = provider.complete(model="gpt-5.5", messages=[])

    assert turn.tool_calls[0].arguments == {"_raw": "{not json"}


def test_tools_omitted_when_none():
    client = _FakeClient(_response(content="x"))
    provider = OpenAIProvider(client=client)

    provider.complete(model="gpt-5.5", messages=[])

    assert "tools" not in client.chat.completions.calls[0]


def test_settings_forwarded():
    client = _FakeClient(_response(content="x"))
    provider = OpenAIProvider(client=client)

    provider.complete(model="gpt-5.5", messages=[], temperature=0.2)

    assert client.chat.completions.calls[0]["temperature"] == 0.2


def test_capabilities_known_models():
    assert capabilities_for("gpt-5.5").tools is True
    assert capabilities_for("openai:gpt-5.5").vision is True  # provider prefix stripped
    assert capabilities_for("o3-mini").parallel_tool_calls is False
    assert capabilities_for("deepseek-chat").tools is True


def test_capabilities_via_provider():
    provider = OpenAIProvider(client=_FakeClient(_response()))
    caps = provider.capabilities("gpt-5.5")
    assert isinstance(caps, ModelCapabilities)
    assert caps.tools is True


# -- GPT-5.6 tools + reasoning_effort on chat/completions (owner repro 2026-07-14) ----
# The API defaults these models to effort "medium" and then rejects function tools:
# "Function tools with reasoning_effort are not supported for gpt-5.6-sol in
# /v1/chat/completions. To use function tools, use /v1/responses or set
# reasoning_effort to 'none'." Until we speak the Responses API, we pin effort none.

_TOOLS = [{"type": "function", "function": {"name": "read_file"}}]
_EFFORT_400 = (
    "Error code: 400 - {'error': {'message': \"Function tools with reasoning_effort "
    "are not supported for %s in /v1/chat/completions. To use function tools, use "
    "/v1/responses or set reasoning_effort to 'none'.\", 'type': "
    "'invalid_request_error', 'param': 'reasoning_effort', 'code': None}}"
)


def test_gpt56_tools_pin_reasoning_effort_none():
    client = _FakeClient(_response(content="x"))
    provider = OpenAIProvider(client=client)
    calls = client.chat.completions.calls

    for model in ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"):
        provider.complete(model=model, messages=[], tools=_TOOLS)
    assert [c["reasoning_effort"] for c in calls] == ["none"] * 3

    # an explicit caller choice is respected on the first attempt
    provider.complete(
        model="gpt-5.6-sol", messages=[], tools=_TOOLS, reasoning_effort="low"
    )
    assert calls[3]["reasoning_effort"] == "low"

    # no tools, or another model → the request is untouched
    provider.complete(model="gpt-5.6-sol", messages=[])
    provider.complete(model="gpt-5.5", messages=[], tools=_TOOLS)
    assert "reasoning_effort" not in calls[4] and "reasoning_effort" not in calls[5]


class _EffortRejectingCompletions:
    """Behaves like the live API: tools + any effort other than 'none' → the 400."""

    def __init__(self, response):
        self._response = response
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("tools") and kwargs.get("reasoning_effort") != "none":
            raise RuntimeError(_EFFORT_400 % kwargs["model"])
        if kwargs.get("stream"):
            return iter([_chunk(content="ok"), _chunk(finish="stop")])
        return self._response


def test_effort_400_from_an_unpinned_model_retries_once_at_none():
    # a hypothetical next generation we haven't listed yet — proactive pin misses it
    client = _FakeClient(_response(content="x"))
    client.chat.completions = _EffortRejectingCompletions(_response(content="x"))
    provider = OpenAIProvider(client=client)

    turn = provider.complete(model="gpt-5.7-sol", messages=[], tools=_TOOLS)
    calls = client.chat.completions.calls
    assert turn.text == "x" and len(calls) == 2
    assert "reasoning_effort" not in calls[0] and calls[1]["reasoning_effort"] == "none"

    # streaming path retries the same way
    out = list(provider.stream(model="gpt-5.7-sol", messages=[], tools=_TOOLS))
    assert out[-1].turn.text == "ok" and len(client.chat.completions.calls) == 4


def test_max_tokens_rejection_retries_as_max_completion_tokens():
    """Reasoning-routed models 400 on max_tokens (want max_completion_tokens); compat
    servers know only max_tokens — so the swap happens on rejection, never up front.
    (Owner-hit 2026-07-20: the auto-title call silently no-oped on gpt-5.6-sol.)"""

    class _MaxTokensRejecting:
        def __init__(self, response):
            self._response = response
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if "max_tokens" in kwargs:
                raise RuntimeError(
                    "Error code: 400 - Unsupported parameter: 'max_tokens' is not "
                    "supported with this model. Use 'max_completion_tokens' instead."
                )
            return self._response

    client = _FakeClient(_response(content="Jira vs Linear"))
    client.chat.completions = _MaxTokensRejecting(_response(content="Jira vs Linear"))
    provider = OpenAIProvider(client=client)

    turn = provider.complete(model="gpt-5.6-sol", messages=[], max_tokens=64)
    calls = client.chat.completions.calls
    assert turn.text == "Jira vs Linear" and len(calls) == 2
    assert calls[0]["max_tokens"] == 64
    assert "max_tokens" not in calls[1] and calls[1]["max_completion_tokens"] == 64


def test_unsupported_reasoning_effort_is_dropped_for_compat_gateway():
    class _ReasoningEffortRejecting:
        def __init__(self, response):
            self._response = response
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if "reasoning_effort" in kwargs:
                raise RuntimeError(
                    "Error code: 400 - Unsupported parameter: 'reasoning_effort'"
                )
            return self._response

    client = _FakeClient(_response(content="summary"))
    client.chat.completions = _ReasoningEffortRejecting(_response(content="summary"))
    provider = OpenAIProvider(client=client)

    turn = provider.complete(
        model="compat-summary-model",
        messages=[{"role": "user", "content": "summarize"}],
        reasoning_effort="none",
    )

    calls = client.chat.completions.calls
    assert turn.text == "summary" and len(calls) == 2
    assert calls[0]["reasoning_effort"] == "none"
    assert "reasoning_effort" not in calls[1]


def test_unrelated_400s_are_not_retried():
    class _AlwaysRejects:
        calls: list = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            raise RuntimeError("Error code: 400 - context_length_exceeded")

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _AlwaysRejects()
    provider = OpenAIProvider(client=client)
    try:
        provider.complete(model="gpt-5.5", messages=[], tools=_TOOLS)
        raise AssertionError("should have raised")
    except RuntimeError:
        pass
    assert len(client.chat.completions.calls) == 1  # no blind second attempt


# -- streaming ------------------------------------------------------------------


def _chunk(content=None, tool_call=None, finish=None, reasoning=None):
    delta = SimpleNamespace(
        content=content,
        tool_calls=[tool_call] if tool_call else None,
        reasoning_content=reasoning,
    )
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=finish)])


class _StreamClient:
    def __init__(self, chunks):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: iter(chunks))
        )


def test_stream_text_deltas():
    chunks = [_chunk(content="Hel"), _chunk(content="lo"), _chunk(finish="stop")]
    provider = OpenAIProvider(client=_StreamClient(chunks))
    out = list(provider.stream(model="gpt-5.5", messages=[]))
    assert [c.text_delta for c in out if c.text_delta] == ["Hel", "lo"]
    assert out[-1].turn.text == "Hello"
    assert out[-1].turn.finish_reason == "stop"


def test_opencode_go_stream_uses_per_request_session_header():
    chunks = [_chunk(content="ok"), _chunk(finish="stop")]
    client = _FakeClient(_response(content="unused"))
    client.chat.completions = _FakeCompletions(iter(chunks))
    provider = OpenAIProvider(
        client=client, base_url="https://opencode.ai/zen/go/v1/"
    )

    list(
        provider.stream(
            model="deepseek-v4-flash",
            messages=[],
            _opencode_session_id="session-a",
        )
    )

    request = client.chat.completions.calls[0]
    assert request["extra_headers"]["x-opencode-session"] == "session-a"
    assert "_opencode_session_id" not in request


def test_opencode_go_complete_session_is_stable_and_per_conversation():
    client = _FakeClient(_response(content="ok"))
    provider = OpenAIProvider(
        client=client, base_url="https://opencode.ai/zen/go/v1"
    )

    for session_id in ("session-a", "session-a", "session-b"):
        provider.complete(
            model="deepseek-v4-flash",
            messages=[],
            _opencode_session_id=session_id,
        )

    requests = client.chat.completions.calls
    assert [
        request["extra_headers"]["x-opencode-session"] for request in requests
    ] == ["session-a", "session-a", "session-b"]
    assert all("_opencode_session_id" not in request for request in requests)


def test_non_opencode_compatible_endpoint_has_no_automatic_session_header():
    client = _FakeClient(_response(content="ok"))
    provider = OpenAIProvider(client=client, base_url="https://compat.example/v1")

    provider.complete(
        model="deepseek-v4-flash",
        messages=[],
        _opencode_session_id="session-a",
    )

    request = client.chat.completions.calls[0]
    assert "extra_headers" not in request
    assert "_opencode_session_id" not in request


def test_opencode_endpoint_match_rejects_lookalike_host_and_path():
    from coworker.providers.openai_provider import _is_opencode_go_endpoint

    assert _is_opencode_go_endpoint("https://opencode.ai/zen/go/v1")
    assert _is_opencode_go_endpoint("https://opencode.ai/zen/go/v1/chat/completions")
    assert not _is_opencode_go_endpoint("https://evil.example/opencode.ai/zen/go/v1")
    assert not _is_opencode_go_endpoint("https://opencode.ai/zen/other/v1")


def test_stream_tools_none_yields_deltas_before_upstream_finishes():
    """tools=None must true-stream: first delta is visible before later chunks arrive."""
    import threading

    release_rest = threading.Event()
    first_pulled = threading.Event()

    class _GatedStream:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)

            def _gen():
                yield _chunk(content="Hel")
                assert first_pulled.wait(timeout=2.0), "consumer never pulled first delta"
                assert release_rest.wait(timeout=2.0), "test never released remaining chunks"
                yield _chunk(content="lo")
                yield _chunk(finish="stop")

            return _gen()

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _GatedStream()
    provider = OpenAIProvider(client=client)
    it = iter(provider.stream(model="gpt-5.5", messages=[]))
    first = next(it)
    assert first.text_delta == "Hel"
    first_pulled.set()
    release_rest.set()
    rest = list(it)
    assert [c.text_delta for c in rest if c.text_delta] == ["lo"]
    assert rest[-1].turn.text == "Hello"


def test_stream_accumulates_tool_calls():
    tc1 = SimpleNamespace(
        index=0,
        id="call_1",
        function=SimpleNamespace(name="read_file", arguments='{"pa'),
    )
    tc2 = SimpleNamespace(
        index=0, id=None, function=SimpleNamespace(name=None, arguments='th": "a.py"}')
    )
    chunks = [_chunk(tool_call=tc1), _chunk(tool_call=tc2), _chunk(finish="tool_calls")]
    provider = OpenAIProvider(client=_StreamClient(chunks))
    turn = list(provider.stream(model="gpt-5.5", messages=[]))[-1].turn
    assert turn.tool_calls[0] == ToolCall(
        id="call_1", name="read_file", arguments={"path": "a.py"}
    )


def test_stream_salvages_textual_tool_call_on_final_turn():
    """Compat-buffered tools path: salvage into structured tool_calls and never leak
    the raw textual tool-call blob as ASSISTANT_DELTA text_delta."""
    blob = '{"name": "get_weather", "arguments": {"city": "Paris"}}'
    tools = [{"type": "function", "function": {"name": "get_weather"}}]
    chunks = [
        _chunk(content=blob[:20]),
        _chunk(content=blob[20:]),
        _chunk(finish="stop"),
    ]
    provider = OpenAIProvider(client=_StreamClient(chunks))
    out = list(provider.stream(model="ollama:x", messages=[], tools=tools))
    assert [c.text_delta for c in out if c.text_delta] == []
    turn = out[-1].turn
    assert turn.text is None
    assert turn.has_tool_calls
    assert turn.tool_calls[0].name == "get_weather"
    assert turn.tool_calls[0].arguments == {"city": "Paris"}


def test_stream_does_not_salvage_textual_tool_call_without_tools():
    blob = '{"name": "get_weather", "arguments": {"city": "Paris"}}'
    chunks = [_chunk(content=blob), _chunk(finish="stop")]
    provider = OpenAIProvider(client=_StreamClient(chunks))
    turn = list(provider.stream(model="ollama:x", messages=[]))[-1].turn
    assert not turn.has_tool_calls
    assert turn.text == blob


def test_stream_malformed_structured_tool_args_keep_raw():
    tc = SimpleNamespace(
        index=0,
        id="call_bad",
        function=SimpleNamespace(name="x", arguments="{not json"),
    )
    chunks = [_chunk(tool_call=tc), _chunk(finish="tool_calls")]
    provider = OpenAIProvider(client=_StreamClient(chunks))
    turn = list(provider.stream(model="gpt-5.5", messages=[]))[-1].turn
    assert turn.tool_calls[0] == ToolCall(
        id="call_bad", name="x", arguments={"_raw": "{not json"}
    )


# -- HARD STOP F: structured-tools true streaming (known-safe + kill switch) -----


def _tools_read_file():
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            },
        }
    ]


def test_known_safe_structured_tools_streaming_matrix():
    from coworker.providers.openai_provider import (
        is_known_safe_structured_tools_streaming,
    )

    assert is_known_safe_structured_tools_streaming("gpt-5.5", base_url=None)
    assert is_known_safe_structured_tools_streaming(
        "openai:gpt-4o", base_url="https://api.openai.com/v1"
    )
    assert is_known_safe_structured_tools_streaming(
        "gpt-5.6",
        base_url="https://my-resource.openai.azure.com/openai/v1",
    )
    # OpenAI-compatible alone is NOT known-safe — even with a gpt-* model name.
    assert not is_known_safe_structured_tools_streaming(
        "gpt-5.5", base_url="https://custom.example/v1"
    )
    assert not is_known_safe_structured_tools_streaming(
        "gpt-5.6-luna", base_url="https://www.tokenfoundryx.com/v1"
    )
    # D-164: live PASS pairs on apihub.chem-cloud.cn are known-safe.
    assert is_known_safe_structured_tools_streaming(
        "deepseek-v4-flash", base_url="https://apihub.chem-cloud.cn/v1"
    )
    assert is_known_safe_structured_tools_streaming(
        "deepseek-v4-pro", base_url="https://apihub.chem-cloud.cn/v1"
    )
    assert is_known_safe_structured_tools_streaming(
        "glm-5.2", base_url="https://apihub.chem-cloud.cn/v1"
    )
    assert not is_known_safe_structured_tools_streaming(
        "kimi-k3", base_url="https://apihub.chem-cloud.cn/v1"
    )
    assert not is_known_safe_structured_tools_streaming(
        "deepseek-v4-flash", base_url="https://www.tokenfoundryx.com/v1"
    )
    assert not is_known_safe_structured_tools_streaming(
        "deepseek-v4-pro", base_url="https://www.tokenfoundryx.com/v1"
    )
    assert not is_known_safe_structured_tools_streaming(
        "glm-5.2", base_url="https://custom.example/v1"
    )
    assert not is_known_safe_structured_tools_streaming(
        "ollama:qwen3", base_url="http://localhost:11434/v1"
    )
    assert not is_known_safe_structured_tools_streaming(
        "qwen-plus", base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )


def test_structured_tools_true_streaming_kill_switch_off_stays_compat_buffered():
    """Explicit kill switch OFF: tools path remains buffered, even for gpt-*."""
    import threading

    release_rest = threading.Event()
    first_pulled = threading.Event()
    tools = _tools_read_file()

    class _GatedStream:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)

            def _gen():
                yield _chunk(content="Hel")
                # If true-streaming leaked, consumer would pull before release.
                # Compat path buffers everything first, so this runs before next().
                assert not first_pulled.is_set()
                yield _chunk(content="lo")
                yield _chunk(finish="stop")
                release_rest.set()

            return _gen()

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _GatedStream()
    provider = OpenAIProvider(client=client)  # stock OpenAI host (known-safe model)
    out = list(
        provider.stream(
            model="gpt-5.5",
            messages=[],
            tools=tools,
            # kill switch OFF: omit flag / False
            structured_tools_true_streaming_enabled=False,
        )
    )
    assert release_rest.is_set()
    assert [c.text_delta for c in out if c.text_delta] == ["Hel", "lo"]
    assert out[-1].turn.text == "Hello"
    # Internal flag must not leak into the OpenAI request kwargs.
    assert "structured_tools_true_streaming_enabled" not in client.chat.completions.calls[0]


def test_structured_tools_true_streaming_known_safe_yields_before_upstream_finishes():
    """Kill switch ON + known-safe: text deltas stream live; split tool args accumulate."""
    import threading

    release_rest = threading.Event()
    first_pulled = threading.Event()
    tools = _tools_read_file()
    tc1 = SimpleNamespace(
        index=0,
        id="call_1",
        function=SimpleNamespace(name="read_file", arguments='{"pa'),
    )
    tc2 = SimpleNamespace(
        index=0, id=None, function=SimpleNamespace(name=None, arguments='th":"a.py"}')
    )

    class _GatedStream:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)

            def _gen():
                yield _chunk(content="Looking")
                assert first_pulled.wait(timeout=2.0), "consumer never pulled first delta"
                assert release_rest.wait(timeout=2.0), "test never released remaining chunks"
                yield _chunk(tool_call=tc1)
                yield _chunk(tool_call=tc2)
                yield _chunk(finish="tool_calls")

            return _gen()

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _GatedStream()
    provider = OpenAIProvider(client=client)
    it = iter(
        provider.stream(
            model="gpt-5.5",
            messages=[],
            tools=tools,
            structured_tools_true_streaming_enabled=True,
        )
    )
    first = next(it)
    assert first.text_delta == "Looking"
    first_pulled.set()
    release_rest.set()
    rest = list(it)
    assert [c.text_delta for c in rest if c.text_delta] == []
    turn = rest[-1].turn
    assert turn.text == "Looking"
    assert turn.tool_calls == [
        ToolCall(id="call_1", name="read_file", arguments={"path": "a.py"})
    ]
    assert "structured_tools_true_streaming_enabled" not in client.chat.completions.calls[0]


def test_structured_tools_true_streaming_unknown_compat_stays_buffered_even_when_on():
    """Unknown/custom OpenAI-compatible endpoint: never assume structured-tool-safe."""
    import threading

    release_rest = threading.Event()
    tools = _tools_read_file()

    class _GatedStream:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)

            def _gen():
                yield _chunk(content="Hel")
                yield _chunk(content="lo")
                yield _chunk(finish="stop")
                release_rest.set()

            return _gen()

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _GatedStream()
    provider = OpenAIProvider(client=client, base_url="https://custom.example/v1")
    out = list(
        provider.stream(
            model="gpt-5.5",
            messages=[],
            tools=tools,
            structured_tools_true_streaming_enabled=True,
        )
    )
    assert release_rest.is_set()
    assert [c.text_delta for c in out if c.text_delta] == ["Hel", "lo"]
    assert out[-1].turn.text == "Hello"


def test_structured_tools_true_streaming_apihub_cn_pair_yields_before_upstream_finishes(
    monkeypatch,
):
    """D-161: listed ApiHub CN pair + kill switch ON uses true streaming (not buffered)."""
    import threading

    from coworker.providers import openai_provider as m

    monkeypatch.setattr(
        m,
        "_KNOWN_SAFE_COMPAT_PAIRS",
        frozenset({("apihub.chem-cloud.cn", "deepseek-v4-flash")}),
    )
    release_rest = threading.Event()
    first_pulled = threading.Event()
    tools = _tools_read_file()

    class _GatedStream:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)

            def _gen():
                yield _chunk(content="Looking")
                assert first_pulled.wait(timeout=2.0), "consumer never pulled first delta"
                assert release_rest.wait(timeout=2.0), "test never released remaining chunks"
                yield _chunk(finish="stop")

            return _gen()

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _GatedStream()
    provider = OpenAIProvider(
        client=client, base_url="https://apihub.chem-cloud.cn/v1"
    )
    it = iter(
        provider.stream(
            model="deepseek-v4-flash",
            messages=[],
            tools=tools,
            structured_tools_true_streaming_enabled=True,
        )
    )
    first = next(it)
    assert first.text_delta == "Looking"
    first_pulled.set()
    release_rest.set()
    rest = list(it)
    assert rest[-1].turn.text == "Looking"


def test_structured_tools_kill_switch_off_buffers_even_for_apihub_cn_pair(monkeypatch):
    """Kill switch OFF restores buffering even when the D-161 pair is listed."""
    import threading

    from coworker.providers import openai_provider as m

    monkeypatch.setattr(
        m,
        "_KNOWN_SAFE_COMPAT_PAIRS",
        frozenset({("apihub.chem-cloud.cn", "deepseek-v4-flash")}),
    )
    release_rest = threading.Event()
    first_pulled = threading.Event()
    tools = _tools_read_file()

    class _GatedStream:
        def create(self, **kwargs):
            def _gen():
                yield _chunk(content="Hel")
                assert not first_pulled.is_set()
                yield _chunk(content="lo")
                yield _chunk(finish="stop")
                release_rest.set()

            return _gen()

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _GatedStream()
    provider = OpenAIProvider(
        client=client, base_url="https://apihub.chem-cloud.cn/v1"
    )
    out = list(
        provider.stream(
            model="deepseek-v4-flash",
            messages=[],
            tools=tools,
            structured_tools_true_streaming_enabled=False,
        )
    )
    assert release_rest.is_set()
    assert [c.text_delta for c in out if c.text_delta] == ["Hel", "lo"]

    """OFF must seamlessly restore compat-buffered + textual salvage (no UI leak)."""
    blob = '{"name": "read_file", "arguments": {"path": "a.py"}}'
    tools = _tools_read_file()
    chunks = [
        _chunk(content=blob[:18]),
        _chunk(content=blob[18:]),
        _chunk(finish="stop"),
    ]
    provider = OpenAIProvider(client=_StreamClient(chunks))
    out = list(
        provider.stream(
            model="gpt-5.5",
            messages=[],
            tools=tools,
            structured_tools_true_streaming_enabled=False,
        )
    )
    assert [c.text_delta for c in out if c.text_delta] == []
    turn = out[-1].turn
    assert turn.text is None
    assert turn.tool_calls[0].name == "read_file"
    assert turn.tool_calls[0].arguments == {"path": "a.py"}


def test_stream_usage_only_chunk_does_not_block_retry():
    """Usage-only / empty-choices heartbeat is not semantic progress."""

    class _UsageThenFailThenOk:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            stream_n = sum(1 for c in self.calls if c.get("stream"))
            if kwargs.get("stream"):
                if stream_n == 1:
                    usage = SimpleNamespace(
                        prompt_tokens=3,
                        completion_tokens=0,
                        prompt_tokens_details=None,
                    )

                    def _gen():
                        yield SimpleNamespace(choices=[], usage=usage)
                        raise RuntimeError(
                            "peer closed connection without sending complete "
                            "message body (incomplete chunked read)"
                        )

                    return _gen()
                return iter([_chunk(content="OK"), _chunk(finish="stop")])
            return _response(content="unused")

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _UsageThenFailThenOk()
    provider = OpenAIProvider(client=client)
    out = list(provider.stream(model="gpt-5.5", messages=[]))
    assert [c.text_delta for c in out if c.text_delta] == ["OK"]
    assert sum(1 for c in client.chat.completions.calls if c.get("stream")) == 2


def test_stream_retries_incomplete_chunked_read_without_duplicating_deltas():
    """No semantic progress yet → one ChemClaw retry; never flush a dead partial."""

    class _FlakyThenOk:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            stream_n = sum(1 for c in self.calls if c.get("stream"))
            if kwargs.get("stream"):
                if stream_n == 1:
                    raise RuntimeError(
                        "peer closed connection without sending complete "
                        "message body (incomplete chunked read)"
                    )
                return iter(
                    [_chunk(content="OK"), _chunk(finish="stop")]
                )
            return _response(content="should-not-use-fallback")

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _FlakyThenOk()
    provider = OpenAIProvider(client=client)
    out = list(provider.stream(model="gpt-5.5", messages=[]))
    assert [c.text_delta for c in out if c.text_delta] == ["OK"]
    assert out[-1].turn.text == "OK"
    assert sum(1 for c in client.chat.completions.calls if c.get("stream")) == 2


def test_stream_falls_back_to_nonstream_after_transport_failures():
    class _StreamAlwaysDies:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("stream"):
                raise RuntimeError(
                    "peer closed connection without sending complete "
                    "message body (incomplete chunked read)"
                )
            return _response(content="from-nonstream")

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _StreamAlwaysDies()
    provider = OpenAIProvider(client=client)
    out = list(provider.stream(model="gpt-5.5", messages=[]))
    assert out[-1].turn is not None
    assert out[-1].turn.text == "from-nonstream"
    assert sum(1 for c in client.chat.completions.calls if c.get("stream")) == 2
    assert any(not c.get("stream") for c in client.chat.completions.calls)


def test_opencode_stream_fallback_keeps_session_header():
    class _StreamAlwaysDies:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("stream"):
                raise RuntimeError(
                    "peer closed connection without sending complete "
                    "message body (incomplete chunked read)"
                )
            return _response(content="from-nonstream")

    client = _FakeClient(_response(content="unused"))
    client.chat.completions = _StreamAlwaysDies()
    provider = OpenAIProvider(
        client=client, base_url="https://opencode.ai/zen/go/v1"
    )

    out = list(
        provider.stream(
            model="deepseek-v4-flash",
            messages=[],
            _opencode_session_id="session-fallback",
        )
    )

    assert out[-1].turn.text == "from-nonstream"
    assert len(client.chat.completions.calls) == 3
    assert all(
        call["extra_headers"]["x-opencode-session"] == "session-fallback"
        for call in client.chat.completions.calls
    )
    assert all(
        "_opencode_session_id" not in call
        for call in client.chat.completions.calls
    )


def test_concurrent_streams_use_distinct_sdk_clients():
    """Two sessions stream on one OpenAIProvider via thread-pool workers. Each stream must
    own a fresh SDK client so overlapping chunked bodies cannot tear each other down
    (ChemClaw: switch chat mid-answer → Connection error on the background turn)."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    built: list[object] = []
    lock = threading.Lock()

    class _FakeSDK:
        def __init__(self):
            self.closed = False
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kw: iter(
                        [_chunk(content=f"ok-{id(self)}"), _chunk(finish="stop")]
                    )
                )
            )
            with lock:
                built.append(self)

        def close(self) -> None:
            self.closed = True

    provider = OpenAIProvider(api_key="sk-test", base_url="https://example.test/v1")
    provider._make_sdk_client = lambda **kw: _FakeSDK()  # type: ignore[method-assign]

    def _run():
        return list(provider.stream(model="kimi-k2.5", messages=[]))

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_run)
        f2 = pool.submit(_run)
        out1, out2 = f1.result(), f2.result()

    assert out1[-1].turn and out2[-1].turn
    assert len(built) == 2
    assert built[0] is not built[1]
    assert all(c.closed for c in built)


def test_stream_retries_generic_connection_error(monkeypatch):
    """OpenAI SDK's APIConnectionError default message is 'Connection error.' — treat like
    other stream transport failures so a parallel-session flake can retry/fallback."""

    class _ConnThenOk:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            stream_n = sum(1 for c in self.calls if c.get("stream"))
            if kwargs.get("stream"):
                if stream_n == 1:
                    raise RuntimeError("Connection error.")
                return iter([_chunk(content="recovered"), _chunk(finish="stop")])
            return _response(content="unused")

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _ConnThenOk()
    provider = OpenAIProvider(client=client)
    out = list(provider.stream(model="gpt-5.5", messages=[]))
    assert [c.text_delta for c in out if c.text_delta] == ["recovered"]


def _transport_after_first_delta(*, kind: str):
    """Fake completions: first stream attempt emits one semantic delta then dies."""

    class _BoomAfterProgress:
        def __init__(self):
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if not kwargs.get("stream"):
                return _response(content="fallback-should-not-run")
            if kind == "text":
                first = _chunk(content="partial-")
            elif kind == "reasoning":
                first = _chunk(reasoning="think-")
            elif kind == "structured_tool":
                tc = SimpleNamespace(
                    index=0,
                    id="call_1",
                    function=SimpleNamespace(name="read_file", arguments='{"p":'),
                )
                first = _chunk(tool_call=tc)
            elif kind == "textual_tool_candidate":
                first = _chunk(content='{"name": "get_weather"')
            else:
                raise AssertionError(kind)

            def _boom():
                yield first
                raise RuntimeError(
                    "peer closed connection without sending complete "
                    "message body (incomplete chunked read)"
                )

            return _boom()

    return _BoomAfterProgress()


def test_stream_no_retry_after_text_progress():
    import pytest

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _transport_after_first_delta(kind="text")
    provider = OpenAIProvider(client=client)
    with pytest.raises(RuntimeError, match="incomplete chunked read"):
        list(provider.stream(model="gpt-5.5", messages=[]))
    assert sum(1 for c in client.chat.completions.calls if c.get("stream")) == 1


def test_stream_no_retry_after_reasoning_progress():
    import pytest

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _transport_after_first_delta(kind="reasoning")
    provider = OpenAIProvider(client=client)
    with pytest.raises(RuntimeError, match="incomplete chunked read"):
        list(provider.stream(model="gpt-5.5", messages=[]))
    assert sum(1 for c in client.chat.completions.calls if c.get("stream")) == 1


def test_stream_no_retry_after_structured_tool_progress():
    import pytest

    client = _FakeClient(_response(content="x"))
    client.chat.completions = _transport_after_first_delta(kind="structured_tool")
    provider = OpenAIProvider(client=client)
    with pytest.raises(RuntimeError, match="incomplete chunked read"):
        list(provider.stream(model="gpt-5.5", messages=[]))
    assert sum(1 for c in client.chat.completions.calls if c.get("stream")) == 1


def test_stream_no_retry_after_textual_tool_candidate_progress():
    import pytest

    tools = [{"type": "function", "function": {"name": "get_weather"}}]
    client = _FakeClient(_response(content="x"))
    client.chat.completions = _transport_after_first_delta(
        kind="textual_tool_candidate"
    )
    provider = OpenAIProvider(client=client)
    with pytest.raises(RuntimeError, match="incomplete chunked read"):
        list(provider.stream(model="ollama:x", messages=[], tools=tools))
    assert sum(1 for c in client.chat.completions.calls if c.get("stream")) == 1


def test_sdk_client_kwargs_stream_owns_retry_with_explicit_timeout():
    from coworker.providers.openai_provider import _sdk_client_kwargs

    kw = _sdk_client_kwargs(
        api_key="sk-test",
        base_url="https://example.test/v1",
        streaming_retry_owned=True,
    )
    assert kw["max_retries"] == 0
    assert kw["api_key"] == "sk-test"
    assert kw["base_url"] == "https://example.test/v1"
    timeout = kw["timeout"]
    assert timeout.connect == 15.0
    assert timeout.read == 300.0
    assert timeout.write == 30.0
    assert timeout.pool == 15.0


def test_sdk_client_kwargs_complete_keeps_sdk_retry_ownership():
    from coworker.providers.openai_provider import _sdk_client_kwargs

    kw = _sdk_client_kwargs(api_key="sk-test", streaming_retry_owned=False)
    assert "max_retries" not in kw
    assert kw["timeout"].read == 300.0


def test_make_sdk_client_passes_streaming_retry_ownership(monkeypatch):
    captured: list[dict] = []

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            captured.append(kwargs)

    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeOpenAI)
    provider = OpenAIProvider(api_key="sk-test", base_url="https://example.test/v1")
    provider._make_sdk_client(streaming_retry_owned=True)
    provider._make_sdk_client(streaming_retry_owned=False)
    assert captured[0]["max_retries"] == 0
    assert "max_retries" not in captured[1]


# -- OpenAI-compatible vendor providers (Z AI, DeepSeek, Kimi, MiniMax, Qwen, xAI, Mistral) ------

COMPAT_VENDORS = {
    "apihub-cn": "https://apihub.chem-cloud.cn/v1",
    "apihub-intl": "https://www.tokenfoundryx.com/v1",
    "zai": "https://api.z.ai/api/paas/v4",
    "deepseek": "https://api.deepseek.com",
    "kimi": "https://api.moonshot.ai/v1",
    "minimax": "https://api.minimax.io/v1",
    "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "xai": "https://api.x.ai/v1",
    "mistral": "https://api.mistral.ai/v1",
}


def test_compat_vendor_descriptors_ship_prefilled_endpoints():
    from coworker.providers.registry import get_descriptor

    for name, endpoint in COMPAT_VENDORS.items():
        d = get_descriptor(name)
        assert d is not None and d.needs_key, name
        base = next(f for f in d.fields if f.key == "base_url")
        assert base.default == endpoint  # prefilled, editable
        assert not base.required  # blank falls back to the default in the builder
        assert "OpenAI-compatible" in d.blurb
        assert d.env_key and d.recommended_model


def test_compat_builder_defaults_and_profile_override(monkeypatch):
    from coworker.providers.registry import build_provider_client

    p = build_provider_client("zai", {"api_key": "zk"}, None)
    assert p._base_url == COMPAT_VENDORS["zai"]
    assert p._api_key == "zk"

    override = "https://open.bigmodel.cn/api/paas/v4"
    p2 = build_provider_client("zai", {"api_key": "zk", "base_url": override}, None)
    assert p2._base_url == override


def test_compat_builder_env_key_fallback(monkeypatch):
    from coworker.providers.registry import build_provider_client

    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
    p = build_provider_client("deepseek", {}, None)
    assert p._api_key == "ds-key"
    assert p._base_url == COMPAT_VENDORS["deepseek"]


def test_compat_builder_never_leaks_the_openai_key(monkeypatch):
    """A configured OPENAI_API_KEY must never be sent to a different vendor's endpoint —
    a missing vendor key fails fast with a vendor-named error instead."""
    import pytest

    from coworker.providers.registry import build_provider_client

    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-real")
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Kimi"):
        build_provider_client("kimi", {}, None)


def test_compat_models_route_and_get_tool_capabilities():
    from coworker.providers.router import ProviderRouter

    router = ProviderRouter.__new__(
        ProviderRouter
    )  # only using _provider_name (stateless)
    for model in (
        "apihub-cn:deepseek-v4-flash",
        "apihub-intl:gpt-5.6-luna",
        "zai:glm-5.2",
        "deepseek:deepseek-v4-flash",
        "kimi:kimi-k2.6",
        "minimax:MiniMax-M2.5",
        "qwen:qwen3-max",
        "xai:grok-4.3",
        "mistral:mistral-large-latest",
    ):
        prefix = model.split(":", 1)[0]
        assert router._provider_name(model) == prefix
        assert ProviderRouter._bare(model) == model.split(":", 1)[1]
        caps = capabilities_for(model)
        assert caps.tools and caps.streaming


def test_compat_recommended_models_are_in_the_suggested_lists():
    """set_provider only auto-adds the recommended model if it's in _suggested_models —
    keep the registry and the manager's COMPAT_MODELS table in lockstep."""
    from coworker.providers.registry import get_descriptor
    from coworker.server.manager import SessionManager

    for name in COMPAT_VENDORS:
        d = get_descriptor(name)
        assert d.recommended_model in SessionManager.COMPAT_MODELS[name], name


# -- curated model matrix (labels + capabilities by full routed id) -----------------


def test_matrix_answers_capabilities_for_reseller_ids():
    """Reseller ids ('together:zai-org/GLM-5.2') defeat the name-prefix heuristics — the
    matrix must answer them exactly, with tool calling on."""
    for mid in (
        "together:zai-org/GLM-5.2",
        "together:meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        "fireworks:accounts/fireworks/models/kimi-k2p6",
        "openrouter:z-ai/glm-5.2",
        "openrouter:meta-llama/llama-4-maverick",
    ):
        caps = capabilities_for(mid)
        assert caps.tools and caps.parallel_tool_calls and caps.streaming


def test_matrix_labels_and_custom_model_fallback():
    from coworker.providers.matrix import MATRIX, model_labels

    labels = model_labels()
    assert labels["together:zai-org/GLM-5.2"] == "GLM-5.2 · via Together"
    assert labels["zai:glm-5.2"] == "GLM-5.2 · Z AI"
    assert labels["apihub-cn:deepseek-v4-flash"] == "DeepSeek V4 Flash · via ApiHub CN"
    assert labels["apihub-intl:gpt-5.6-luna"] == "GPT-5.6 Luna · via ApiHub Intl"
    # Deliberately small: agent-capable current models only (owner call, 2026-07-04).
    assert len(MATRIX) < 80
    assert all(e.caps.tools for e in MATRIX.values())
    # A custom (unlisted) reseller model falls back to the conservative default — usable,
    # but at the user's own risk (no parallel tool calls assumed).
    caps = capabilities_for("together:some-org/Brand-New-Model")
    assert caps.tools and not caps.parallel_tool_calls


def test_reseller_descriptors_and_matrix_stay_in_lockstep():
    """Reseller suggested models derive from the matrix, and each descriptor's
    recommended model must be one of them (set_provider's auto-add depends on it)."""
    from coworker.providers.matrix import models_for_provider
    from coworker.providers.registry import get_descriptor

    for name in ("together", "fireworks", "openrouter"):
        d = get_descriptor(name)
        assert d is not None and d.needs_key
        curated = models_for_provider(name)
        assert curated and d.recommended_model in curated
        # full ids in the matrix must round-trip: prefix + bare == matrix key
        base = next(f for f in d.fields if f.key == "base_url")
        assert base.default.startswith("https://")


def test_foreign_sidecars_stripped_from_outbound_messages():
    """Provider-private sidecars (`_gemini` thought signatures et al) must never reach the
    OpenAI wire — it and its compat servers reject unknown message fields."""
    client = _FakeClient(_response(content="ok"))
    provider = OpenAIProvider(client=client)
    provider.complete(
        model="gpt-5.5",
        messages=[
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "prev", "_gemini": {"call_sigs": ["x"]}},
        ],
    )
    sent = client.chat.completions.calls[0]["messages"]
    assert sent[1] == {"role": "assistant", "content": "prev"}


def test_stream_reasoning_content_deltas():
    """DeepSeek-style thinking: reasoning_content deltas surface as reasoning chunks and
    land on the final turn — never mixed into the answer text."""
    def rchunk(text):
        delta = SimpleNamespace(content=None, tool_calls=None, reasoning_content=text)
        return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=None)])

    chunks = [rchunk("hmm "), rchunk("okay."), _chunk(content="Answer"), _chunk(finish="stop")]
    provider = OpenAIProvider(client=_StreamClient(chunks))
    out = list(provider.stream(model="deepseek-v4-pro", messages=[]))
    assert [c.reasoning_delta for c in out if c.reasoning_delta] == ["hmm ", "okay."]
    final = out[-1].turn
    assert final.text == "Answer" and final.reasoning == "hmm okay."


def test_complete_picks_up_reasoning_content():
    message = SimpleNamespace(content="Answer", tool_calls=None, reasoning_content="deep thought")
    choice = SimpleNamespace(message=message, finish_reason="stop")
    provider = OpenAIProvider(client=_FakeClient(SimpleNamespace(choices=[choice])))
    turn = provider.complete(model="deepseek-v4-pro", messages=[{"role": "user", "content": "x"}])
    assert turn.text == "Answer" and turn.reasoning == "deep thought"
    assert turn.extras == {"_openai": {"reasoning_content": "deep thought"}}


def test_reasoning_content_replayed_on_follow_up():
    """DeepSeek thinking mode: prior assistant reasoning_content must ride on the wire."""
    client = _FakeClient(_response(content="second"))
    provider = OpenAIProvider(client=client)
    history = [
        {"role": "user", "content": "first"},
        {
            "role": "assistant",
            "content": "done",
            "_openai": {"reasoning_content": "prior chain of thought"},
        },
        {"role": "user", "content": "second"},
    ]
    provider.complete(
        model="deepseek-v4-pro",
        messages=history,
        tools=[{"type": "function", "function": {"name": "read_file"}}],
    )
    sent = client.chat.completions.calls[0]["messages"][1]
    assert sent == {
        "role": "assistant",
        "content": "done",
        "reasoning_content": "prior chain of thought",
    }


def test_legacy_reasoning_sidecar_replayed_as_reasoning_content():
    """Older sessions stored thinking only on the display `reasoning` sidecar."""
    client = _FakeClient(_response(content="ok"))
    provider = OpenAIProvider(client=client)
    provider.complete(
        model="deepseek-v4-pro",
        messages=[
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": "prev",
                "reasoning": "legacy thinking",
            },
        ],
        tools=[{"type": "function", "function": {"name": "read_file"}}],
    )
    sent = client.chat.completions.calls[0]["messages"][1]
    assert sent == {
        "role": "assistant",
        "content": "prev",
        "reasoning_content": "legacy thinking",
    }


def test_stream_reasoning_content_sidecar_on_final_turn():
    def rchunk(text):
        delta = SimpleNamespace(content=None, tool_calls=None, reasoning_content=text)
        return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=None)])

    chunks = [rchunk("think"), _chunk(content="Answer"), _chunk(finish="stop")]
    provider = OpenAIProvider(client=_StreamClient(chunks))
    final = list(provider.stream(model="deepseek-v4-pro", messages=[]))[-1].turn
    assert final.extras == {"_openai": {"reasoning_content": "think"}}
