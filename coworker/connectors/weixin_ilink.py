"""Tencent official Weixin iLink direct-message Channel (D-193).

Protocol reference: Tencent ``openclaw-weixin``. There is no desktop injection,
accessibility automation or unofficial hook in this adapter.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import random
import ssl
import time
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from ..channels.mappings import inbound_to_message_event
from ..channels.media import ChannelMediaManager
from ..channels.models import ChannelAttachment, ChannelCapabilities, OutboundEnvelope
from ..channels.platform_mappings import weixin_update_to_inbound
from .base import BasePlatformAdapter, SendResult

logger = logging.getLogger("coworker.connectors.weixin")

DEFAULT_BASE_URL = "https://ilinkai.weixin.qq.com"
DEFAULT_CDN_BASE_URL = "https://novac2c.cdn.weixin.qq.com/c2c"
# Wire values mirrored from Tencent openclaw-weixin v2.4.6
# (commit cef0bfc390393f716903e16d50408118047f87e0).
CHANNEL_VERSION = "2.4.6"
CLIENT_VERSION = str((2 << 16) | (4 << 8) | 6)
_LIVE: dict[str, "WeixinIlinkAdapter"] = {}


def live_adapter(account_key: str = "") -> Optional["WeixinIlinkAdapter"]:
    if account_key and account_key in _LIVE:
        return _LIVE[account_key]
    if len(_LIVE) == 1:
        return next(iter(_LIVE.values()))
    return None


def _common_headers() -> dict[str, str]:
    return {
        "iLink-App-Id": "bot",
        "iLink-App-ClientVersion": CLIENT_VERSION,
    }


def _headers(token: str = "") -> dict[str, str]:
    uin = base64.b64encode(str(random.randint(0, 0xFFFFFFFF)).encode()).decode()
    out = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": uin,
        **_common_headers(),
    }
    if token:
        out["Authorization"] = f"Bearer {token}"
    return out


def _aes_encrypt(data: bytes, key: bytes) -> bytes:
    from Crypto.Cipher import AES

    pad = 16 - len(data) % 16
    return AES.new(key, AES.MODE_ECB).encrypt(data + bytes([pad]) * pad)


def _aes_decrypt(data: bytes, key: bytes) -> bytes:
    from Crypto.Cipher import AES

    raw = AES.new(key, AES.MODE_ECB).decrypt(data)
    pad = raw[-1]
    return raw[:-pad] if 0 < pad <= 16 else raw


def _decode_aes_key(value: str) -> bytes:
    try:
        key = bytes.fromhex(value)
        if len(key) == 16:
            return key
    except (TypeError, ValueError):
        pass
    decoded = base64.b64decode(value)
    if len(decoded) == 32:
        decoded = bytes.fromhex(decoded.decode("ascii"))
    if len(decoded) != 16:
        raise ValueError("iLink AES key 长度无效")
    return decoded


def _cdn_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    try:
        context.set_ciphers("DEFAULT@SECLEVEL=1")
    except ssl.SSLError:
        pass
    return context


class WeixinIlinkApi:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        cdn_base_url: str = DEFAULT_CDN_BASE_URL,
        token: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cdn_base_url = cdn_base_url.rstrip("/")
        self.token = token

    async def post(self, endpoint: str, body: dict[str, Any], *, timeout: float = 20) -> dict[str, Any]:
        import httpx

        base_info = body.setdefault("base_info", {})
        base_info.setdefault("channel_version", CHANNEL_VERSION)
        base_info.setdefault("bot_agent", f"ChemClaw/{CHANNEL_VERSION}")
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/{endpoint}", headers=_headers(self.token), json=body
                    )
                    response.raise_for_status()
                    return response.json()
            except httpx.TimeoutException:
                if endpoint.endswith("getupdates"):
                    return {"ret": 0, "msgs": []}
                if attempt >= 2:
                    raise
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if (status != 429 and status < 500) or attempt >= 2:
                    raise
            except httpx.TransportError:
                if attempt >= 2:
                    raise
            await asyncio.sleep(0.5 * (2**attempt))
        raise RuntimeError("iLink 请求重试耗尽")

    async def fetch_qr(self, local_tokens: Optional[list[str]] = None) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{DEFAULT_BASE_URL}/ilink/bot/get_bot_qrcode",
                params={"bot_type": "3"},
                headers={"Content-Type": "application/json", **_common_headers()},
                json={"local_token_list": list(local_tokens or [])[-10:]},
            )
            response.raise_for_status()
            return response.json()

    async def poll_qr(
        self,
        qrcode: str,
        *,
        verify_code: str = "",
        base_url: str = DEFAULT_BASE_URL,
    ) -> dict[str, Any]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=40) as client:
                response = await client.get(
                    f"{base_url.rstrip('/')}/ilink/bot/get_qrcode_status",
                    params={
                        "qrcode": qrcode,
                        **({"verify_code": verify_code} if verify_code else {}),
                    },
                    headers=_common_headers(),
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            return {"status": "wait"}

    async def get_updates(self, cursor: str) -> dict[str, Any]:
        return await self.post(
            "ilink/bot/getupdates", {"get_updates_buf": cursor}, timeout=40
        )

    async def send_items(self, to: str, context_token: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        return await self.post(
            "ilink/bot/sendmessage",
            {
                "msg": {
                    "from_user_id": "",
                    "to_user_id": to,
                    "client_id": uuid.uuid4().hex[:16],
                    "message_type": 2,
                    "message_state": 2,
                    "item_list": items,
                    "context_token": context_token,
                }
            },
        )

    async def upload(self, data: bytes, to: str, media_type: int) -> dict[str, Any]:
        import httpx

        key = os.urandom(16)
        key_hex = key.hex()
        encrypted = _aes_encrypt(data, key)
        file_key = uuid.uuid4().hex
        meta = await self.post(
            "ilink/bot/getuploadurl",
            {
                "filekey": file_key,
                "media_type": media_type,
                "to_user_id": to,
                "rawsize": len(data),
                "rawfilemd5": hashlib.md5(data).hexdigest(),
                "filesize": len(encrypted),
                "aeskey": key_hex,
                "no_need_thumb": True,
            },
        )
        upload_url = str(meta.get("upload_full_url") or "")
        if not upload_url:
            param = str(meta.get("upload_param") or "")
            if not param:
                raise RuntimeError("iLink 未返回 CDN 上传地址")
            upload_url = (
                f"{self.cdn_base_url}/upload?encrypted_query_param={quote(param)}"
                f"&filekey={quote(file_key)}"
            )
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=120, verify=_cdn_ssl_context()) as client:
                    response = await client.post(
                        upload_url,
                        content=encrypted,
                        headers={"Content-Type": "application/octet-stream"},
                    )
                    response.raise_for_status()
                break
            except (httpx.TransportError, httpx.HTTPStatusError):
                if attempt >= 2:
                    raise
                await asyncio.sleep(0.5 * (2**attempt))
        download_param = response.headers.get("x-encrypted-param", "")
        if not download_param:
            raise RuntimeError("iLink CDN 未返回下载参数")
        return {
            "encrypt_query_param": download_param,
            "aes_key": base64.b64encode(key_hex.encode("ascii")).decode("ascii"),
            "ciphertext_size": len(encrypted),
        }

    async def download(self, encrypted_param: str, aes_key: str) -> bytes:
        import httpx

        async with httpx.AsyncClient(timeout=60, verify=_cdn_ssl_context()) as client:
            response = await client.get(
                f"{self.cdn_base_url}/download",
                params={"encrypted_query_param": encrypted_param},
            )
            response.raise_for_status()
        return _aes_decrypt(response.content, _decode_aes_key(aes_key))


class WeixinIlinkAdapter(BasePlatformAdapter):
    platform = "weixin"

    def __init__(
        self,
        token: str = "",
        *,
        bot_id: str = "",
        account_id: str = "default",
        base_url: str = DEFAULT_BASE_URL,
        cdn_base_url: str = DEFAULT_CDN_BASE_URL,
        context_tokens: Optional[dict[str, str]] = None,
        get_updates_buf: str = "",
        media_manager: Optional[ChannelMediaManager] = None,
        secrets=None,
    ) -> None:
        super().__init__()
        self.account_id = account_id or "default"
        self.bot_id = bot_id
        self.api = WeixinIlinkApi(base_url=base_url, cdn_base_url=cdn_base_url, token=token)
        self._media = media_manager
        self._secrets = secrets
        self._context_tokens = dict(context_tokens or {})
        self._cursor = get_updates_buf
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._poll_task: Optional[asyncio.Task] = None
        self._qr_task: Optional[asyncio.Task] = None
        self._closing = False
        self._qr_url = ""
        self._qrcode = ""
        self._qr_status = ""
        self._qr_poll_base_url = DEFAULT_BASE_URL
        self._pending_verify_code = ""
        self._sent_keys: set[str] = set()
        self._last_poll_at: Optional[float] = None
        self._last_poll_message_count = 0
        self._last_inbound_at: Optional[float] = None
        self.capabilities = ChannelCapabilities(
            direct_messages=True,
            group_chat=False,
            group_mentions=False,
            proactive_messages=False,
            # iLink has no WeCom-style single-message update API. ChemClaw provides ordered,
            # throttled incremental messages and reports the concrete mode in status details.
            streaming=True,
            receive_images=True,
            send_images=True,
            receive_files=True,
            send_files=True,
            max_inbound_bytes=50 * 1024 * 1024,
            max_outbound_bytes=50 * 1024 * 1024,
        )

    def channel_status(self):
        status = super().channel_status()
        # QR pending must stay auth_required even if a caller briefly flipped state.
        if not self.api.token:
            status.state = "auth_required"
            status.authenticated = False
        status.details = {
            **({"qr_url": self._qr_url} if self._qr_url else {}),
            **({"qr_status": self._qr_status} if self._qr_status else {}),
            "needs_verify_code": self._qr_status == "need_verifycode",
            "last_poll_at": self._last_poll_at,
            "last_poll_message_count": self._last_poll_message_count,
            "last_inbound_at": self._last_inbound_at,
            "streaming_mode": "incremental_messages",
        }
        if self._last_error:
            status.last_error = self._last_error
        return status

    def _persist(self) -> None:
        if self._secrets is None:
            return
        account_key = f"weixin:account:{self.account_id}"
        profile = self._secrets.get(account_key) or {}
        profile.update(
            {
                "type": "token",
                "enabled": True,
                "token": self.api.token,
                "bot_id": self.bot_id,
                "account_id": self.account_id,
                "base_url": self.api.base_url,
                "cdn_base_url": self.api.cdn_base_url,
                "context_tokens": dict(self._context_tokens),
                "get_updates_buf": self._cursor,
            }
        )
        self._secrets.put(account_key, profile)
        pointer = self._secrets.get("weixin:default") or {}
        pointer.setdefault("type", "token")
        pointer.setdefault("enabled", True)
        pointer.setdefault("default_account", self.account_id)
        self._secrets.put("weixin:default", pointer)

    async def connect(self) -> bool:
        try:
            from Crypto.Cipher import AES  # noqa: F401
        except ImportError:
            self._channel_state = "degraded"
            self._last_error = "未安装 pycryptodome，无法使用微信文件加解密"
            return False
        self._loop = asyncio.get_running_loop()
        self._closing = False
        _LIVE[self.account_id] = self
        if self.bot_id:
            _LIVE[self.bot_id] = self
        if self.api.token:
            self._channel_state = "connected"
            self._channel_authenticated = True
            self._poll_task = asyncio.create_task(self._poll_loop())
            return True
        self._channel_state = "auth_required"
        self._channel_authenticated = False
        try:
            await self._refresh_qr()
        except Exception as exc:
            self._last_error = f"获取微信登录二维码失败（{type(exc).__name__}）"
            return False
        self._qr_task = asyncio.create_task(self._qr_login_loop())
        return True

    async def _refresh_qr(self) -> str:
        local_tokens: list[str] = []
        if self._secrets is not None:
            try:
                from . import accounts

                local_tokens = [
                    str(profile.get("token") or "").strip()
                    for _account_id, profile in accounts.list_accounts(
                        self._secrets, "weixin"
                    )
                    if str(profile.get("token") or "").strip()
                ][-10:]
            except Exception:
                local_tokens = []
        data = await self.api.fetch_qr(local_tokens)
        self._qrcode = str(data.get("qrcode") or "")
        self._qr_url = str(data.get("qrcode_img_content") or "")
        self._qr_status = "wait"
        self._qr_poll_base_url = DEFAULT_BASE_URL
        self._pending_verify_code = ""
        # ``qrcode_img_content`` is a WeChat scan URL, not a raster image. The GUI
        # renders it locally as a QR code (see WeixinQrImage).
        if not self._qrcode:
            raise RuntimeError("iLink 未返回二维码")
        return self._qr_url

    async def _qr_login_loop(self) -> None:
        refreshes = 0
        while not self._closing:
            try:
                data = await self.api.poll_qr(
                    self._qrcode,
                    verify_code=self._pending_verify_code,
                    base_url=self._qr_poll_base_url,
                )
                status = str(data.get("status") or "wait")
                self._qr_status = status
                if status in {"wait", "scaned"}:
                    if status == "scaned" and self._pending_verify_code:
                        self._pending_verify_code = ""
                    await asyncio.sleep(1)
                    continue
                if status == "need_verifycode":
                    self._last_error = "手机微信要求输入配对码，请在连接页填写手机上显示的数字"
                    await asyncio.sleep(1)
                    continue
                if status == "verify_code_blocked":
                    self._pending_verify_code = ""
                    self._last_error = "配对码多次错误，已刷新二维码，请重新扫描"
                    refreshes += 1
                    if refreshes > 3:
                        return
                    await self._refresh_qr()
                    continue
                if status == "scaned_but_redirect":
                    host = str(data.get("redirect_host") or "").strip().lower()
                    if host and "/" not in host and (
                        host == "weixin.qq.com" or host.endswith(".weixin.qq.com")
                    ):
                        self._qr_poll_base_url = f"https://{host}"
                    else:
                        self._last_error = "微信扫码跳转地址无效，请刷新二维码重试"
                    await asyncio.sleep(1)
                    continue
                if status == "binded_redirect":
                    self._last_error = "此微信已绑定过当前客户端；请使用已保存账号或先解除旧绑定"
                    return
                if status == "expired":
                    refreshes += 1
                    if refreshes > 3:
                        self._last_error = "微信二维码多次过期，请重新连接"
                        return
                    await self._refresh_qr()
                    continue
                if status == "confirmed":
                    token = str(data.get("bot_token") or "")
                    bot_id = str(data.get("ilink_bot_id") or "")
                    if not token or not bot_id:
                        raise RuntimeError("扫码已确认，但 iLink 未返回凭据")
                    self.api.token = token
                    self.api.base_url = str(data.get("baseurl") or self.api.base_url).rstrip("/")
                    self.bot_id = bot_id
                    _LIVE[bot_id] = self
                    self._qr_url = ""
                    self._qr_status = "confirmed"
                    self._channel_state = "connected"
                    self._channel_authenticated = True
                    self._last_error = ""
                    owner_user_id = str(data.get("ilink_user_id") or "").strip()
                    if owner_user_id and self._secrets is not None:
                        profile = self._secrets.get(
                            f"weixin:account:{self.account_id}"
                        ) or {}
                        allowed = {
                            str(value).strip()
                            for value in profile.get("allowed_users") or []
                            if str(value).strip()
                        }
                        allowed.add(owner_user_id)
                        profile["allowed_users"] = sorted(allowed)
                        self._secrets.put(
                            f"weixin:account:{self.account_id}", profile
                        )
                    self._persist()
                    self._poll_task = asyncio.create_task(self._poll_loop())
                    return
                self._last_error = "微信返回了无法识别的扫码状态，请刷新二维码重试"
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                return
            except Exception as exc:
                self._last_error = f"微信扫码登录失败（{type(exc).__name__}）"
                await asyncio.sleep(2)

    def submit_verify_code(self, value: str) -> bool:
        """Supply the short code shown by Weixin without persisting it."""
        code = str(value or "").strip()
        if not code.isdigit() or not 4 <= len(code) <= 8:
            return False
        self._pending_verify_code = code
        self._last_error = ""
        return True

    async def _poll_loop(self) -> None:
        failures = 0
        while not self._closing and self.api.token:
            try:
                data = await self.api.get_updates(self._cursor)
                self._last_poll_at = time.time()
                messages = data.get("msgs") if isinstance(data.get("msgs"), list) else []
                self._last_poll_message_count = len(messages)
                ret = int(data.get("ret") or data.get("errcode") or 0)
                if ret == -14:
                    self.api.token = ""
                    self._channel_authenticated = False
                    self._channel_state = "auth_required"
                    self._last_error = "微信登录凭据已过期，请重新扫码"
                    self._persist()
                    await self._refresh_qr()
                    self._qr_task = asyncio.create_task(self._qr_login_loop())
                    return
                if ret:
                    raise RuntimeError(str(data.get("errmsg") or f"iLink error {ret}"))
                failures = 0
                next_cursor = str(data.get("get_updates_buf") or self._cursor)
                if next_cursor != self._cursor:
                    self._cursor = next_cursor
                    self._persist()
                for message in messages:
                    if isinstance(message, dict) and int(message.get("message_type") or 0) == 1:
                        await self._on_message(message)
            except asyncio.CancelledError:
                return
            except Exception as exc:
                failures += 1
                self._last_error = f"微信消息轮询失败（{type(exc).__name__}）"
                self._reconnect_count += 1
                await asyncio.sleep(min(60, 2 ** min(failures, 5)))

    async def _on_message(self, raw: dict[str, Any]) -> None:
        inbound = weixin_update_to_inbound(raw, account_id=self.account_id)
        if inbound is None:
            return
        self._last_inbound_at = time.time()
        if inbound.context_token:
            self._context_tokens[inbound.user_id] = inbound.context_token
            self._persist()
        event = inbound_to_message_event(inbound, raw=raw)
        if self._media is not None and inbound.attachments:
            async def load_attachments() -> list[str]:
                return await self._media.materialize(inbound, self._download_attachment)

            event.attachment_loader = load_attachments
        await self.enqueue_message(event)

    async def _download_attachment(self, attachment: ChannelAttachment):
        data = await self.api.download(
            attachment.remote_ref, str(attachment.encryption.get("aes_key") or "")
        )
        return attachment.name, data, attachment.mime_type

    async def disconnect(self) -> None:
        self._closing = True
        tasks = [
            task
            for task in (self._poll_task, self._qr_task)
            if task is not None and task is not asyncio.current_task()
        ]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._poll_task = None
        self._qr_task = None
        _LIVE.pop(self.account_id, None)
        if self.bot_id:
            _LIVE.pop(self.bot_id, None)
        self._channel_state = "disconnected"
        self._channel_authenticated = False

    def _context_for(self, user_id: str, explicit: str = "") -> str:
        return explicit or self._context_tokens.get(user_id, "")

    async def send(
        self,
        chat_id: str | OutboundEnvelope,
        text: Optional[str] = None,
        *,
        thread_id: Optional[str] = None,
    ) -> SendResult:
        envelope = chat_id if isinstance(chat_id, OutboundEnvelope) else None
        context_token = ""
        if envelope is not None:
            if envelope.idempotency_key and envelope.idempotency_key in self._sent_keys:
                return SendResult(True, message_id=envelope.idempotency_key)
            chat_id, text = envelope.conversation_id, envelope.text
            context_token = envelope.context_token
            if envelope.attachments:
                if text:
                    result = await self.send(str(chat_id), text)
                    if not result.ok:
                        return result
                last = SendResult(True)
                for attachment in envelope.attachments:
                    path = Path(attachment.local_path)
                    if not path.is_file() or path.is_symlink():
                        return SendResult(False, error="待发送附件不存在或不是普通文件")
                    last = await self.send_file(
                        str(chat_id), attachment.name or path.name, path.read_bytes()
                    )
                    if not last.ok:
                        return last
                if envelope.idempotency_key:
                    self._sent_keys.add(envelope.idempotency_key)
                return last
        _ = thread_id
        token = self._context_for(str(chat_id), context_token)
        if not token:
            return SendResult(False, error="该微信会话没有有效 context_token，请先让对方发一条消息")
        try:
            message_id = ""
            body = text or ""
            for start in range(0, len(body) or 1, 6000):
                chunk = body[start : start + 6000]
                await self.throttle_outbound()
                data = await self.api.send_items(
                    str(chat_id), token, [{"type": 1, "text_item": {"text": chunk}}]
                )
                ret = int(data.get("ret") or data.get("errcode") or 0)
                if ret:
                    if ret == -14:
                        self._context_tokens.pop(str(chat_id), None)
                        self._persist()
                    return SendResult(False, error=str(data.get("errmsg") or f"iLink error {ret}"))
                message_id = str(data.get("message_id") or message_id)
            self._last_sent_at = time.time()
            if envelope is not None and envelope.idempotency_key:
                self._sent_keys.add(envelope.idempotency_key)
            return SendResult(True, message_id=message_id or None)
        except Exception as exc:
            self._last_error = f"微信消息发送失败（{type(exc).__name__}）"
            return SendResult(False, error=self._last_error)

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
        context_token = self._context_for(chat_id)
        if not context_token:
            return SendResult(False, error="该微信会话没有有效 context_token，请先让对方发一条消息")
        if len(data) > (self.capabilities.max_outbound_bytes or len(data)):
            return SendResult(False, error="微信附件超过 50 MB 限制")
        try:
            is_image = Path(filename).suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
            await self.throttle_outbound()
            upload = await self.api.upload(data, chat_id, 1 if is_image else 3)
            items: list[dict[str, Any]] = []
            if comment:
                items.append({"type": 1, "text_item": {"text": comment}})
            media = {
                "encrypt_query_param": upload["encrypt_query_param"],
                "aes_key": upload["aes_key"],
                "encrypt_type": 1,
            }
            if is_image:
                items.append(
                    {
                        "type": 2,
                        "image_item": {"media": media, "mid_size": upload["ciphertext_size"]},
                    }
                )
            else:
                items.append(
                    {
                        "type": 4,
                        "file_item": {"media": media, "file_name": filename, "len": str(len(data))},
                    }
                )
            await self.throttle_outbound()
            response = await self.api.send_items(chat_id, context_token, items)
            ret = int(response.get("ret") or response.get("errcode") or 0)
            if ret:
                return SendResult(False, error=str(response.get("errmsg") or f"iLink error {ret}"))
            self._last_sent_at = time.time()
            return SendResult(True, message_id=str(response.get("message_id") or "") or None)
        except Exception as exc:
            self._last_error = f"微信文件发送失败（{type(exc).__name__}）"
            return SendResult(False, error=self._last_error)

    def send_sync(self, chat_id: str, text: str, *, thread_id: Optional[str] = None) -> SendResult:
        if self._loop is None or not self._loop.is_running():
            return SendResult(False, error="微信事件循环未运行")
        future = asyncio.run_coroutine_threadsafe(self.send(chat_id, text, thread_id=thread_id), self._loop)
        try:
            return future.result(timeout=60)
        except Exception as exc:
            return SendResult(False, error=f"微信消息发送失败（{type(exc).__name__}）")

    def send_file_sync(self, chat_id: str, filename: str, data: bytes, *, title=None, comment=None) -> SendResult:
        if self._loop is None or not self._loop.is_running():
            return SendResult(False, error="微信事件循环未运行")
        future = asyncio.run_coroutine_threadsafe(
            self.send_file(chat_id, filename, data, title=title, comment=comment), self._loop
        )
        try:
            return future.result(timeout=180)
        except Exception as exc:
            return SendResult(False, error=f"微信文件发送失败（{type(exc).__name__}）")
