"""WeCom AI Bot inbound adapter — WebSocket long connection (D-188).

Uses optional `wecom-aibot-sdk` (lazy import). Outbound for `send_message` goes through
the live adapter registry (WS active push), not HTTP bot tokens.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path
from time import time
from typing import Any, Optional

from ..channels.mappings import frame_to_inbound, inbound_to_message_event
from ..channels.media import ChannelMediaManager
from ..channels.models import (
    ChannelAttachment,
    ChannelCapabilities,
    OutboundEnvelope,
)
from .base import BasePlatformAdapter, SendResult

logger = logging.getLogger("coworker.connectors.wecom")

# Live adapters keyed by bot_id — sync send_message tool looks these up.
_LIVE: dict[str, "WecomBotAdapter"] = {}

# Attachment safety (Phase 6)
_MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
_ALLOWED_IMAGE_EXT = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})
_PROGRESS_ACK_ZH = "ChemClaw 正在处理…"


def live_adapter(bot_id: str = "") -> Optional["WecomBotAdapter"]:
    if bot_id and bot_id in _LIVE:
        return _LIVE[bot_id]
    if len(_LIVE) == 1:
        return next(iter(_LIVE.values()))
    return None


class WecomBotAdapter(BasePlatformAdapter):
    platform = "wecom"

    def __init__(
        self,
        bot_id: str,
        secret: str,
        *,
        account_id: str = "default",
        attachment_dir: Optional[Path] = None,
        media_manager: Optional[ChannelMediaManager] = None,
    ) -> None:
        super().__init__()
        self.account_id = account_id or "default"
        self.bot_id = bot_id
        self.secret = secret
        self._client: Any = None
        self._connect_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._media = media_manager or (
            ChannelMediaManager(attachment_dir) if attachment_dir is not None else None
        )
        self._seen_ids: set[str] = set()
        self._seen_order: list[str] = []
        self._ack_enabled = os.environ.get("CHEMCLAW_WECOM_ACK", "1").lower() not in (
            "0",
            "false",
            "no",
        )
        self._sent_keys: set[str] = set()
        self._reply_frames: dict[str, dict[str, Any]] = {}
        self._reply_streams: dict[str, tuple[dict[str, Any], str]] = {}
        self.capabilities = ChannelCapabilities(
            direct_messages=True,
            group_chat=True,
            group_mentions=True,
            proactive_messages=True,
            streaming=True,
            receive_images=True,
            send_images=True,
            receive_files=True,
            send_files=True,
            max_inbound_bytes=_MAX_ATTACHMENT_BYTES,
            max_outbound_bytes=50 * 1024 * 1024,
        )

    async def start(self) -> bool:
        """Start the SDK without treating socket creation as authentication success."""
        return await self.connect()

    async def connect(self) -> bool:
        self._channel_state = "connecting"
        try:
            from wecom_aibot_sdk import WSClient
        except ImportError:
            logger.error(
                "wecom-aibot-sdk not installed — install wecom-aibot-sdk==1.0.8 "
                "into the ChemClaw runtime (pip install -e '.[messaging]') and restart"
            )
            self._channel_state = "degraded"
            self._last_error = "未安装 wecom-aibot-sdk==1.0.8"
            return False
        if self._client is not None:
            await self.disconnect()

        self._loop = asyncio.get_running_loop()
        client = WSClient(
            bot_id=self.bot_id,
            secret=self.secret,
            max_reconnect_attempts=-1,
        )
        client.on("message", self._on_frame)

        def _on_authenticated():
            self._channel_state = "connected"
            self._channel_authenticated = True
            self._last_error = ""

        def _on_disconnected(_reason=None):
            self._channel_state = (
                "connecting" if self._client is not None else "disconnected"
            )
            self._channel_authenticated = False

        def _on_reconnecting(_attempt=None):
            self._channel_state = "connecting"
            self._channel_authenticated = False
            self._reconnect_count += 1

        def _on_error(err):
            self._last_error = f"企业微信连接异常（{type(err).__name__}）"
            self._channel_state = "degraded"
            self._channel_authenticated = False
            logger.warning("wecom ws error: %s", type(err).__name__)

        client.on("authenticated", _on_authenticated)
        client.on("disconnected", _on_disconnected)
        client.on("reconnecting", _on_reconnecting)
        client.on("error", _on_error)
        self._client = client
        _LIVE[self.bot_id] = self
        try:
            await client.connect()
        except Exception:
            logger.exception("wecom connect failed")
            _LIVE.pop(self.bot_id, None)
            self._client = None
            self._channel_state = "degraded"
            self._channel_authenticated = False
            self._last_error = "企业微信连接或认证失败"
            return False
        # SDK connect() starts the socket/auth exchange and may schedule a retry after
        # failure.  Only the authenticated event is proof that messages can be sent.
        if self._channel_state == "connecting":
            self._channel_authenticated = False
        return True

    async def disconnect(self) -> None:
        _LIVE.pop(self.bot_id, None)
        client = self._client
        self._client = None
        if client is None:
            self._reply_frames.clear()
            self._reply_streams.clear()
            self._channel_state = "disconnected"
            self._channel_authenticated = False
            return
        try:
            await client.disconnect()
        except Exception:
            logger.debug("wecom disconnect error", exc_info=True)
        finally:
            self._reply_frames.clear()
            self._reply_streams.clear()
            self._channel_state = "disconnected"
            self._channel_authenticated = False

    async def send(
        self,
        chat_id: str | OutboundEnvelope,
        text: Optional[str] = None,
        *,
        thread_id: Optional[str] = None,
    ) -> SendResult:
        envelope = chat_id if isinstance(chat_id, OutboundEnvelope) else None
        if envelope is not None:
            if envelope.idempotency_key and envelope.idempotency_key in self._sent_keys:
                return SendResult(True, message_id=envelope.idempotency_key)
            chat_id = envelope.conversation_id
            text = envelope.text
            thread_id = envelope.reply_to
            if envelope.attachments:
                result = await self._send_attachments(
                    str(chat_id), envelope.attachments, comment=text or None
                )
                if result.ok and envelope.idempotency_key:
                    self._sent_keys.add(envelope.idempotency_key)
                return result
        _ = thread_id
        client = self._client
        if client is None or not self._channel_authenticated:
            return SendResult(False, error="企业微信尚未完成连接认证，请稍后重试")
        try:
            await self.throttle_outbound()
            target = str(chat_id)
            pending_stream = self._reply_streams.pop(target, None)
            if pending_stream is not None:
                frame, stream_id = pending_stream
                await client.reply_stream(frame, stream_id, text or "", finish=True)
                self._reply_frames.pop(target, None)
            else:
                frame = self._reply_frames.pop(target, None)
                if frame is not None:
                    await client.reply(
                        frame,
                        {
                            "msgtype": "markdown",
                            "markdown": {"content": text or ""},
                        },
                    )
                else:
                    await client.send_message(
                        target,
                        {
                            "msgtype": "markdown",
                            "markdown": {"content": text or ""},
                        },
                    )
            self._last_sent_at = time()
            if envelope is not None and envelope.idempotency_key:
                self._sent_keys.add(envelope.idempotency_key)
            return SendResult(True)
        except Exception as exc:
            logger.exception("wecom send failed")
            self._last_error = f"企业微信消息发送失败（{type(exc).__name__}）"
            return SendResult(False, error=self._last_error)

    async def _send_attachments(
        self,
        chat_id: str,
        attachments: list[ChannelAttachment],
        *,
        comment: Optional[str] = None,
    ) -> SendResult:
        client = self._client
        if client is None:
            return SendResult(False, error="企业微信未连接")
        if comment:
            text_result = await self.send(chat_id, comment)
            if not text_result.ok:
                return text_result
        last_id: Optional[str] = None
        for attachment in attachments:
            path = Path(attachment.local_path)
            if not attachment.local_path or not path.is_file() or path.is_symlink():
                return SendResult(False, error="待发送附件不存在或不是普通文件")
            data = path.read_bytes()
            if len(data) > (self.capabilities.max_outbound_bytes or len(data)):
                return SendResult(False, error="企业微信附件超过 50 MB 限制")
            media_type = "image" if attachment.kind == "image" else "file"
            try:
                await self.throttle_outbound()
                uploaded = await client.upload_media(
                    data, type=media_type, filename=attachment.name or path.name
                )
                media_id = str((uploaded or {}).get("media_id") or "")
                if not media_id:
                    return SendResult(False, error="企业微信上传完成但未返回 media_id")
                await self.throttle_outbound()
                await client.send_media_message(chat_id, media_type, media_id)
                last_id = media_id
            except Exception as exc:
                self._last_error = f"企业微信文件发送失败（{type(exc).__name__}）"
                return SendResult(False, error=self._last_error)
        self._last_sent_at = time()
        return SendResult(True, message_id=last_id)

    async def send_file(
        self,
        chat_id: str,
        filename: str,
        data: bytes,
        *,
        title: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> SendResult:
        _ = title
        client = self._client
        if client is None or not self._channel_authenticated:
            return SendResult(False, error="企业微信尚未完成连接认证，请稍后重试")
        if comment:
            sent = await self.send(chat_id, comment)
            if not sent.ok:
                return sent
        try:
            media_type = "image" if Path(filename).suffix.lower() in _ALLOWED_IMAGE_EXT else "file"
            await self.throttle_outbound()
            uploaded = await client.upload_media(data, type=media_type, filename=filename)
            media_id = str((uploaded or {}).get("media_id") or "")
            if not media_id:
                return SendResult(False, error="企业微信上传完成但未返回 media_id")
            await self.throttle_outbound()
            await client.send_media_message(chat_id, media_type, media_id)
            self._last_sent_at = time()
            return SendResult(True, message_id=media_id)
        except Exception as exc:
            self._last_error = f"企业微信文件发送失败（{type(exc).__name__}）"
            return SendResult(False, error=self._last_error)

    async def acknowledge(self, event, text: str = _PROGRESS_ACK_ZH) -> None:
        """Begin a frame-bound reply stream after Gateway authorization."""
        if not isinstance(getattr(event, "raw", None), dict):
            return
        chat_id = str(getattr(event.source, "chat_id", "") or "")
        frame = event.raw
        self._reply_frames[chat_id] = frame
        # Bound memory even if a turn is cancelled before it produces a final reply.
        while len(self._reply_frames) > 500:
            stale_chat = next(iter(self._reply_frames))
            self._reply_frames.pop(stale_chat, None)
            self._reply_streams.pop(stale_chat, None)
        if not self._ack_enabled:
            return
        client = self._client
        if client is None or frame is None:
            return
        stream_id = f"chemclaw-{uuid.uuid4().hex[:20]}"
        try:
            await self.throttle_outbound()
            await client.reply_stream(frame, stream_id, text, finish=False)
            self._reply_streams[chat_id] = (frame, stream_id)
            self._last_sent_at = time()
        except Exception as exc:
            self._last_error = f"企业微信进度回复失败（{type(exc).__name__}）"
            logger.debug("wecom progress ack failed", exc_info=True)

    def send_sync(
        self, chat_id: str, text: str, *, thread_id: Optional[str] = None
    ) -> SendResult:
        """Bridge sync ToolRegistry → async WS send (engine runs tools in a thread)."""
        loop = self._loop
        if loop is None or not loop.is_running():
            return SendResult(False, error="企业微信事件循环未运行")
        fut = asyncio.run_coroutine_threadsafe(
            self.send(chat_id, text, thread_id=thread_id), loop
        )
        try:
            return fut.result(timeout=45)
        except Exception as exc:
            return SendResult(False, error=str(exc))

    def send_file_sync(
        self,
        chat_id: str,
        filename: str,
        data: bytes,
        *,
        title: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> SendResult:
        loop = self._loop
        if loop is None or not loop.is_running():
            return SendResult(False, error="企业微信事件循环未运行")
        future = asyncio.run_coroutine_threadsafe(
            self.send_file(
                chat_id, filename, data, title=title, comment=comment
            ),
            loop,
        )
        try:
            return future.result(timeout=180)
        except Exception as exc:
            return SendResult(False, error=str(exc))

    async def _on_frame(self, frame: Any) -> None:
        if not isinstance(frame, dict):
            return
        inbound = frame_to_inbound({**frame, "account_id": self.account_id})
        if inbound is None:
            return
        mid = inbound.message_id or ""
        if mid:
            if mid in self._seen_ids:
                return
            self._seen_ids.add(mid)
            self._seen_order.append(mid)
            while len(self._seen_order) > 500:
                old = self._seen_order.pop(0)
                self._seen_ids.discard(old)

        event = inbound_to_message_event(inbound, raw=frame)
        if self._media is not None and inbound.attachments:
            async def load_attachments() -> list[str]:
                return await self._media.materialize(inbound, self._download_attachment)

            event.attachment_loader = load_attachments
        await self.enqueue_message(event)

    async def _download_attachment(self, attachment: ChannelAttachment):
        client = self._client
        if client is None or not hasattr(client, "download_file"):
            raise RuntimeError("企业微信 SDK 不支持附件下载")
        result = await client.download_file(
            attachment.remote_ref, attachment.encryption.get("aes_key") or None
        )
        if not isinstance(result, dict) or not isinstance(result.get("buffer"), (bytes, bytearray)):
            raise RuntimeError("企业微信未返回可用文件数据")
        return (
            str(result.get("filename") or attachment.name),
            result["buffer"],
            attachment.mime_type,
        )
