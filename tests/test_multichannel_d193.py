"""D-193 multi-platform Channel contracts, media safety and fake transports."""

from __future__ import annotations

import asyncio
import sys
import threading
import tomllib
import types
from pathlib import Path

import pytest

from coworker.channels import (
    ChannelAttachment,
    ChannelDeliveryCoordinator,
    ChannelMediaError,
    ChannelMediaManager,
    InboundEnvelope,
    MessageDeduplicator,
)
from coworker.channels.platform_mappings import (
    dingtalk_callback_to_inbound,
    feishu_event_to_inbound,
    weixin_update_to_inbound,
)
from coworker.connectors.base import MessageEvent, SendResult, SessionSource
from coworker.connectors.config import ConnectorSettings, load_settings
from coworker.connectors.context import (
    reset_current_channel_target,
    set_current_channel_target,
)
from coworker.connectors.dingtalk_bot import DingTalkAdapter
from coworker.connectors.feishu_bot import FeishuAdapter
from coworker.connectors.gateway import Gateway
from coworker.connectors.fake import FakeAdapter
from coworker.connectors.setup import connect_connector
from coworker.connectors.tools import make_send_file_tool
from coworker.connectors.weixin_ilink import WeixinIlinkAdapter, _aes_decrypt, _aes_encrypt
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient
from coworker.secrets import SecretStore
from coworker.server.manager import SessionManager


class _TextProvider(ProviderClient):
    def complete(self, *, model, messages, tools=None, **settings):
        return AssistantTurn(text="这是可靠的通道回复", finish_reason="stop")

    def capabilities(self, model):
        return ModelCapabilities()


def _feishu_payload(*, chat_type="p2p", mentioned=True, message_type="text"):
    mentions = [{"id": {"open_id": "bot-open"}}] if mentioned else []
    content = (
        '{"text":"@_user_1 查甲醇"}'
        if message_type == "text"
        else '{"file_key":"file-k","file_name":"询价单.xlsx"}'
    )
    return {
        "event": {
            "sender": {
                "sender_id": {"open_id": "ou-alice"},
                "sender_name": "Alice",
            },
            "message": {
                "message_id": "om-1",
                "chat_id": "oc-group" if chat_type == "group" else "oc-dm",
                "chat_type": chat_type,
                "message_type": message_type,
                "content": content,
                "mentions": mentions,
            },
        }
    }


def test_public_envelope_route_key_is_platform_account_conversation():
    inbound = InboundEnvelope(
        platform="feishu",
        account_id="sales",
        conversation_id="oc-1",
        chat_type="dm",
        user_id="ou-1",
        message_id="om-1",
    )
    assert inbound.route_key == ("feishu", "sales", "oc-1")
    source = SessionSource(platform="feishu", account_id="sales", chat_id="oc-1")
    assert source.target == "feishu:sales/oc-1"


def test_feishu_private_group_mention_file_and_untagged():
    dm = feishu_event_to_inbound(_feishu_payload())
    assert dm and dm.chat_type == "dm" and dm.mentions_bot
    group = feishu_event_to_inbound(
        _feishu_payload(chat_type="group"), bot_open_id="bot-open"
    )
    assert group and group.chat_type == "group" and group.mentions_bot
    untagged = feishu_event_to_inbound(
        _feishu_payload(chat_type="group", mentioned=False),
        bot_open_id="bot-open",
    )
    assert untagged is not None and untagged.mentions_bot is False
    file_message = feishu_event_to_inbound(
        _feishu_payload(message_type="file")
    )
    assert file_message and file_message.attachments[0].name == "询价单.xlsx"
    assert file_message.attachments[0].remote_ref == "file-k"


def test_dingtalk_private_group_mention_file_and_untagged():
    dm = dingtalk_callback_to_inbound(
        {
            "msgId": "d1",
            "senderStaffId": "staff-1",
            "conversationType": "1",
            "text": {"content": "你好"},
            "msgtype": "text",
        }
    )
    assert dm and dm.chat_type == "dm" and dm.conversation_id == "staff-1"
    group = {
        "msgId": "d2",
        "senderStaffId": "staff-1",
        "conversationId": "cid-group",
        "conversationType": "2",
        "isInAtList": True,
        "msgtype": "file",
        "content": {"downloadCode": "down-1", "fileName": "合同.pdf"},
    }
    mapped = dingtalk_callback_to_inbound(group)
    assert mapped and mapped.chat_type == "group"
    assert mapped.attachments[0].name == "合同.pdf"
    group["isInAtList"] = False
    untagged = dingtalk_callback_to_inbound(group)
    assert untagged is not None and untagged.mentions_bot is False

    rich = dingtalk_callback_to_inbound(
        {
            "msgId": "d3",
            "senderStaffId": "staff-1",
            "conversationId": "cid-group",
            "conversationType": "2",
            "isInAtList": True,
            "msgtype": "richText",
            "content": {
                "richText": [
                    {"text": "请看图片"},
                    {"downloadCode": "rich-image"},
                ]
            },
        }
    )
    assert rich and rich.text == "请看图片"
    assert rich.attachments[0].remote_ref == "rich-image"


def test_weixin_is_dm_only_and_preserves_context_and_crypto_metadata():
    mapped = weixin_update_to_inbound(
        {
            "from_user_id": "wx-user",
            "message_id": "wx-1",
            "context_token": "ctx-1",
            "item_list": [
                {"type": 1, "text_item": {"text": "请看附件"}},
                {
                    "type": 4,
                    "file_item": {
                        "file_name": "样品表.csv",
                        "aeskey": "00112233445566778899aabbccddeeff",
                        "media": {"encrypt_query_param": "enc-param"},
                    },
                },
            ],
        }
    )
    assert mapped and mapped.chat_type == "dm" and mapped.context_token == "ctx-1"
    assert mapped.attachments[0].remote_ref == "enc-param"
    assert mapped.attachments[0].encryption["aes_key"].startswith("0011")
    key = bytes.fromhex("00112233445566778899aabbccddeeff")
    assert _aes_decrypt(_aes_encrypt(b"chemical-data", key), key) == b"chemical-data"


def _inbound(attachment: ChannelAttachment) -> InboundEnvelope:
    return InboundEnvelope(
        platform="wecom",
        account_id="default",
        conversation_id="room-1",
        chat_type="dm",
        user_id="u1",
        message_id="m1",
        attachments=[attachment],
    )


@pytest.mark.asyncio
async def test_media_manager_chinese_filename_workspace_import_and_ttl(tmp_path):
    manager = ChannelMediaManager(tmp_path / "spool", ttl_seconds=1)
    attachment = ChannelAttachment(kind="file", name="报价单.pdf")
    envelope = _inbound(attachment)

    async def download(_attachment):
        return "报价单.pdf", b"%PDF-1.7\nchemical", "application/pdf"

    assert await manager.materialize(envelope, download) == []
    assert Path(attachment.local_path).name == "报价单.pdf"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    text, prompt = manager.prompt_parts("总结", [attachment], workspace)
    assert "._chemclaw" in text and prompt[0]["kind"] == "pdf"
    Path(attachment.local_path).touch()
    assert manager.cleanup_expired(now=Path(attachment.local_path).stat().st_mtime + 2) >= 1


def test_media_manager_rejects_traversal_fake_pdf_and_outside_file(tmp_path):
    manager = ChannelMediaManager(tmp_path / "spool")
    attachment = ChannelAttachment(kind="file", name="../../机密.pdf")
    with pytest.raises(ChannelMediaError, match="内容不是 PDF"):
        manager.store_bytes(_inbound(attachment), attachment, b"not-a-pdf")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    root = tmp_path / "workspace"
    root.mkdir()
    with pytest.raises(ChannelMediaError, match="不在当前工作区"):
        manager.resolve_outbound(str(outside), [root])


def test_media_manager_rejects_symlink_when_supported(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    target = root / "real.txt"
    target.write_text("ok", encoding="utf-8")
    link = root / "alias.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("当前 Windows 测试账户不能创建符号链接")
    manager = ChannelMediaManager(tmp_path / "spool")
    with pytest.raises(ChannelMediaError):
        manager.resolve_outbound(str(link), [root])


@pytest.mark.asyncio
async def test_fifo_serializes_five_messages_and_parallelizes_ten_sessions():
    order: list[int] = []
    running = 0
    max_running = 0

    async def runner(session_id, payload):
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        await asyncio.sleep(0.01)
        if session_id == "same":
            order.append(payload)
        running -= 1

    coordinator = ChannelDeliveryCoordinator(runner, max_concurrency=10, turn_timeout=2)
    await asyncio.gather(
        *(
            coordinator.submit("same", ("wecom", "default", "room"), i)
            for i in range(5)
        )
    )
    assert order == list(range(5))
    await asyncio.gather(
        *(
            coordinator.submit(
                f"session-{i}", ("feishu", "default", f"chat-{i}"), i
            )
            for i in range(10)
        )
    )
    assert max_running >= 2
    assert coordinator.queue_length() == 0
    await coordinator.close()


@pytest.mark.asyncio
async def test_adapter_ingress_is_fifo_per_chat_but_parallel_across_chats():
    adapter = FakeAdapter()
    adapter.platform = "wecom"
    running = 0
    max_running = 0
    same_order: list[str] = []

    async def handler(event):
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        await asyncio.sleep(0.02)
        if event.source.chat_id == "same":
            same_order.append(event.text)
        running -= 1

    adapter.set_message_handler(handler)
    events = [
        MessageEvent(
            text=str(index),
            source=SessionSource(platform="wecom", chat_id="same", user_id="u"),
        )
        for index in range(3)
    ] + [
        MessageEvent(
            text="other",
            source=SessionSource(platform="wecom", chat_id="other", user_id="v"),
        )
    ]
    await asyncio.gather(*(adapter.enqueue_message(event) for event in events))
    await adapter.drain_inbound()
    assert same_order == ["0", "1", "2"]
    assert max_running >= 2


def test_message_deduplication_is_platform_and_account_scoped():
    dedup = MessageDeduplicator()
    assert dedup.accept(("wecom", "default", "m1"))
    assert not dedup.accept(("wecom", "default", "m1"))
    assert dedup.accept(("wecom", "sales", "m1"))
    assert dedup.accept(("feishu", "default", "m1"))


@pytest.mark.asyncio
async def test_feishu_and_dingtalk_fake_inbound_transports(tmp_path):
    events: list[MessageEvent] = []
    media = ChannelMediaManager(tmp_path / "spool")
    feishu = FeishuAdapter("cli-test", "secret", media_manager=media)

    async def receive(event):
        events.append(event)

    gateway = Gateway(
        settings={
            "feishu": ConnectorSettings("feishu", enabled=True, allow_all=True),
            "dingtalk": ConnectorSettings("dingtalk", enabled=True, allow_all=True),
        },
        handler=receive,
    )
    gateway.register(feishu)

    async def feishu_download(_attachment):
        return "询价单.xlsx", b"PK\x03\x04xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    feishu._download_attachment = feishu_download  # type: ignore[method-assign]
    await feishu._on_payload(_feishu_payload(message_type="file"))
    await feishu.drain_inbound()
    assert events[-1].attachments[0].local_path

    ding = DingTalkAdapter("ding-test", "secret", media_manager=media)
    gateway.register(ding)

    async def ding_download(_attachment):
        return "合同.pdf", b"%PDF-1.7\ncontract", "application/pdf"

    ding._download_attachment = ding_download  # type: ignore[method-assign]
    await ding._on_payload(
        {
            "msgId": "d-file",
            "senderStaffId": "staff-1",
            "conversationId": "cid-group",
            "conversationType": "2",
            "isInAtList": True,
            "msgtype": "file",
            "content": {"downloadCode": "code", "fileName": "合同.pdf"},
        }
    )
    await ding.drain_inbound()
    assert events[-1].source.platform == "dingtalk"
    assert events[-1].attachments[0].local_path


@pytest.mark.asyncio
async def test_dingtalk_async_sdk_start_is_awaited_and_status_is_real(monkeypatch):
    started = threading.Event()

    class ChatbotHandler:
        pass

    class FakeClient:
        def __init__(self, _credential):
            self.websocket = None
            self._stop = None

        def register_callback_handler(self, _topic, _handler):
            return None

        async def start(self):
            self._stop = asyncio.Event()
            self.websocket = object()
            started.set()
            await self._stop.wait()
            self.websocket = None

        async def stop(self):
            if self._stop is not None:
                self._stop.set()

    module = types.ModuleType("dingtalk_stream")
    module.ChatbotHandler = ChatbotHandler
    module.AckMessage = types.SimpleNamespace(
        STATUS_OK=200, STATUS_SYSTEM_EXCEPTION=500
    )
    module.Credential = lambda client_id, client_secret: (client_id, client_secret)
    module.DingTalkStreamClient = FakeClient
    module.chatbot = types.SimpleNamespace(
        ChatbotMessage=types.SimpleNamespace(TOPIC="chatbot")
    )
    monkeypatch.setitem(sys.modules, "dingtalk_stream", module)

    adapter = DingTalkAdapter("client", "secret")

    async def access_token():
        return "token"

    adapter._access_token = access_token  # type: ignore[method-assign]
    try:
        assert await adapter.start()
        assert adapter.channel_status().state == "connecting"
        assert await asyncio.to_thread(started.wait, 2)
        for _ in range(50):
            if adapter.channel_status().authenticated:
                break
            await asyncio.sleep(0.01)
        assert adapter.channel_status().state == "connected"
        assert adapter.channel_status().authenticated
    finally:
        await adapter.stop()


@pytest.mark.asyncio
async def test_unauthorized_remote_attachment_is_not_downloaded(tmp_path):
    downloads = 0
    deliveries: list[MessageEvent] = []
    adapter = FeishuAdapter(
        "cli-test",
        "secret",
        media_manager=ChannelMediaManager(tmp_path / "spool"),
    )

    async def download(_attachment):
        nonlocal downloads
        downloads += 1
        return "询价单.xlsx", b"PK\x03\x04xlsx", "application/zip"

    async def receive(event):
        deliveries.append(event)

    adapter._download_attachment = download  # type: ignore[method-assign]
    gateway = Gateway(
        settings={"feishu": ConnectorSettings("feishu", enabled=True)},
        handler=receive,
    )
    gateway.register(adapter)
    await adapter._on_payload(_feishu_payload(message_type="file"))
    await adapter.drain_inbound()
    assert downloads == 0
    assert deliveries == []
    assert not list((tmp_path / "spool").rglob("*.xlsx"))


@pytest.mark.asyncio
async def test_weixin_fake_transport_context_text_and_file(tmp_path):
    adapter = WeixinIlinkAdapter("token", context_tokens={"wx-u": "ctx"})
    calls: list[tuple] = []

    class FakeApi:
        token = "token"

        async def send_items(self, to, context_token, items):
            calls.append((to, context_token, items))
            return {"ret": 0, "message_id": f"msg-{len(calls)}"}

        async def upload(self, data, to, media_type):
            calls.append(("upload", data, to, media_type))
            return {
                "encrypt_query_param": "param",
                "aes_key": "key",
                "ciphertext_size": 16,
            }

    adapter.api = FakeApi()  # type: ignore[assignment]
    assert (await adapter.send("wx-u", "你好")).ok
    assert (await adapter.send_file("wx-u", "报告.pdf", b"%PDF-x")).ok
    assert any(call[0] == "upload" for call in calls)
    assert not (await adapter.send("unknown", "你好")).ok


@pytest.mark.asyncio
async def test_weixin_multi_account_profiles_auth_routing_and_persistence(tmp_path):
    secrets = SecretStore(tmp_path / "secrets.json")
    for account_id, user_id in (("personal-a", "u-a"), ("personal-b", "u-b")):
        result = connect_connector(
            secrets,
            "weixin",
            {"account_id": account_id, "allowed_users": user_id},
            validate=False,
        )
        assert result["ok"] and result["account_id"] == account_id

    settings = load_settings(secrets)
    assert settings["weixin"].enabled
    assert set(settings["weixin"].accounts) == {"personal-a", "personal-b"}
    assert settings["weixin"].accounts["personal-a"].allowed_users == {"u-a"}

    first, second = FakeAdapter(), FakeAdapter()
    first.platform = second.platform = "weixin"
    first.account_id, second.account_id = "personal-a", "personal-b"
    gateway = Gateway(settings={"weixin": settings["weixin"]})
    gateway.register(first)
    gateway.register(second)
    result = await gateway.deliver("weixin:personal-b/wx-user", "发给 B")
    assert result.ok and first.outbox == []
    assert second.outbox[0]["chat_id"] == "wx-user"

    adapter = WeixinIlinkAdapter(
        "fresh-token", bot_id="wx-bot-a", account_id="personal-a", secrets=secrets
    )
    adapter._context_tokens["wx-user"] = "ctx-new"
    adapter._persist()
    persisted = secrets.get("weixin:account:personal-a") or {}
    assert persisted["token"] == "fresh-token"
    assert persisted["context_tokens"]["wx-user"] == "ctx-new"
    assert (secrets.get("weixin:default") or {})["default_account"] == "personal-a"


def test_weixin_blank_qr_refresh_preserves_account_credentials(tmp_path):
    secrets = SecretStore(tmp_path / "secrets.json")
    assert connect_connector(
        secrets,
        "weixin",
        {"account_id": "personal", "allowed_users": "owner"},
        validate=False,
    )["ok"]
    profile = secrets.get("weixin:account:personal") or {}
    profile.update(
        {
            "token": "saved-token",
            "bot_id": "saved-bot",
            "context_tokens": {"owner": "ctx"},
            "get_updates_buf": "cursor",
        }
    )
    secrets.put("weixin:account:personal", profile)

    assert connect_connector(secrets, "weixin", {}, validate=False)["ok"]
    refreshed = secrets.get("weixin:account:personal") or {}
    assert refreshed["token"] == "saved-token"
    assert refreshed["bot_id"] == "saved-bot"
    assert refreshed["context_tokens"] == {"owner": "ctx"}
    assert refreshed["get_updates_buf"] == "cursor"


@pytest.mark.asyncio
async def test_weixin_qr_contract_confirms_and_persists_owner(tmp_path):
    secrets = SecretStore(tmp_path / "secrets.json")
    connect_connector(
        secrets,
        "weixin",
        {"account_id": "phone"},
        validate=False,
    )

    class FakeApi:
        token = ""
        base_url = "https://ilinkai.weixin.qq.com"
        cdn_base_url = "https://novac2c.cdn.weixin.qq.com/c2c"

        def __init__(self):
            self.local_tokens = None

        async def fetch_qr(self, local_tokens):
            self.local_tokens = local_tokens
            return {"qrcode": "qr-id", "qrcode_img_content": "https://qr.test/payload"}

        async def poll_qr(self, qrcode, *, verify_code="", base_url=""):
            assert qrcode == "qr-id"
            return {
                "status": "confirmed",
                "bot_token": "fresh-token",
                "ilink_bot_id": "fresh-bot",
                "ilink_user_id": "owner-user",
                "baseurl": "https://ilinkai.weixin.qq.com",
            }

        async def get_updates(self, _cursor):
            await asyncio.sleep(3600)
            return {"ret": 0, "msgs": []}

    adapter = WeixinIlinkAdapter(account_id="phone", secrets=secrets)
    fake = FakeApi()
    adapter.api = fake  # type: ignore[assignment]
    try:
        assert await adapter.start()
        for _ in range(50):
            if adapter.channel_status().authenticated:
                break
            await asyncio.sleep(0.01)
        assert adapter.channel_status().authenticated
        persisted = secrets.get("weixin:account:phone") or {}
        assert persisted["token"] == "fresh-token"
        assert "owner-user" in persisted["allowed_users"]
        assert fake.local_tokens == []
    finally:
        await adapter.stop()


@pytest.mark.asyncio
async def test_wecom_users_and_group_mentions_get_isolated_stable_sessions(
    tmp_path, monkeypatch
):
    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "data",
        provider=_TextProvider(),
    )
    deliveries = []

    async def capture(session_id, message, *, event, source=None, target=""):
        deliveries.append((session_id, message, target))

    monkeypatch.setattr(manager, "deliver_channel_to_session", capture)

    def event(user, chat, message_id, *, chat_type="dm", account="default"):
        return MessageEvent(
            text=f"question-{message_id}",
            source=SessionSource(
                platform="wecom",
                account_id=account,
                chat_id=chat,
                user_id=user,
                user_name=user,
                chat_type=chat_type,
            ),
            message_id=message_id,
            mentions_me=chat_type == "group",
        )

    await manager._dispatch_inbound(event("alice", "alice", "dm-1"))
    await manager._dispatch_inbound(event("bob", "bob", "dm-2"))
    assert manager.mention_sessions.get("wecom:alice") != manager.mention_sessions.get(
        "wecom:bob"
    )

    await manager._dispatch_inbound(
        event("alice", "room-1", "group-1", chat_type="group")
    )
    first_group = manager.mention_sessions.get("wecom:room-1")
    await manager._dispatch_inbound(
        event("bob", "room-1", "group-2", chat_type="group")
    )
    assert first_group and manager.mention_sessions.get("wecom:room-1") == first_group
    assert len({row.session_id for row in manager.mention_sessions.all()}) == 3
    assert deliveries[-1][2] == "wecom:room-1"


@pytest.mark.asyncio
async def test_plain_agent_answer_is_delivered_as_channel_final(tmp_path):
    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "data",
        provider=_TextProvider(),
    )

    class CaptureGateway:
        def __init__(self):
            self.sent = []

        async def deliver_envelope(self, target, envelope):
            self.sent.append((target, envelope))
            return SendResult(True, message_id="sent-1")

    gateway = CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    engine = manager.get_engine("channel-session", agent="chat")
    assert engine is not None
    manager.save("channel-session", engine)
    await manager.deliver_to_session(
        "channel-session",
        "你好",
        source={
            "connector": "wecom",
            "kind": "dm",
            "target": "wecom:alice",
            "message_id": "m-final",
        },
    )
    assert gateway.sent[0][0] == "wecom:alice"
    assert gateway.sent[0][1].text.startswith("这是可靠的通道回复")


def test_gateway_status_exposes_single_account_qr_in_accounts_array():
    """AccountsDetail reads details.accounts; single-account must not omit that shape."""
    from coworker.channels.models import ChannelCapabilities, ChannelStatus
    from coworker.connectors.config import ConnectorSettings
    from coworker.connectors.gateway import Gateway

    class QrAdapter:
        platform = "weixin"
        account_id = "default"

        def set_message_handler(self, _handler):
            return None

        def set_interaction_handler(self, _handler):
            return None

        def channel_status(self):
            return ChannelStatus(
                platform="weixin",
                account_id="default",
                state="auth_required",
                authenticated=False,
                capabilities=ChannelCapabilities(direct_messages=True),
                details={"qr_url": "https://example.test/qr.png"},
            )

    gw = Gateway(
        settings={
            "weixin": ConnectorSettings(
                platform="weixin",
                enabled=True,
                allow_all=True,
            )
        }
    )
    gw.register(QrAdapter())  # type: ignore[arg-type]
    weixin = next(r for r in gw.status() if r["platform"] == "weixin")
    assert weixin["state"] == "auth_required"
    assert weixin["details"]["qr_url"] == "https://example.test/qr.png"
    assert weixin["details"]["accounts"][0]["details"]["qr_url"] == (
        "https://example.test/qr.png"
    )


def test_send_file_defaults_to_current_channel_and_keeps_approval(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "报告.csv").write_text("a,b\n1,2", encoding="utf-8")
    secrets = SecretStore(tmp_path / "secrets.json")
    secrets.put(
        "feishu:default", {"app_id": "cli-test", "app_secret": "secret", "enabled": True}
    )
    sent: list[tuple] = []

    def sender(token, chat_id, thread_id, filename, data, title, comment):
        sent.append((token, chat_id, filename, data))
        return SendResult(True, message_id="file-1")

    tool = make_send_file_tool(
        secrets, workspace=workspace, file_senders={"feishu": sender}
    )
    context = set_current_channel_target("feishu:oc-chat")
    try:
        result = tool(path="报告.csv")
    finally:
        reset_current_channel_target(context)
    assert result["ok"] and result["target"] == "feishu:oc-chat"
    assert sent[0][1:3] == ("oc-chat", "报告.csv")
    assert tool.__aisuite_tool_metadata__.requires_approval is True
    assert "error" in tool(path="报告.csv")


def test_exact_channel_sdk_pins_and_lock_hashes():
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    messaging = set(project["project"]["optional-dependencies"]["messaging"])
    expected = {
        "wecom-aibot-sdk==1.0.8",
        "lark-oapi==1.7.3",
        "dingtalk-stream==0.24.4b1",
        "pycryptodome==3.23.0",
        "cos-python-sdk-v5==1.9.38",
    }
    assert expected <= messaging
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    packages = {row["name"]: row for row in lock["package"]}
    for requirement in expected:
        name, version = requirement.split("==")
        row = packages[name]
        assert row["version"] == version
        hashes = [item.get("hash", "") for item in row.get("wheels", [])]
        assert hashes and all(value.startswith("sha256:") for value in hashes)


def test_channel_modules_and_locked_sdks_import_in_frozen_shape():
    import Crypto.Cipher.AES  # noqa: F401
    import dingtalk_stream  # noqa: F401
    import lark_oapi  # noqa: F401
    import wecom_aibot_sdk  # noqa: F401
    import qcloud_cos  # noqa: F401
    import coworker.connectors.dingtalk_bot  # noqa: F401
    import coworker.connectors.feishu_bot  # noqa: F401
    import coworker.connectors.wecom_bot  # noqa: F401
    import coworker.connectors.weixin_ilink  # noqa: F401
    import coworker.filestore  # noqa: F401
