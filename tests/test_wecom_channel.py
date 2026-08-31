"""D-188 WeCom AI Bot channel: mappings, connector wiring, adapter mocks."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from coworker.channels.mappings import (
    frame_to_inbound,
    inbound_to_message_event,
    wecom_frame_to_message_event,
)
from coworker.channels.models import InboundMessage, OutboundMessage
from coworker.connectors import (
    Gateway,
    MessageEvent,
    SessionSource,
    format_target,
    make_send_message_tool,
)
from coworker.connectors.adapters import make_adapter
from coworker.connectors.base import SendResult
from coworker.connectors.config import ConnectorSettings, load_settings
from coworker.connectors.descriptors import get_descriptor
from coworker.connectors.setup import connect_connector, connector_list, disconnect_connector
from coworker.secrets import SecretStore


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


def _group_frame(
    text: str = "@ChemClaw 查甲醇",
    msgid: str = "g1",
    *,
    mentioned: bool | None = None,
) -> dict:
    body = {
        "msgtype": "text",
        "msgid": msgid,
        "chattype": "group",
        "chatid": "wr_room_1",
        "from": {"userid": "user_bob", "name": "Bob"},
        "text": {"content": text},
    }
    if mentioned is False:
        body["is_mentioned"] = False
    elif mentioned is True:
        body["is_mentioned"] = True
        body["mentioned_list"] = ["bot"]
    return {"cmd": "aibot_msg_callback", "req_id": "r2", "body": body}


# -- models / mappings ---------------------------------------------------------
def test_inbound_outbound_round_trip_dict():
    inbound = InboundMessage(
        channel="wecom",
        conversation_id="c1",
        user_id="u1",
        message_id="m1",
        text="hi",
    )
    assert inbound.to_dict()["channel"] == "wecom"
    out = OutboundMessage(
        channel="wecom", conversation_id="c1", kind="progress", text="…"
    )
    assert out.to_dict()["kind"] == "progress"


def test_frame_to_inbound_dm():
    inbound = frame_to_inbound(_dm_frame("甲醇价格"))
    assert inbound is not None
    assert inbound.channel == "wecom"
    assert inbound.conversation_id == "user_alice"
    assert inbound.user_id == "user_alice"
    assert inbound.chat_type == "dm"
    assert inbound.text == "甲醇价格"
    assert inbound.mentions_bot is True


def test_frame_to_inbound_group_default_mention():
    inbound = frame_to_inbound(_group_frame())
    assert inbound is not None
    assert inbound.chat_type == "group"
    assert inbound.conversation_id == "wr_room_1"
    assert inbound.mentions_bot is True


def test_frame_to_inbound_group_explicit_not_mentioned_dropped():
    assert frame_to_inbound(_group_frame(mentioned=False)) is None


def test_wecom_frame_to_message_event():
    ev = wecom_frame_to_message_event(_dm_frame())
    assert isinstance(ev, MessageEvent)
    assert ev.source.platform == "wecom"
    assert ev.source.target == "wecom:user_alice"
    assert "你好" in ev.text


def test_inbound_to_message_event_preserves_mentions():
    inbound = frame_to_inbound(_group_frame(mentioned=True))
    assert inbound is not None
    ev = inbound_to_message_event(inbound)
    assert ev.mentions_me is True
    assert ev.source.chat_type == "group"


# -- descriptor / connect ------------------------------------------------------
def test_wecom_descriptor_present():
    d = get_descriptor("wecom")
    assert d is not None
    assert d.two_way and d.channels and d.available
    keys = {f.key for f in d.fields}
    assert keys >= {"bot_id", "secret", "allowed_users"}


def test_validate_wecom_missing_creds():
    from coworker.connectors.descriptors import _validate_wecom

    r = _validate_wecom({})
    assert r.ok is False


def test_validate_wecom_with_stub_sdk():
    import sys
    import types

    from coworker.connectors.descriptors import _validate_wecom

    sys.modules["wecom_aibot_sdk"] = types.ModuleType("wecom_aibot_sdk")
    try:
        r = _validate_wecom({"bot_id": "bot-abcdef", "secret": "secret-value-long"})
        assert r.ok is True
        assert r.identity and "企业微信" in r.identity
    finally:
        sys.modules.pop("wecom_aibot_sdk", None)


def test_validate_wecom_without_sdk():
    import builtins
    import sys

    from coworker.connectors.descriptors import _validate_wecom

    sys.modules.pop("wecom_aibot_sdk", None)
    real_import = builtins.__import__

    def _imp(name, *a, **k):
        if name == "wecom_aibot_sdk" or (
            isinstance(name, str) and name.startswith("wecom_aibot_sdk.")
        ):
            raise ImportError("no sdk")
        return real_import(name, *a, **k)

    with patch("builtins.__import__", _imp):
        r = _validate_wecom({"bot_id": "bot-abcdef", "secret": "secret-value-long"})
    assert r.ok is False
    assert "SDK" in (r.error or "") or "sdk" in (r.error or "").lower()


def test_connect_wecom_without_sdk_fails_validate(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    import builtins
    import sys

    sys.modules.pop("wecom_aibot_sdk", None)
    real_import = builtins.__import__

    def _imp(name, *a, **k):
        if name == "wecom_aibot_sdk" or (
            isinstance(name, str) and name.startswith("wecom_aibot_sdk.")
        ):
            raise ImportError("no sdk")
        return real_import(name, *a, **k)

    with patch("builtins.__import__", _imp):
        out = connect_connector(
            secrets,
            "wecom",
            {"bot_id": "bot-abcdef", "secret": "secret-value-long"},
            validate=True,
        )
    assert out["ok"] is False
    assert out.get("error")

def test_connect_wecom_validate_false_stores_profile(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    out = connect_connector(
        secrets,
        "wecom",
        {
            "bot_id": "bot-abcdef",
            "secret": "secret-value-long",
            "allowed_users": "user_alice",
        },
        validate=False,
    )
    assert out["ok"] is True
    profile = secrets.get("wecom:default") or {}
    assert profile["bot_id"] == "bot-abcdef"
    assert profile["secret"] == "secret-value-long"
    assert "user_alice" in profile["allowed_users"]
    listed = {c["name"]: c for c in connector_list(secrets)}
    assert listed["wecom"]["connected"] is True
    assert listed["wecom"]["two_way"] is True


def test_load_settings_enables_wecom(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    secrets.put(
        "wecom:default",
        {
            "type": "token",
            "bot_id": "b1",
            "secret": "s1secret",
            "enabled": True,
            "allowed_users": ["u1"],
        },
    )
    settings = load_settings(secrets)
    assert "wecom" in settings
    assert settings["wecom"].enabled is True
    assert "u1" in settings["wecom"].allowed_users


def test_make_adapter_wecom():
    adapter = make_adapter(
        "wecom", {"bot_id": "b1", "secret": "secret-long-enough"}
    )
    assert adapter is not None
    assert adapter.platform == "wecom"


# -- send_message via live adapter ---------------------------------------------
def test_send_message_wecom_uses_live_adapter(tmp_path):
    from coworker.connectors import wecom_bot as wb

    secrets = SecretStore(tmp_path / "s.json")
    secrets.put(
        "wecom:default",
        {"type": "token", "bot_id": "bot1", "secret": "sec", "enabled": True},
    )

    class FakeAdapter:
        bot_id = "bot1"

        def send_sync(self, chat_id, text, *, thread_id=None):
            return SendResult(True, message_id="ok1")

    wb._LIVE["bot1"] = FakeAdapter()  # type: ignore[assignment]
    try:
        tool = make_send_message_tool(secrets)
        out = tool(target="wecom:user_alice", text="回复")
        assert out.get("ok") is True
        assert out.get("target") == "wecom:user_alice"
    finally:
        wb._LIVE.pop("bot1", None)


def test_send_message_wecom_not_connected(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    # No profile → clear error
    tool = make_send_message_tool(secrets)
    out = tool(target="wecom:x", text="hi")
    assert "error" in out


# -- adapter with mock SDK -----------------------------------------------------
@pytest.mark.asyncio
async def test_wecom_adapter_inbound_and_send():
    from coworker.connectors.wecom_bot import WecomBotAdapter, _LIVE

    received: list[MessageEvent] = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.handlers = {}
            self.sent = []

        def on(self, event, handler):
            self.handlers[event] = handler
            return self

        async def connect(self):
            return self

        async def disconnect(self):
            return None

        async def send_message(self, chatid, body):
            self.sent.append((chatid, body))
            return {}

    adapter = WecomBotAdapter("botZ", "secretZ")

    async def on_msg(ev: MessageEvent):
        received.append(ev)

    adapter.set_message_handler(on_msg)
    client = FakeClient()
    adapter._client = client
    adapter._loop = asyncio.get_running_loop()
    adapter._ack_enabled = False
    adapter._channel_authenticated = True
    _LIVE["botZ"] = adapter
    try:
        await adapter._on_frame(_dm_frame("ping", msgid="uniq-1"))
        await adapter.drain_inbound()
        assert len(received) == 1
        assert received[0].text == "ping"
        await adapter._on_frame(_dm_frame("ping", msgid="uniq-1"))
        await adapter.drain_inbound()
        assert len(received) == 1
        result = await adapter.send("user_alice", "pong")
        assert result.ok
        assert client.sent[-1][0] == "user_alice"
    finally:
        _LIVE.pop("botZ", None)
        await adapter.disconnect()


@pytest.mark.asyncio
async def test_wecom_adapter_progress_ack():
    from coworker.connectors.wecom_bot import WecomBotAdapter, _LIVE

    class FakeClient:
        def __init__(self):
            self.streamed = []

        async def reply_stream(self, frame, stream_id, text, finish=False):
            self.streamed.append((frame, stream_id, text, finish))
            return {}

        async def disconnect(self):
            return None

    adapter = WecomBotAdapter("botAck", "secretAck")
    adapter._client = FakeClient()
    adapter._loop = asyncio.get_running_loop()
    adapter._ack_enabled = True
    received: list = []

    async def on_msg(ev):
        received.append(ev)

    adapter.set_message_handler(on_msg)
    _LIVE["botAck"] = adapter
    try:
        await adapter._on_frame(_dm_frame("task", msgid="ack-1"))
        await adapter.drain_inbound()
        # Gateway calls this only after authorization; the transport callback itself
        # must not leak bot activity to an unapproved sender.
        assert adapter._client.streamed == []
        await adapter.acknowledge(received[0])
        assert any("ChemClaw" in item[2] for item in adapter._client.streamed)
        assert len(received) == 1
    finally:
        _LIVE.pop("botAck", None)
        await adapter.disconnect()


@pytest.mark.asyncio
async def test_wecom_start_waits_for_authenticated_event(monkeypatch):
    import sys
    import types

    from coworker.connectors.wecom_bot import WecomBotAdapter

    clients = []

    class FakeWSClient:
        def __init__(self, **_kwargs):
            self.handlers = {}
            clients.append(self)

        def on(self, event, handler):
            self.handlers[event] = handler
            return self

        async def connect(self):
            return self

        async def disconnect(self):
            return None

    module = types.ModuleType("wecom_aibot_sdk")
    module.WSClient = FakeWSClient
    monkeypatch.setitem(sys.modules, "wecom_aibot_sdk", module)
    adapter = WecomBotAdapter("bot-life", "secret-life")
    try:
        assert await adapter.start()
        assert adapter.channel_status().state == "connecting"
        assert not adapter.channel_status().authenticated
        clients[0].handlers["authenticated"]()
        assert adapter.channel_status().state == "connected"
        assert adapter.channel_status().authenticated
    finally:
        await adapter.stop()


@pytest.mark.asyncio
async def test_gateway_never_acknowledges_unauthorized_wecom():
    from coworker.connectors.wecom_bot import WecomBotAdapter

    class FakeClient:
        def __init__(self):
            self.streamed = []

        async def reply_stream(self, *args, **kwargs):
            self.streamed.append((args, kwargs))

        async def disconnect(self):
            return None

    adapter = WecomBotAdapter("bot-deny", "secret-deny")
    adapter._client = FakeClient()
    adapter._loop = asyncio.get_running_loop()
    gateway = Gateway(
        settings={"wecom": ConnectorSettings("wecom", enabled=True)},
        handler=AsyncMock(),
    )
    gateway.register(adapter)
    try:
        await adapter._on_frame(_dm_frame("private", msgid="deny-1"))
        await adapter.drain_inbound()
        assert adapter._client.streamed == []
    finally:
        await adapter.disconnect()


@pytest.mark.asyncio
async def test_wecom_final_prefers_original_reply_frame():
    from coworker.connectors.wecom_bot import WecomBotAdapter

    class FakeClient:
        def __init__(self):
            self.replies = []
            self.proactive = []

        async def reply(self, frame, body):
            self.replies.append((frame, body))

        async def send_message(self, chat_id, body):
            self.proactive.append((chat_id, body))

        async def disconnect(self):
            return None

    adapter = WecomBotAdapter("bot-reply", "secret-reply")
    adapter._client = FakeClient()
    adapter._loop = asyncio.get_running_loop()
    adapter._ack_enabled = False
    adapter._channel_authenticated = True
    event = wecom_frame_to_message_event(_dm_frame("hello", msgid="reply-1"))
    assert event is not None
    await adapter.acknowledge(event)
    try:
        result = await adapter.send("user_alice", "world")
        assert result.ok
        assert len(adapter._client.replies) == 1
        assert adapter._client.proactive == []
    finally:
        await adapter.disconnect()


@pytest.mark.asyncio
async def test_gateway_routes_wecom_when_authorized(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    secrets.put(
        "wecom:default",
        {
            "type": "token",
            "bot_id": "b",
            "secret": "s" * 10,
            "enabled": True,
            "allowed_users": ["user_alice"],
            "allow_all": False,
        },
    )
    got: list[MessageEvent] = []

    async def handler(ev: MessageEvent):
        got.append(ev)

    gw = Gateway(secrets=secrets, handler=handler)
    # Don't start real adapter — inject Fake-like by registering nothing and
    # calling _on_inbound directly after settings load.
    settings = load_settings(secrets)
    gw.settings = settings
    ev = wecom_frame_to_message_event(_dm_frame())
    assert ev is not None
    await gw._on_inbound(ev)
    assert len(got) == 1


@pytest.mark.asyncio
async def test_gateway_parks_unauthorized_wecom(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    secrets.put(
        "wecom:default",
        {
            "type": "token",
            "bot_id": "b",
            "secret": "s" * 10,
            "enabled": True,
            "allowed_users": [],
            "allow_all": False,
        },
    )
    parked: list = []

    async def on_unauth(ev):
        parked.append(ev)

    gw = Gateway(secrets=secrets, handler=AsyncMock(), on_unauthorized=on_unauth)
    gw.settings = load_settings(secrets)
    ev = wecom_frame_to_message_event(_dm_frame())
    assert ev is not None
    await gw._on_inbound(ev)
    assert len(parked) == 1


def test_disconnect_wecom(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    connect_connector(
        secrets,
        "wecom",
        {"bot_id": "bot-abcdef", "secret": "secret-value-long"},
        validate=False,
    )
    assert disconnect_connector(secrets, "wecom")["ok"] is True
    assert (secrets.get("wecom:default") or {}) == {} or not (
        secrets.get("wecom:default") or {}
    ).get("bot_id")


def test_format_target_wecom():
    assert format_target("wecom", "wr_1") == "wecom:wr_1"
    s = SessionSource(platform="wecom", chat_id="wr_1", chat_type="group")
    assert s.target == "wecom:wr_1"
