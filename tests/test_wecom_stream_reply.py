"""D-195 WeCom stream update + finish behaviour."""

from __future__ import annotations

import asyncio

import pytest

from coworker.channels.mappings import wecom_frame_to_message_event
from coworker.connectors.base import SendResult


def _dm_frame(text: str = "你好", msgid: str = "m1") -> dict:
    return {
        "cmd": "aibot_msg_callback",
        "req_id": "r1",
        "body": {
            "msgtype": "text",
            "msgid": msgid,
            "chattype": "single",
            "chatid": "user_alice",
            "from": {"userid": "user_alice", "name": "Alice"},
            "text": {"content": text},
        },
    }


@pytest.mark.asyncio
async def test_update_stream_does_not_finish_or_pop():
    from coworker.connectors.wecom_bot import WecomBotAdapter

    class FakeClient:
        def __init__(self):
            self.streamed = []

        async def reply_stream(self, frame, stream_id, text, finish=False):
            self.streamed.append(
                {"stream_id": stream_id, "text": text, "finish": finish}
            )

        async def disconnect(self):
            return None

    adapter = WecomBotAdapter("bot-stream", "secret-stream")
    adapter._client = FakeClient()
    adapter._loop = asyncio.get_running_loop()
    adapter._channel_authenticated = True
    event = wecom_frame_to_message_event(_dm_frame("查甲醇", msgid="s1"))
    await adapter.acknowledge(event)
    assert "user_alice" in adapter._reply_streams

    r1 = await adapter.update_stream("user_alice", "正在分析…")
    assert r1.ok
    r2 = await adapter.update_stream("user_alice", "草稿：甲醇…")
    assert r2.ok
    assert "user_alice" in adapter._reply_streams
    assert all(item["finish"] is False for item in adapter._client.streamed)
    assert len(adapter._client.streamed) == 3  # ack + 2 updates

    final = await adapter.send("user_alice", "总结 + [查看完整版](https://x)")
    assert final.ok
    assert "user_alice" not in adapter._reply_streams
    assert adapter._client.streamed[-1]["finish"] is True
    assert "查看完整版" in adapter._client.streamed[-1]["text"]
    await adapter.disconnect()


@pytest.mark.asyncio
async def test_update_stream_without_open_stream():
    from coworker.connectors.wecom_bot import WecomBotAdapter

    adapter = WecomBotAdapter("bot-x", "secret-x")
    adapter._client = object()
    adapter._channel_authenticated = True
    result = await adapter.update_stream("nobody", "hi")
    assert isinstance(result, SendResult)
    assert result.ok is False


@pytest.mark.asyncio
async def test_gateway_update_stream_routes_to_adapter():
    from coworker.connectors.gateway import Gateway
    from coworker.connectors.config import ConnectorSettings
    from coworker.connectors.wecom_bot import WecomBotAdapter

    class FakeClient:
        def __init__(self):
            self.streamed = []

        async def reply_stream(self, frame, stream_id, text, finish=False):
            self.streamed.append((text, finish))

        async def disconnect(self):
            return None

    adapter = WecomBotAdapter("bot-gw", "secret-gw")
    adapter._client = FakeClient()
    adapter._loop = asyncio.get_running_loop()
    adapter._channel_authenticated = True
    event = wecom_frame_to_message_event(_dm_frame("hi", msgid="g1"))
    await adapter.acknowledge(event)

    gateway = Gateway(
        settings={"wecom": ConnectorSettings("wecom", enabled=True)},
        handler=None,
    )
    gateway.register(adapter)
    try:
        result = await gateway.update_stream("wecom:user_alice", "过程草稿")
        assert result.ok
        assert any(t == "过程草稿" and not f for t, f in adapter._client.streamed)
    finally:
        await adapter.disconnect()
