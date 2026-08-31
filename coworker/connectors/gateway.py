"""Gateway — owns the messaging adapters and routes inbound messages.

Lives inside the always-on `openworker-server` (started/stopped in its lifespan). On inbound:
enforce the per-platform allowlist, then hand the message to the registered handler (the
super-agent runner, wired in the next increment). Outbound replies go through the
`send_message` tool, not the gateway — so the gateway stays a thin inbound router here.
"""

from __future__ import annotations

import logging
from asyncio import to_thread
from collections import OrderedDict
from typing import Callable, Optional
from urllib.parse import urlparse

from ..channels.models import OutboundEnvelope
from ..secrets import SecretStore
from .base import (
    BasePlatformAdapter,
    InteractionEvent,
    MessageEvent,
    MessageHandler,
    SendResult,
    SessionSource,
    parse_target,
)
from .config import ConnectorSettings, is_authorized, load_settings

logger = logging.getLogger("coworker.connectors")

_RECENT_CAP = 20  # most-recent distinct senders kept for chat-ID auto-capture


class Gateway:
    def __init__(
        self,
        *,
        secrets: Optional[SecretStore] = None,
        settings: Optional[dict[str, ConnectorSettings]] = None,
        handler: Optional[MessageHandler] = None,
        reply_resolver: Optional[Callable[[MessageEvent], bool]] = None,
        interaction_handler: Optional[Callable] = None,
        on_unauthorized: Optional[Callable] = None,
    ) -> None:
        self.secrets = secrets or SecretStore()
        self.settings = (
            settings if settings is not None else load_settings(self.secrets)
        )
        self._handler = handler
        # Tried before the handler: if an inbound message is an Inbox reply (carries an
        # [ow:<id>] token), it resolves the item and is consumed — not routed as a new turn.
        self._reply_resolver = reply_resolver
        # A button click on an interactive prompt (resolves an Inbox item by id).
        self._interaction_handler = interaction_handler
        # Called (awaited) with the MessageEvent when the allow-list drops it, so the message
        # can be PARKED for one-step allow-and-deliver instead of vanishing.
        self._on_unauthorized = on_unauthorized
        self._adapters: dict[str, BasePlatformAdapter] = {}
        self._live: set[str] = set()
        # In-memory recent senders for chat-ID auto-capture (identity only, never persisted).
        self._recent: "OrderedDict[tuple[str, str, str], dict]" = OrderedDict()

    def set_handler(self, handler: MessageHandler) -> None:
        self._handler = handler

    def set_reply_resolver(
        self, resolver: Optional[Callable[[MessageEvent], bool]]
    ) -> None:
        self._reply_resolver = resolver

    def register(self, adapter: BasePlatformAdapter) -> None:
        adapter.set_message_handler(self._on_inbound)
        if self._interaction_handler is not None:
            adapter.set_interaction_handler(self._on_interaction)
        account_id = str(getattr(adapter, "account_id", "") or "default")
        key = adapter.platform if account_id == "default" else f"{adapter.platform}:{account_id}"
        self._adapters[key] = adapter

    def _platform_adapters(self, platform: str) -> list[tuple[str, BasePlatformAdapter]]:
        prefix = f"{platform}:"
        return [
            (key, adapter)
            for key, adapter in self._adapters.items()
            if key == platform or key.startswith(prefix)
        ]

    def _adapter_for_target(
        self, platform: str, chat_id: str
    ) -> tuple[Optional[BasePlatformAdapter], str]:
        """Select an account-qualified adapter and return its platform-native chat id."""
        if "/" in chat_id:
            account_id, bare_chat = chat_id.split("/", 1)
            adapter = self._adapters.get(f"{platform}:{account_id}")
            if adapter is not None and bare_chat:
                return adapter, bare_chat
        adapter = self._adapters.get(platform)
        if adapter is not None:
            return adapter, chat_id
        candidates = self._platform_adapters(platform)
        if len(candidates) == 1:
            only = candidates[0][1]
            account_id = str(getattr(only, "account_id", "") or "default")
            prefix = f"{account_id}/"
            return only, chat_id[len(prefix) :] if chat_id.startswith(prefix) else chat_id
        return None, chat_id

    async def _on_interaction(self, event: InteractionEvent) -> None:
        source = SessionSource(
            platform=event.platform,
            chat_id=event.chat_id,
            user_id=event.user_id,
            user_name=event.user_name,
            chat_type="channel",
            team_id=event.team_id,
        )
        settings = self.settings.get(event.platform)
        if settings is None or not is_authorized(settings, source):
            logger.info("rejecting unauthorized interaction from %s", source.label())
            await self.reject_interaction(event)
            return
        if self._interaction_handler is not None:
            await self._interaction_handler(event)

    async def reject_interaction(
        self,
        event: InteractionEvent,
        text: str = "Only a designated approval owner can respond to this request.",
    ) -> None:
        """Best-effort private feedback for a rejected Slack button click."""
        response_url = str(event.response_url or "")
        parsed = urlparse(response_url)
        if (
            event.platform != "slack"
            or parsed.scheme != "https"
            or parsed.hostname not in {"hooks.slack.com", "hooks.slack-gov.com"}
        ):
            return

        def _post() -> None:
            import httpx

            try:
                httpx.post(
                    response_url,
                    json={"response_type": "ephemeral", "text": text},
                    timeout=10,
                )
            except Exception:
                logger.debug("Slack ephemeral interaction response failed", exc_info=True)

        await to_thread(_post)

    async def _on_inbound(self, event: MessageEvent) -> None:
        self._record_recent(event)  # capture identity even from unauthorized senders
        settings = self.settings.get(event.source.platform)
        if settings is None or not is_authorized(settings, event.source):
            logger.info("parking unauthorized inbound from %s", event.source.label())
            if self._on_unauthorized is not None:
                try:
                    await self._on_unauthorized(event)
                except Exception:
                    logger.exception("parking unauthorized inbound failed")
            return
        # Frame-bound acknowledgements (currently WeCom streaming replies) may only
        # run after the sender passes the allow-list.  Keeping this in Gateway avoids
        # leaking bot activity to parked/unauthorized conversations.
        account_chat = (
            f"{event.source.account_id}/{event.source.chat_id}"
            if getattr(event.source, "account_id", "default") != "default"
            else event.source.chat_id
        )
        adapter, _bare_chat = self._adapter_for_target(
            event.source.platform, account_chat
        )
        acknowledge = getattr(adapter, "acknowledge", None)
        if callable(acknowledge):
            try:
                await acknowledge(event)
            except Exception:
                logger.debug("channel acknowledgement failed", exc_info=True)
        # Authorization must precede every network download and local write.  Unauthorized
        # events may be parked as metadata, but their remote attachments never land on disk.
        try:
            await event.prepare_attachments()
        except Exception as exc:
            logger.warning(
                "authorized %s attachment preparation failed: %s",
                event.source.platform,
                type(exc).__name__,
            )
            event.text = "\n".join(
                part
                for part in (event.text, "[附件处理失败] 平台附件下载或校验失败")
                if part
            )
        # An inbound reply that resolves an Inbox item (approval/answer) is consumed here, not
        # routed to the super-agent as a new turn. The suspended agent awaiting that item is
        # released automatically (InboxStore.resolve fires its waiter).
        if self._reply_resolver is not None:
            try:
                if self._reply_resolver(event):
                    return
            except Exception:
                logger.exception("inbox reply resolver failed")
        if self._handler is not None:
            await self._handler(event)

    def _record_recent(self, event: MessageEvent) -> None:
        s = event.source
        if not s.user_id:
            return
        # Ids are workspace-scoped, so the same U… in two teams is two senders.
        key = (s.platform, s.team_id or "", s.user_id)
        self._recent.pop(key, None)  # move to most-recent
        self._recent[key] = {
            "platform": s.platform,
            "user_id": s.user_id,
            "user_name": s.user_name,
            "chat_id": s.chat_id,
            "chat_type": s.chat_type,
            "target": s.target,
            "team_id": s.team_id,  # workspace (managed relay); None for socket mode
        }
        while len(self._recent) > _RECENT_CAP:
            self._recent.popitem(last=False)

    def recent_senders(self, platform: Optional[str] = None) -> list[dict]:
        """Most-recent-first list of who has messaged (for the allowlist UI)."""
        items = list(self._recent.values())[::-1]
        return [e for e in items if platform is None or e["platform"] == platform]

    async def start(self) -> list[str]:
        """Connect every enabled+registered adapter. Returns the platforms that came up."""
        self._live.clear()
        live: list[str] = []
        for key, adapter in self._adapters.items():
            platform = adapter.platform
            settings = self.settings.get(platform)
            if settings is None or not settings.enabled:
                continue
            try:
                starter = getattr(adapter, "start", None)
                connected = await starter() if callable(starter) else await adapter.connect()
                if connected:
                    live.append(key)
                    self._live.add(key)
            except Exception:  # bad token / network — skip, don't break the server
                # SDK exceptions can echo credentials (Telegram InvalidToken does).
                logger.error("failed to connect %s adapter", platform)
        return live

    async def stop(self) -> None:
        for adapter in self._adapters.values():
            try:
                stopper = getattr(adapter, "stop", None)
                if callable(stopper):
                    await stopper()
                else:
                    await adapter.disconnect()
            except Exception:
                logger.exception("error disconnecting %s adapter", adapter.platform)
        self._live.clear()

    async def deliver(self, target: str, text: str) -> SendResult:
        """Send via a live adapter (used where the persistent connection is preferred)."""
        platform, chat_id, thread_id = parse_target(target)
        adapter, chat_id = self._adapter_for_target(platform, chat_id)
        if adapter is None:
            return SendResult(False, error=f"no adapter for {platform}")
        return await adapter.send(chat_id, text, thread_id=thread_id)

    async def deliver_envelope(
        self, target: str, envelope: OutboundEnvelope
    ) -> SendResult:
        """Route a platform-neutral envelope to the account named by ``target``."""
        platform, chat_id, thread_id = parse_target(target)
        adapter, bare_chat_id = self._adapter_for_target(platform, chat_id)
        if adapter is None:
            return SendResult(False, error=f"no adapter for {platform}")
        envelope.platform = platform
        envelope.account_id = str(getattr(adapter, "account_id", "") or "default")
        envelope.conversation_id = bare_chat_id
        envelope.reply_to = envelope.reply_to or thread_id
        return await adapter.send(envelope)

    async def deliver_interactive(self, target: str, text: str, buttons) -> SendResult:
        """Send a prompt with choice buttons (adapters without interactive support show text only)."""
        platform, chat_id, thread_id = parse_target(target)
        adapter, chat_id = self._adapter_for_target(platform, chat_id)
        if adapter is None:
            return SendResult(False, error=f"no adapter for {platform}")
        return await adapter.send_interactive(
            chat_id, text, buttons, thread_id=thread_id
        )

    async def update_message(
        self, platform: str, chat_id: str, message_id: str, text: str
    ) -> None:
        """Replace a resolved prompt's buttons with a plain-text outcome, if the adapter supports it."""
        adapter, chat_id = self._adapter_for_target(platform, chat_id)
        fn = getattr(adapter, "update_message", None)
        if fn is not None:
            await fn(chat_id, message_id, text)

    def status(self) -> list[dict]:
        out = []
        for platform, settings in self.settings.items():
            adapters = self._platform_adapters(platform)
            row = {
                    "platform": platform,
                    "enabled": settings.enabled,
                    "connected": any(key in self._live for key, _ in adapters),
                    "allow_all": settings.allow_all,
                    "allowed_users": len(settings.allowed_users),
                }
            snapshots = []
            for key, adapter in adapters:
                snapshot = getattr(adapter, "channel_status", None)
                if not callable(snapshot):
                    continue
                try:
                    detail = snapshot().to_dict()
                    detail["live"] = key in self._live
                    snapshots.append(detail)
                except Exception:
                    pass
            if snapshots:
                connected = [s for s in snapshots if s.get("state") == "connected"]
                auth_needed = [s for s in snapshots if s.get("state") == "auth_required"]
                degraded = [s for s in snapshots if s.get("state") == "degraded"]
                primary = dict(snapshots[0])
                primary_details = (
                    primary.get("details")
                    if isinstance(primary.get("details"), dict)
                    else {}
                )
                # Always expose per-account snapshots so AccountsDetail can render QR login
                # for the common single-account Weixin case (not only when N>1).
                details = {"accounts": snapshots, **primary_details}
                row.update(
                    {
                        "connected": bool(connected),
                        "state": (
                            "connected"
                            if connected
                            else "auth_required"
                            if auth_needed
                            else "degraded"
                            if degraded
                            else "disconnected"
                        ),
                        "authenticated": bool(connected),
                        "account_id": primary.get("account_id") or "default",
                        "last_received_at": max(
                            (s.get("last_received_at") or 0 for s in snapshots),
                            default=0,
                        )
                        or None,
                        "last_sent_at": max(
                            (s.get("last_sent_at") or 0 for s in snapshots),
                            default=0,
                        )
                        or None,
                        "queue_length": sum(
                            int(s.get("queue_length") or 0) for s in snapshots
                        ),
                        "reconnect_count": sum(
                            int(s.get("reconnect_count") or 0) for s in snapshots
                        ),
                        "last_error": next(
                            (
                                str(s.get("last_error"))
                                for s in snapshots
                                if s.get("last_error")
                            ),
                            "",
                        ),
                        "capabilities": primary.get("capabilities") or {},
                        "details": details,
                    }
                )
            out.append(row)
        return out
