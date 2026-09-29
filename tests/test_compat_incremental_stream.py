"""Unknown endpoints keep tool salvage without delaying ordinary prose."""
from types import SimpleNamespace

import pytest

from coworker.providers.openai_provider import OpenAIProvider
from tests.test_providers import _chunk, _response, _FakeClient, _StreamClient, _tools_read_file


@pytest.mark.parametrize("kind", ["text", "reasoning"])
@pytest.mark.parametrize("enabled", [False, True])
def test_first_fragment_before_next_network_chunk(kind, enabled):
    consumed = []
    def chunks():
        yield _chunk(**({"content": "你好"} if kind == "text" else {"reasoning": "分析中"}))
        assert consumed == [kind], "provider buffered output until the next chunk"
        yield _chunk(content="！")
        yield _chunk(finish="stop")
    provider = OpenAIProvider(client=_StreamClient(chunks()), base_url="https://custom.example/v1")
    iterator = iter(provider.stream(model="deepseek-v4.1-flash", messages=[], tools=_tools_read_file(),
                                   structured_tools_true_streaming_enabled=enabled))
    first = next(iterator)
    assert first.text_delta if kind == "text" else first.reasoning_delta
    consumed.append(kind)
    assert list(iterator)[-1].turn.finish_reason == "stop"


@pytest.mark.parametrize("blob", [
    '{"name":"read_file","arguments":{"path":"a.py"}}',
    '<tool_call>{"name":"read_file","arguments":{"path":"a.py"}}</tool_call>',
    '<function=read_file><parameter=path>a.py</parameter></function>',
    'read_file {"path":"a.py"}',
    '```json\n{"name":"read_file","arguments":{"path":"a.py"}}\n```',
])
def test_split_textual_calls_never_leak_and_keep_visible_narration(blob):
    prefix = "正在读取。 "
    chunks = [_chunk(content=prefix)] + [_chunk(content=c) for c in blob] + [_chunk(finish="stop")]
    provider = OpenAIProvider(client=_StreamClient(chunks), base_url="https://custom.example/v1")
    out = list(provider.stream(model="custom", messages=[], tools=_tools_read_file()))
    assert "".join(c.text_delta or "" for c in out) == prefix
    assert out[-1].turn.text == prefix
    assert out[-1].turn.tool_calls[0].arguments == {"path": "a.py"}


def test_tool_names_with_shared_prefix_remain_intact():
    tools = [*_tools_read_file(), {"type": "function", "function": {"name": "read"}}]
    blob = 'read_file {"path":"a.py"}'
    chunks = [_chunk(content=c) for c in blob] + [_chunk(finish="stop")]
    out = list(OpenAIProvider(client=_StreamClient(chunks)).stream(model="custom", messages=[], tools=tools))
    assert not any(c.text_delta for c in out)
    assert out[-1].turn.tool_calls[0].name == "read_file"


@pytest.mark.parametrize("text", [
    '你好！可以帮你做资料研究。',
    '见[来源](https://example.test)。\n**结论**：有效。',
    '图表：\n```chart\n{"version":1,"type":"line","labels":["今天"],"series":[]}\n```',
    '代码：\n```python\nprint("hello")\n```\n完成。',
    '可以使用 read_file 读取资料。',
    '{}' * 1500,
])
def test_markdown_and_chart_content_remain_exact(text):
    provider = OpenAIProvider(client=_StreamClient([*[_chunk(content=c) for c in text], _chunk(finish="stop")]))
    out = list(provider.stream(model="custom", messages=[], tools=_tools_read_file()))
    assert "".join(c.text_delta or "" for c in out) == text
    assert out[-1].turn.text == text
    assert not out[-1].turn.tool_calls


def test_plain_markdown_does_not_hold_the_rest_until_terminal():
    displayed = []
    text = '见[来源](https://example.test)。\n```chart\n{"version":1,"type":"line"}\n```\n结论。'
    def chunks():
        for char in text:
            yield _chunk(content=char)
        assert "".join(displayed) == text
        yield _chunk(finish="stop")
    provider = OpenAIProvider(client=_StreamClient(chunks()))
    for chunk in provider.stream(model="custom", messages=[], tools=_tools_read_file()):
        if chunk.text_delta:
            displayed.append(chunk.text_delta)


@pytest.mark.parametrize("kind", ["text", "reasoning"])
def test_visible_fragments_disable_transport_replay(kind):
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        def chunks():
            yield _chunk(**({"content": "你好"} if kind == "text" else {"reasoning": "分析中"}))
            raise ConnectionError("connection reset")
        return chunks()
    client = _FakeClient(_response(content="must not replay"))
    client.chat.completions.create = create
    out = []
    with pytest.raises(ConnectionError):
        for item in OpenAIProvider(client=client).stream(model="custom", messages=[], tools=_tools_read_file()):
            out.append(item)
    assert len(calls) == 1 and len(out) == 1
    assert not any(c.turn for c in out)


@pytest.mark.parametrize("finish", [None, "length"])
def test_incomplete_structured_call_is_never_committed(finish):
    tc = SimpleNamespace(index=0, id="call_1", function=SimpleNamespace(name="read_file", arguments='{"path":'))
    chunks = [_chunk(content="读取中。"), _chunk(tool_call=tc)]
    if finish:
        chunks.append(_chunk(finish=finish))
    provider = OpenAIProvider(client=_StreamClient(chunks))
    out = []
    try:
        out = list(provider.stream(model="custom", messages=[], tools=_tools_read_file()))
    except ConnectionError:
        assert finish is None
    assert all(not c.turn or not c.turn.tool_calls for c in out)


def test_websocket_delivers_first_fragment_before_provider_finishes(tmp_path):
    from threading import Event
    from fastapi.testclient import TestClient
    from coworker.server.app import create_app
    from coworker.server.manager import SessionManager

    displayed = Event()
    def chunks():
        yield _chunk(content="你好")
        assert displayed.wait(5), "WebSocket waited for the completed answer"
        yield _chunk(content="！")
        yield _chunk(finish="stop")
    provider = OpenAIProvider(client=_StreamClient(chunks()), base_url="https://custom.example/v1")
    manager = SessionManager(workspace=tmp_path, model="deepseek-v4.1-flash", provider=provider)
    with TestClient(create_app(manager)) as client:
        with client.websocket_connect("/ws/session/stream-test?agent=cowork") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json({"type": "user_message", "text": "你好", "model": "deepseek-v4.1-flash"})
            events = []
            while True:
                event = ws.receive_json()
                events.append(event)
                if event["type"] == "assistant_delta":
                    displayed.set()
                if event["type"] == "turn_done":
                    break
    assert displayed.is_set()
    assert any(e["type"] == "assistant_message" and e["data"]["text"] == "你好！" for e in events)
