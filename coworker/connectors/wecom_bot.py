"""WeCom AI Bot inbound adapter — WebSocket long connection (D-188).

Uses optional `wecom-aibot-sdk` (lazy import). Outbound for `send_message` goes through
the live adapter registry (WS active push), not HTTP bot tokens.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional

from ..channels.mappings import wecom_frame_to_message_event
from .base import BasePlatformAdapter, SendResult

logger = logging.getLogger("coworker.connectors.wecom")

# Live adapters keyed by bot_id — sync send_message tool looks these up.
_LIVE: dict[str, "WecomBotAdapter"] = {}

# Attachment safety (Phase 6)
_MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
_ALLOWED_IMAGE_EXT = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})
_ALLOWED_FILE_EXT = frozenset(
    {".pdf", ".txt", ".csv", ".xlsx", ".xls", ".doc", ".docx", ".ppt", ".pptx", ".zip"}
) | _ALLOWED_IMAGE_EXT

_PROGRESS_ACK_ZH = "ChemClaw 正在处理…"


def live_adapter(bot_id: str = "") -> Optional["WecomBotAdapter"]:
    if bot_id and bot_id in _LIVE:
        return _LIVE[bot_id]
    if len(_LIVE) == 1:
        return next(iter(_LIVE.values()))
    return None


def _safe_filename(name: str) -> str:
    base = Path(name or "file").name
    cleaned = "".join(c for c in base if c.isalnum() or c in "._- ") or "file"
    return cleaned[:180]


class WecomBotAdapter(BasePlatformAdapter):
    platform = "wecom"

    def __init__(self, bot_id: str, secret: str, *, attachment_dir: Optional[Path] = None) -> None:
        super().__init__()
        self.bot_id = bot_id
        self.secret = secret
        self._client: Any = None
        self._connect_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._attachment_dir = attachment_dir
        self._seen_ids: set[str] = set()
        self._seen_order: list[str] = []
        self._ack_enabled = os.environ.get("CHEMCLAW_WECOM_ACK", "1").lower() not in (
            "0",
            "false",
            "no",
        )

    async def connect(self) -> bool:
        try:
            from wecom_aibot_sdk import WSClient
        except ImportError:
            logger.error(
                "wecom-aibot-sdk not installed — install wecom-aibot-sdk>=1.0.8 "
                "into the ChemClaw runtime (pip install -e '.[messaging]') and restart"
            )
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
        client.on("error", lambda err: logger.warning("wecom ws error: %s", err))
        self._client = client
        _LIVE[self.bot_id] = self
        try:
            await client.connect()
        except Exception:
            logger.exception("wecom connect failed")
            _LIVE.pop(self.bot_id, None)
            self._client = None
            return False
        return True

    async def disconnect(self) -> None:
        _LIVE.pop(self.bot_id, None)
        client = self._client
        self._client = None
        if client is None:
            return
        try:
            await client.disconnect()
        except Exception:
            logger.debug("wecom disconnect error", exc_info=True)

    async def send(
        self, chat_id: str, text: str, *, thread_id: Optional[str] = None
    ) -> SendResult:
        _ = thread_id
        client = self._client
        if client is None:
            return SendResult(False, error="企业微信未连接")
        try:
            await client.send_message(
                chat_id,
                {"msgtype": "markdown", "markdown": {"content": text}},
            )
            return SendResult(True)
        except Exception as exc:
            logger.exception("wecom send failed")
            return SendResult(False, error=str(exc))

    async def send_progress(self, chat_id: str, text: str = _PROGRESS_ACK_ZH) -> None:
        try:
            await self.send(chat_id, text)
        except Exception:
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

    async def _on_frame(self, frame: Any) -> None:
        if not isinstance(frame, dict):
            return
        event = wecom_frame_to_message_event(frame)
        if event is None:
            return
        mid = event.message_id or ""
        if mid:
            if mid in self._seen_ids:
                return
            self._seen_ids.add(mid)
            self._seen_order.append(mid)
            while len(self._seen_order) > 500:
                old = self._seen_order.pop(0)
                self._seen_ids.discard(old)

        if self._ack_enabled and event.source.chat_id:
            asyncio.create_task(self.send_progress(event.source.chat_id))

        if self._attachment_dir and event.raw:
            await self._maybe_save_attachments(event)

        await self.handle_message(event)

    async def _maybe_save_attachments(self, event) -> None:
        client = self._client
        raw = event.raw if isinstance(event.raw, dict) else {}
        body = raw.get("body") if isinstance(raw.get("body"), dict) else {}
        msgtype = str(body.get("msgtype") or "")
        items: list[tuple[str, str, str]] = []  # kind, url, aeskey
        if msgtype == "image":
            img = body.get("image") if isinstance(body.get("image"), dict) else {}
            items.append(
                (
                    "image",
                    str(img.get("url") or ""),
                    str(img.get("aeskey") or img.get("aes_key") or ""),
                )
            )
        elif msgtype == "file":
            f = body.get("file") if isinstance(body.get("file"), dict) else {}
            items.append(
                (
                    "file",
                    str(f.get("url") or ""),
                    str(f.get("aeskey") or f.get("aes_key") or ""),
                )
            )
        if not items or client is None or not hasattr(client, "download_file"):
            return
        dest_root = Path(self._attachment_dir)
        try:
            dest_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            return
        for kind, url, aes in items:
            if not url:
                continue
            try:
                result = await client.download_file(url, aes or None)
            except Exception:
                logger.debug("wecom attachment download failed", exc_info=True)
                continue
            buf = result.get("buffer") if isinstance(result, dict) else None
            if not isinstance(buf, (bytes, bytearray)):
                continue
            if len(buf) > _MAX_ATTACHMENT_BYTES:
                logger.info("wecom attachment rejected: too large (%s bytes)", len(buf))
                continue
            name = _safe_filename(
                str((result.get("filename") if isinstance(result, dict) else None) or kind)
            )
            ext = Path(name).suffix.lower()
            allowed = _ALLOWED_IMAGE_EXT if kind == "image" else _ALLOWED_FILE_EXT
            if ext and ext not in allowed:
                logger.info("wecom attachment rejected: extension %s", ext)
                continue
            path = dest_root / name
            try:
                path.write_bytes(bytes(buf))
            except OSError:
                logger.debug("wecom attachment write failed", exc_info=True)
