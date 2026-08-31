"""Feishu/Lark WebSocket Channel adapter (D-193).

The SDK is used only for the long connection. REST is kept behind the adapter for
messages and media, which makes the protocol contract straightforward to fake in tests.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Optional

from ..channels.mappings import inbound_to_message_event
from ..channels.media import ChannelMediaManager
from ..channels.models import ChannelAttachment, ChannelCapabilities, OutboundEnvelope
from ..channels.platform_mappings import feishu_event_to_inbound
from .base import BasePlatformAdapter, SendResult

logger = logging.getLogger("coworker.connectors.feishu")
_LIVE: dict[str, "FeishuAdapter"] = {}


def live_adapter(account_key: str = "") -> Optional["FeishuAdapter"]:
    if account_key and account_key in _LIVE:
        return _LIVE[account_key]
    if len(_LIVE) == 1:
        return next(iter(_LIVE.values()))
    return None


class FeishuAdapter(BasePlatformAdapter):
    platform = "feishu"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        account_id: str = "default",
        media_manager: Optional[ChannelMediaManager] = None,
        api_base: str = "https://open.feishu.cn/open-apis",
    ) -> None:
        super().__init__()
        self.app_id = app_id
        self.app_secret = app_secret
        self.account_id = account_id or "default"
        self.api_base = api_base.rstrip("/")
        self._media = media_manager
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._client: Any = None
        self._thread: Optional[threading.Thread] = None
        self._sdk_loop: Optional[asyncio.AbstractEventLoop] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._closing = False
        self._token = ""
        self._token_expiry = 0.0
        self._bot_open_id = ""
        self._sent_keys: set[str] = set()
        self.capabilities = ChannelCapabilities(
            direct_messages=True,
            group_chat=True,
            group_mentions=True,
            proactive_messages=True,
            streaming=False,
            receive_images=True,
            send_images=True,
            receive_files=True,
            send_files=True,
            max_inbound_bytes=30 * 1024 * 1024,
            max_outbound_bytes=30 * 1024 * 1024,
        )

    async def start(self) -> bool:
        """Keep status at connecting until the SDK has a real WebSocket."""
        return await self.connect()

    async def _access_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.api_base}/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            data = response.json()
        if response.status_code >= 400 or data.get("code") not in (None, 0):
            raise RuntimeError(data.get("msg") or f"HTTP {response.status_code}")
        token = str(data.get("tenant_access_token") or "")
        if not token:
            raise RuntimeError("飞书未返回 tenant_access_token")
        self._token = token
        self._token_expiry = time.time() + max(60, int(data.get("expire") or 7200) - 300)
        return token

    async def connect(self) -> bool:
        self._channel_state = "connecting"
        self._loop = asyncio.get_running_loop()
        self._closing = False
        try:
            await self._access_token()
            import lark_oapi as lark
        except ImportError:
            self._channel_state = "degraded"
            self._last_error = "未安装 lark-oapi"
            return False
        except Exception as exc:
            self._channel_state = "auth_required"
            self._last_error = f"飞书认证失败（{type(exc).__name__}）"
            return False

        def on_message(data) -> None:
            try:
                raw = data if isinstance(data, dict) else json.loads(lark.JSON.marshal(data))
                asyncio.run_coroutine_threadsafe(self._on_payload(raw), self._loop)
            except Exception as exc:
                self._last_error = f"飞书事件解析失败（{type(exc).__name__}）"
                logger.exception("feishu event mapping failed")

        try:
            builder = lark.EventDispatcherHandler.builder("", "")
            builder.register_p2_im_message_receive_v1(on_message)
            handler = builder.build()
            client = lark.ws.Client(self.app_id, self.app_secret, event_handler=handler)
            self._client = client
            import lark_oapi.ws.client as lark_ws_client

            # lark-oapi 1.7.3 owns a module-level loop. Give this adapter a fresh
            # loop so hot reconnect does not reuse a stopped loop from the prior client.
            sdk_loop = asyncio.new_event_loop()
            lark_ws_client.loop = sdk_loop
            self._sdk_loop = sdk_loop

            def on_reconnecting() -> None:
                self._channel_state = "connecting"
                self._channel_authenticated = False
                self._reconnect_count += 1

            def on_reconnected() -> None:
                self._channel_state = "connected"
                self._channel_authenticated = True
                self._last_error = ""

            client.on_reconnecting = on_reconnecting
            client.on_reconnected = on_reconnected

            def run() -> None:
                asyncio.set_event_loop(sdk_loop)
                if self._closing:
                    sdk_loop.close()
                    return
                try:
                    client.start()
                except Exception as exc:
                    if not self._closing:
                        self._last_error = (
                            f"飞书长连接停止（{type(exc).__name__}）"
                        )
                        self._channel_state = "degraded"
                        self._channel_authenticated = False
                        logger.exception("feishu websocket stopped")
                finally:
                    if not sdk_loop.is_closed():
                        sdk_loop.close()

            self._thread = threading.Thread(
                target=run, daemon=True, name=f"chemclaw-feishu-{self.account_id}"
            )
            self._thread.start()
            self._monitor_task = asyncio.create_task(
                self._monitor_connection(),
                name=f"channel-monitor:feishu:{self.account_id}",
            )
        except Exception as exc:
            self._channel_state = "degraded"
            self._last_error = f"飞书长连接启动失败（{type(exc).__name__}）"
            return False
        _LIVE[self.account_id] = self
        _LIVE[self.app_id] = self
        self._channel_state = "connecting"
        self._channel_authenticated = False
        return True

    async def _monitor_connection(self) -> None:
        was_connected = False
        while not self._closing and self._client is not None:
            connected = getattr(self._client, "_conn", None) is not None
            if connected:
                self._channel_state = "connected"
                self._channel_authenticated = True
                self._last_error = ""
            elif was_connected:
                self._channel_state = "connecting"
                self._channel_authenticated = False
                self._reconnect_count += 1
            was_connected = connected
            await asyncio.sleep(0.25)

    async def disconnect(self) -> None:
        self._closing = True
        _LIVE.pop(self.account_id, None)
        _LIVE.pop(self.app_id, None)
        client, self._client = self._client, None
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            await asyncio.gather(self._monitor_task, return_exceptions=True)
            self._monitor_task = None
        sdk_loop = self._sdk_loop
        if client is not None and sdk_loop is not None and sdk_loop.is_running():
            disconnect = getattr(client, "_disconnect", None)
            if callable(disconnect):
                try:
                    future = asyncio.run_coroutine_threadsafe(disconnect(), sdk_loop)
                    await asyncio.wrap_future(future)
                except Exception:
                    logger.debug("feishu close failed", exc_info=True)
            sdk_loop.call_soon_threadsafe(sdk_loop.stop)
        thread, self._thread = self._thread, None
        if thread is not None and thread.is_alive():
            await asyncio.to_thread(thread.join, 5)
        self._sdk_loop = None
        self._channel_state = "disconnected"
        self._channel_authenticated = False

    async def _on_payload(self, payload: dict[str, Any]) -> None:
        inbound = feishu_event_to_inbound(
            payload, account_id=self.account_id, bot_open_id=self._bot_open_id
        )
        if inbound is None:
            return
        event = inbound_to_message_event(inbound, raw=payload)
        if self._media is not None and inbound.attachments:
            async def load_attachments() -> list[str]:
                return await self._media.materialize(inbound, self._download_attachment)

            event.attachment_loader = load_attachments
        await self.enqueue_message(event)

    async def _download_attachment(self, attachment: ChannelAttachment):
        import httpx

        token = await self._access_token()
        message_id = str(attachment.metadata.get("message_id") or "")
        resource_type = str(attachment.metadata.get("resource_type") or "file")
        if resource_type not in {"image", "file"}:
            resource_type = "file"
        url = (
            f"{self.api_base}/im/v1/messages/{message_id}/resources/"
            f"{attachment.remote_ref}"
        )
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(
                url,
                params={"type": resource_type},
                headers={"Authorization": f"Bearer {token}"},
            )
        if response.status_code >= 400:
            raise RuntimeError(f"飞书附件下载失败（HTTP {response.status_code}）")
        return attachment.name, response.content, response.headers.get("content-type", "")

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
            chat_id, text, thread_id = envelope.conversation_id, envelope.text, envelope.reply_to
            if envelope.attachments:
                last: Optional[SendResult] = None
                if text:
                    last = await self.send(str(chat_id), text)
                    if not last.ok:
                        return last
                for attachment in envelope.attachments:
                    path = Path(attachment.local_path)
                    if not path.is_file() or path.is_symlink():
                        return SendResult(False, error="待发送附件不存在或不是普通文件")
                    last = await self.send_file(
                        str(chat_id), attachment.name or path.name, path.read_bytes()
                    )
                    if not last.ok:
                        return last
                result = last or SendResult(True)
                if result.ok and envelope.idempotency_key:
                    self._sent_keys.add(envelope.idempotency_key)
                return result
        try:
            result = await self._send_message(str(chat_id), "text", {"text": text or ""})
            if envelope is not None and envelope.idempotency_key:
                self._sent_keys.add(envelope.idempotency_key)
            return result
        except Exception as exc:
            self._last_error = f"飞书消息发送失败（{type(exc).__name__}）"
            return SendResult(False, error=self._last_error)

    async def _send_message(self, chat_id: str, msg_type: str, content: dict[str, Any]) -> SendResult:
        import httpx

        token = await self._access_token()
        for attempt in range(3):
            await self.throttle_outbound()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.api_base}/im/v1/messages",
                    params={"receive_id_type": "chat_id"},
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "receive_id": chat_id,
                        "msg_type": msg_type,
                        "content": json.dumps(content, ensure_ascii=False),
                    },
                )
                data = response.json()
            if response.status_code != 429 and response.status_code < 500:
                break
            if attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))
        if response.status_code >= 400 or data.get("code") not in (None, 0):
            return SendResult(False, error=str(data.get("msg") or f"HTTP {response.status_code}"))
        self._last_sent_at = time.time()
        return SendResult(True, message_id=str((data.get("data") or {}).get("message_id") or ""))

    async def send_file(
        self,
        chat_id: str,
        filename: str,
        data: bytes,
        *,
        title: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> SendResult:
        import httpx

        if len(data) > (self.capabilities.max_outbound_bytes or len(data)):
            return SendResult(False, error="飞书附件超过 30 MB 限制")
        token = await self._access_token()
        suffix = Path(filename).suffix.lower()
        is_image = suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        endpoint = "images" if is_image else "files"
        form = {"image_type": "message"} if is_image else {"file_type": "stream", "file_name": filename}
        field = "image" if is_image else "file"
        for attempt in range(3):
            await self.throttle_outbound()
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.api_base}/im/v1/{endpoint}",
                    headers={"Authorization": f"Bearer {token}"},
                    data=form,
                    files={field: (filename, data)},
                )
                uploaded = response.json()
            if response.status_code != 429 and response.status_code < 500:
                break
            if attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))
        if response.status_code >= 400 or uploaded.get("code") not in (None, 0):
            return SendResult(False, error=str(uploaded.get("msg") or "飞书附件上传失败"))
        key_name = "image_key" if is_image else "file_key"
        key = str((uploaded.get("data") or {}).get(key_name) or "")
        if not key:
            return SendResult(False, error=f"飞书上传完成但未返回 {key_name}")
        if comment:
            comment_result = await self.send(chat_id, comment)
            if not comment_result.ok:
                return comment_result
        return await self._send_message(chat_id, "image" if is_image else "file", {key_name: key})

    def send_sync(self, chat_id: str, text: str, *, thread_id: Optional[str] = None) -> SendResult:
        if self._loop is None or not self._loop.is_running():
            return SendResult(False, error="飞书事件循环未运行")
        future = asyncio.run_coroutine_threadsafe(self.send(chat_id, text, thread_id=thread_id), self._loop)
        try:
            return future.result(timeout=60)
        except Exception as exc:
            return SendResult(False, error=f"飞书消息发送失败（{type(exc).__name__}）")

    def send_file_sync(
        self, chat_id: str, filename: str, data: bytes, *, title=None, comment=None
    ) -> SendResult:
        if self._loop is None or not self._loop.is_running():
            return SendResult(False, error="飞书事件循环未运行")
        future = asyncio.run_coroutine_threadsafe(
            self.send_file(chat_id, filename, data, title=title, comment=comment), self._loop
        )
        try:
            return future.result(timeout=180)
        except Exception as exc:
            return SendResult(False, error=f"飞书文件发送失败（{type(exc).__name__}）")
