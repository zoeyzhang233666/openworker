from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from coworker.channels.questions import (
    format_channel_question,
    parse_channel_answer,
)
from coworker.channels.runtime import ChannelDeliveryCoordinator
from coworker.connectors.base import MessageEvent, SendResult, SessionSource
from coworker.connectors.config import ConnectorSettings, TeamAuth, is_authorized
from coworker.connectors.context import reset_current_channel_target, set_current_channel_target
from coworker.connectors.gateway import Gateway
from coworker.connectors.weixin_ilink import WeixinIlinkAdapter
from coworker.inbox import InboxStore
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient, StreamChunk
from coworker.server.manager import SessionManager


class _CaptureGateway:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    async def deliver(self, target: str, text: str):
        self.sent.append((target, text))
        return SendResult(True, message_id=f"m-{len(self.sent)}")


class _EnvelopeCaptureGateway(_CaptureGateway):
    def __init__(self):
        super().__init__()
        self.envelopes: list[tuple[str, object]] = []

    async def deliver_envelope(self, target: str, envelope):
        self.envelopes.append((target, envelope))
        return SendResult(True, message_id=f"e-{len(self.envelopes)}")


class _TextProvider(ProviderClient):
    def complete(self, *, model, messages, tools=None, **settings):
        return AssistantTurn(text="你好，这里是 ChemClaw。", finish_reason="stop")

    def capabilities(self, model):
        return ModelCapabilities()


class _LongStreamingProvider(ProviderClient):
    first = "第一段增量内容。" * 40
    second = "第二段收束内容。" * 24
    answer = first + second

    def complete(self, **kwargs):  # pragma: no cover - streamed instead
        raise NotImplementedError

    def capabilities(self, model):
        return ModelCapabilities()

    def stream(self, *, model, messages, tools=None, **settings):
        yield StreamChunk(text_delta=self.first)
        yield StreamChunk(text_delta=self.second)
        yield StreamChunk(
            turn=AssistantTurn(text=self.answer, finish_reason="stop")
        )


def _event(
    text: str,
    *,
    platform: str = "wecom",
    account: str = "default",
    chat: str = "alice",
    user: str = "alice",
    chat_type: str = "dm",
    mentions: bool | None = None,
) -> MessageEvent:
    return MessageEvent(
        text=text,
        source=SessionSource(
            platform=platform,
            account_id=account,
            chat_id=chat,
            user_id=user,
            user_name=user,
            chat_name=chat,
            chat_type=chat_type,
        ),
        message_id=f"{platform}-{chat}-{text}",
        mentions_me=(chat_type == "dm" if mentions is None else mentions),
    )


def test_question_text_renders_rich_options_and_parses_number_text_and_multi(tmp_path):
    store = InboxStore(tmp_path / "inbox.json")
    item = store.add_question(
        "s1",
        "选择市场",
        options=[
            {"label": "化工现货", "description": "区域现货价", "recommended": True},
            {"label": "国内期货", "description": "交易所合约价"},
        ],
        allow_text=False,
        data={"channel_target": "wecom:alice"},
    )
    rendered = format_channel_question(item)
    assert "1. 化工现货（推荐）" in rendered
    assert "区域现货价" in rendered and "/answer 1" in rendered
    assert parse_channel_answer(item, "1").answer == "化工现货"
    assert parse_channel_answer(item, "/answer 国内期货").answer == "国内期货"
    assert not parse_channel_answer(item, "9").valid

    multi = store.add_question(
        "s2", "多选", options=["A", "B", "C"], allow_text=False, multi=True
    )
    assert parse_channel_answer(multi, "/answer 1，B、3").answer == "A、B、C"


@pytest.mark.asyncio
async def test_bound_question_mirrors_and_natural_reply_resolves_same_conversation(tmp_path):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    gateway = _CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    item = manager.inbox.add_question(
        "s1",
        "选择口径",
        options=["现货", "期货"],
        allow_text=False,
        data={"channel_target": "wecom:corp-a/alice"},
    )
    await manager.mirror_inbox_item(item)
    assert gateway.sent[-1][0] == "wecom:corp-a/alice"
    assert "1. 现货" in gateway.sent[-1][1]

    assert manager._resolve_inbox_reply(
        _event("1", account="corp-a", chat="alice")
    )
    assert manager.inbox.get(item.id).resolution == "现货"


@pytest.mark.asyncio
async def test_real_question_asker_binds_active_channel_and_resumes_with_answer(tmp_path):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    gateway = _CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    token = set_current_channel_target("wecom:corp-a/alice")
    try:
        ask = manager.inbox_question_asker("s1", manager.personas.default_id())
        task = asyncio.create_task(
            ask(
                {
                    "question": "选择口径",
                    "options": ["现货", "期货"],
                    "allow_text": False,
                },
                "call-1",
            )
        )
        for _ in range(20):
            if manager.inbox.pending("s1"):
                break
            await asyncio.sleep(0)
        item = manager.inbox.pending("s1")[0]
        assert item.data["channel_target"] == "wecom:corp-a/alice"
        assert gateway.sent[-1][0] == "wecom:corp-a/alice"
        assert manager._resolve_inbox_reply(
            _event("1", account="corp-a", chat="alice")
        )
        assert await asyncio.wait_for(task, timeout=0.3) == {"answer": "现货"}
    finally:
        reset_current_channel_target(token)


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["wecom", "weixin"])
async def test_attended_desktop_question_asker_also_mirrors_active_channel(
    tmp_path, platform
):
    """Regression for the real screenshot: an open desktop socket must not swallow options."""
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    gateway = _CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    inline = []

    async def notify(item):
        inline.append(item)

    target = f"{platform}:alice"
    token = set_current_channel_target(target)
    try:
        ask = manager.inbox_question_asker(
            "s1",
            manager.personas.default_id(),
            visibility=lambda: "inline",
            inline_notifier=notify,
        )
        task = asyncio.create_task(
            ask(
                {
                    "question": "甲醇同时有现货和期货两种价格，请选择：",
                    "options": ["现货价格", "期货行情"],
                    "allow_text": False,
                },
                "call-attended",
            )
        )
        for _ in range(20):
            if manager.inbox.pending("s1"):
                break
            await asyncio.sleep(0)
        item = manager.inbox.pending("s1")[0]
        assert item.visibility == "inline"
        assert item.data["channel_target"] == target
        assert inline == [item]
        assert gateway.sent[-1][0] == target
        assert "1. 现货价格" in gateway.sent[-1][1]
        assert manager._resolve_inbox_reply(_event("1", platform=platform))
        assert await asyncio.wait_for(task, timeout=0.3) == {"answer": "现货价格"}
    finally:
        reset_current_channel_target(token)


@pytest.mark.asyncio
async def test_channel_question_delivery_retries_until_send_result_is_ok(tmp_path):
    class FlakyGateway(_CaptureGateway):
        def __init__(self):
            super().__init__()
            self.attempts = 0

        async def deliver(self, target: str, text: str):
            self.attempts += 1
            self.sent.append((target, text))
            return SendResult(self.attempts >= 2, error="transient")

    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    gateway = FlakyGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    item = manager.inbox.add_question(
        "s1",
        "选择口径",
        options=["现货", "期货"],
        data={"channel_target": "wecom:alice"},
    )
    await manager.mirror_inbox_item(item)
    assert gateway.attempts == 2
    assert item.state == "pending"


@pytest.mark.asyncio
async def test_invalid_and_cross_conversation_answers_are_consumed_without_new_turn(tmp_path):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    gateway = _CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    item = manager.inbox.add_question(
        "s1",
        "选择口径",
        options=["现货", "期货"],
        allow_text=False,
        data={"channel_target": "wecom:alice"},
    )

    assert manager._resolve_inbox_reply(_event("9"))
    await asyncio.sleep(0)
    assert manager.inbox.get(item.id).state == "pending"
    assert "不在可选范围" in gateway.sent[-1][1]

    assert manager._resolve_inbox_reply(_event("/answer 1", chat="bob", user="bob"))
    await asyncio.sleep(0)
    assert manager.inbox.get(item.id).state == "pending"
    assert gateway.sent[-1][0] == "wecom:bob"
    assert "没有等待回答的问题" in gateway.sent[-1][1]


@pytest.mark.asyncio
async def test_grouped_questions_advance_one_by_one_and_resolve_answers_json(tmp_path):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    gateway = _CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    item = manager.inbox.add_question(
        "s1",
        "图表？",
        questions=[
            {"question": "图表？", "header": "图表", "options": ["柱状", "折线"], "allow_text": False},
            {"question": "地区？", "header": "地区", "options": [], "allow_text": True},
        ],
        data={"channel_target": "feishu:tenant-a/group-1", "channel_step": 0},
    )
    first = _event("2", platform="feishu", account="tenant-a", chat="group-1", chat_type="group", user="u1", mentions=False)
    assert manager._resolve_inbox_reply(first)
    await asyncio.sleep(0)
    assert manager.inbox.get(item.id).state == "pending"
    assert "第 2/2 题" in gateway.sent[-1][1]

    second = _event("华东", platform="feishu", account="tenant-a", chat="group-1", chat_type="group", user="u2", mentions=False)
    assert manager._resolve_inbox_reply(second)
    resolved = manager.inbox.get(item.id)
    assert json.loads(resolved.resolution) == {"图表": "折线", "地区": "华东"}


@pytest.mark.asyncio
async def test_security_prompt_requires_desktop_instead_of_channel_approval(tmp_path):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    gateway = _CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    item = manager.inbox.add_approval(
        "s1", "写入文件？", data={"channel_target": "wecom:alice"}
    )
    await manager.mirror_inbox_item(item)
    assert "电脑桌面端" in gateway.sent[-1][1]
    assert manager.inbox.get(item.id).state == "pending"

    assert manager._resolve_inbox_reply(_event(f"approve [ow:{item.id}]"))
    await asyncio.sleep(0)
    assert manager.inbox.get(item.id).state == "pending"
    assert "必须在 ChemClaw 电脑桌面端审批" in gateway.sent[-1][1]


@pytest.mark.asyncio
async def test_legacy_answer_token_cannot_cross_bound_conversation(tmp_path):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    gateway = _CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    item = manager.inbox.add_question(
        "s1", "选择口径", data={"channel_target": "wecom:alice"}
    )
    assert manager._resolve_inbox_reply(
        _event(f"期货 [ow:{item.id}]", chat="bob", user="bob")
    )
    await asyncio.sleep(0)
    assert manager.inbox.get(item.id).state == "pending"
    assert "属于另一个账号或会话" in gateway.sent[-1][1]


@pytest.mark.asyncio
async def test_stop_is_not_consumed_as_answer_and_releases_pending_question(tmp_path):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    event = _event("/stop")
    item = manager.inbox.add_question(
        "s1", "选择口径", options=["现货", "期货"], data={"channel_target": event.source.target}
    )

    assert not manager._resolve_inbox_reply(event)
    await manager.deliver_channel_to_session("s1", event.text, event=event)
    assert manager.inbox.get(item.id).state == "resolved"
    assert manager.inbox.get(item.id).resolution == "channel stop"


def test_group_reset_command_accepts_transport_mention_but_remains_exact():
    normalize = SessionManager._normalized_channel_command
    assert normalize('<at user_id="bot">ChemClaw</at> /new') == "/new"
    assert normalize("<@bot-id> /reset") == "/reset"
    assert normalize("@_user_1 /new") == "/new"
    assert normalize("@ChemClaw /reset") == "/reset"
    assert normalize("@ChemClaw /reset 然后帮我查价") != "/reset"


@pytest.mark.parametrize(
    "text",
    [
        "新的对话",
        "开新的对话",
        "开始新对话。",
        "新建对话！",
        "/新的对话",
        "@ChemClaw 重新开一个对话",
    ],
)
def test_natural_language_reset_commands_are_exact_whole_messages(text):
    assert SessionManager._is_channel_reset_command(text)


def test_natural_language_reset_does_not_match_a_longer_request():
    assert not SessionManager._is_channel_reset_command("开新的对话然后帮我查甲醇")
    assert not SessionManager._is_channel_reset_command("新的对话应该怎么用")


def test_natural_language_reset_is_not_consumed_as_pending_question_answer(tmp_path):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    item = manager.inbox.add_question(
        "s1",
        "选择口径",
        options=["现货", "期货"],
        data={"channel_target": "wecom:alice"},
    )
    assert not manager._resolve_inbox_reply(_event("新的对话"))
    assert manager.inbox.get(item.id).state == "pending"


@pytest.mark.asyncio
async def test_coordinator_fast_enqueue_fifo_and_human_wait_exempts_timeout():
    gate = asyncio.Event()
    waiting = {"s1": True}
    order: list[str] = []

    async def runner(session_id, payload):
        order.append(payload)
        if payload == "first":
            await gate.wait()

    coordinator = ChannelDeliveryCoordinator(
        runner,
        turn_timeout=0.03,
        is_waiting_for_human=lambda sid: waiting.get(sid, False),
    )
    first = await coordinator.submit("s1", ("wecom", "default", "a"), "first", wait=False)
    second = await coordinator.submit("s1", ("wecom", "default", "a"), "second", wait=False)
    await asyncio.sleep(0.09)
    assert not first.done() and not second.done()
    assert order == ["first"]
    gate.set()
    await asyncio.wait_for(first, timeout=0.3)
    waiting["s1"] = False
    await asyncio.wait_for(second, timeout=0.3)
    assert order == ["first", "second"]
    await coordinator.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["wecom", "weixin", "feishu", "dingtalk"])
async def test_reset_creates_fresh_session_preserves_old_and_suppresses_old_delivery(tmp_path, platform):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / f"data-{platform}")
    gateway = _CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    event = _event("/reset", platform=platform, chat="chat-1")
    target = event.source.target
    old_sid = f"old-{platform}"
    old_engine = manager.get_engine(old_sid, agent=manager.personas.default_id())
    assert old_engine is not None
    old_engine.messages.append({"role": "user", "content": "旧上下文"})
    old_engine.permissions.task_rules.setdefault("send_message", set()).add(target)
    manager.save(old_sid, old_engine)
    manager.mention_sessions.set(target, old_sid, channel=f"{platform}:chat-1")
    pending = manager.inbox.add_question(
        old_sid, "旧问题", data={"channel_target": target}
    )

    new_sid = await manager._reset_managed_channel_session(event, target=target)
    assert new_sid and new_sid != old_sid
    assert manager.mention_sessions.get(target) == new_sid
    assert manager.session_store.load(old_sid) is not None
    fresh_messages = manager.session_store.load(new_sid).messages
    assert not [message for message in fresh_messages if message.get("role") != "system"]
    assert manager.inbox.get(pending.id).state == "resolved"
    assert not manager._channel_mapping_allows_delivery(old_sid, target)
    assert manager._channel_mapping_allows_delivery(new_sid, target)
    assert "已开始新对话" in gateway.sent[-1][1]


@pytest.mark.asyncio
async def test_subscribed_group_reset_is_protected(tmp_path):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    gateway = _CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    event = _event("/new", platform="wecom", chat="room-1", chat_type="group", mentions=True)
    ms = SimpleNamespace()
    await manager._route_mention(event, ms, [SimpleNamespace(session_id="desktop-s1")])
    assert manager.mention_sessions.get("wecom:room-1") is None
    assert "不能重置桌面对话" in gateway.sent[-1][1]


def test_weixin_default_account_uses_account_allowlist():
    settings = ConnectorSettings(
        platform="weixin",
        accounts={"default": TeamAuth(allowed_users={"owner"})},
    )
    source = SessionSource(platform="weixin", account_id="default", chat_id="owner", user_id="owner")
    assert is_authorized(settings, source)


@pytest.mark.asyncio
async def test_weixin_first_inbound_refreshes_stale_gateway_auth_and_keeps_context(tmp_path):
    class MemorySecrets:
        def __init__(self):
            self.rows = {
                "weixin:default": {
                    "type": "token",
                    "enabled": True,
                    "default_account": "default",
                },
                "weixin:account:default": {
                    "type": "token",
                    "enabled": True,
                    "token": "t",
                    "allowed_users": ["owner"],
                },
            }

        def get(self, key):
            value = self.rows.get(key)
            return dict(value) if value else None

        def put(self, key, value):
            self.rows[key] = dict(value)

        def delete(self, key):
            return self.rows.pop(key, None) is not None

        def status(self):
            return [
                {"profile": key, "type": value.get("type")}
                for key, value in self.rows.items()
            ]

    secrets = MemorySecrets()
    received: list[MessageEvent] = []

    async def handler(event):
        received.append(event)

    stale = ConnectorSettings(
        platform="weixin",
        enabled=True,
        accounts={"default": TeamAuth()},
    )
    gateway = Gateway(secrets=secrets, settings={"weixin": stale}, handler=handler)
    event = _event("你好", platform="weixin", chat="owner", user="owner")
    event.context_token = "ctx-owner"
    await gateway._on_inbound(event)
    assert received == [event]
    assert gateway.settings["weixin"].accounts["default"].allowed_users == {"owner"}


def test_weixin_status_has_content_free_poll_diagnostics():
    adapter = WeixinIlinkAdapter("token")
    adapter._last_poll_at = 123.0
    adapter._last_poll_message_count = 2
    adapter._last_inbound_at = 124.0
    details = adapter.channel_status().details
    assert details["last_poll_at"] == 123.0
    assert details["last_poll_message_count"] == 2
    assert details["last_inbound_at"] == 124.0
    assert details["streaming_mode"] == "incremental_messages"
    assert adapter.capabilities.streaming is True
    assert "text" not in details and "token" not in details


@pytest.mark.asyncio
async def test_weixin_long_answer_streams_ordered_chunks_without_repeating_final(tmp_path):
    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "data",
        provider=_LongStreamingProvider(),
    )
    gateway = _EnvelopeCaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    event = _event("请给我长回答", platform="weixin", chat="owner", user="owner")
    target = event.source.target
    session_id = "weixin-stream-session"
    engine = manager.get_engine(session_id, agent=manager.personas.default_id())
    assert engine is not None
    manager.save(session_id, engine)
    manager.mention_sessions.set(target, session_id, channel="weixin:owner")

    await manager.deliver_to_session(
        session_id,
        event.tagged_text(),
        source={
            "connector": "weixin",
            "kind": "dm",
            "channel_id": "owner",
            "channel_name": "owner",
            "sender_id": "owner",
            "sender_name": "owner",
            "ts": 1.0,
            "text": event.text,
            "target": target,
            "message_id": "wx-in-1",
        },
    )

    kinds = [envelope.kind for _target, envelope in gateway.envelopes]
    assert kinds[0] == "progress"
    assert "stream_chunk" in kinds
    assert kinds[-1] == "final"
    delivered = "".join(
        envelope.text
        for _target, envelope in gateway.envelopes
        if envelope.kind in {"stream_chunk", "final"}
    )
    assert delivered == _LongStreamingProvider.answer


@pytest.mark.asyncio
async def test_weixin_inbound_creates_session_and_replies_with_same_context_token(tmp_path):
    calls: list[tuple[str, str, list[dict]]] = []

    class FakeApi:
        token = "token"

        async def send_items(self, to, context_token, items):
            calls.append((to, context_token, items))
            return {"ret": 0, "message_id": "out-1"}

    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "data",
        provider=_TextProvider(),
    )
    adapter = WeixinIlinkAdapter("token", account_id="default")
    adapter.api = FakeApi()  # type: ignore[assignment]
    settings = ConnectorSettings(
        platform="weixin",
        enabled=True,
        accounts={"default": TeamAuth(allowed_users={"owner"})},
    )
    gateway = Gateway(
        settings={"weixin": settings}, handler=manager._dispatch_inbound
    )
    gateway.register(adapter)
    manager.gateway = gateway

    await adapter._on_message(
        {
            "message_type": 1,
            "message_id": "in-1",
            "from_user_id": "owner",
            "context_token": "ctx-in-1",
            "item_list": [{"type": 1, "text_item": {"text": "你好"}}],
        }
    )
    await adapter.drain_inbound()
    for _ in range(200):
        if calls:
            break
        await asyncio.sleep(0.01)
    assert calls and calls[0][0:2] == ("owner", "ctx-in-1")
    sid = manager.mention_sessions.get("weixin:owner")
    assert sid and manager.session_store.load(sid) is not None
    assert adapter._context_tokens["owner"] == "ctx-in-1"
    await manager.channel_delivery.close()
