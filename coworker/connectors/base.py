"""Messaging connector core — the platform-agnostic adapter contract + value types.

Patterns borrowed from Hermes' gateway (read-only ref). An adapter connects to a platform
(Slack/Telegram), receives inbound messages and dispatches them via `handle_message`, and
can `send` outbound. Inbound identity is carried by `SessionSource`; a `target` token
(`platform:chat_id[:thread]`) is the opaque handle the agent passes back to reply.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import asdict, dataclass, field
from enum import Enum
from time import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional

if TYPE_CHECKING:
    from ..channels.models import ChannelAttachment, OutboundEnvelope


class MessageType(str, Enum):
    TEXT = "text"
    COMMAND = "command"
    MEDIA = "media"


# -- target tokens -------------------------------------------------------------
def format_target(platform: str, chat_id: str, thread_id: Optional[str] = None) -> str:
    base = f"{platform}:{chat_id}"
    return f"{base}:{thread_id}" if thread_id else base


def parse_target(target: str) -> tuple[str, str, Optional[str]]:
    """`'platform:chat_id[:thread]'` -> (platform, chat_id, thread_id)."""
    parts = (target or "").split(":")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"invalid target {target!r} (expected 'platform:chat_id[:thread]')"
        )
    thread = ":".join(parts[2:]) if len(parts) > 2 else None
    return parts[0], parts[1], (thread or None)


# -- value types ---------------------------------------------------------------
@dataclass
class SessionSource:
    platform: str
    chat_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    chat_name: Optional[str] = None  # channel/DM display name (resolved, §2.3)
    chat_type: str = "dm"  # "dm" | "group" | "channel"
    thread_id: Optional[str] = None
    team_id: Optional[str] = None  # workspace id for managed-relay multi-workspace
    account_id: str = "default"

    @property
    def target(self) -> str:
        chat_id = self.chat_id
        if self.account_id and self.account_id != "default":
            chat_id = f"{self.account_id}/{chat_id}"
        return format_target(self.platform, chat_id, self.thread_id)

    def label(self) -> str:
        who = self.user_name or self.user_id or "?"
        where = {"dm": "DM", "group": "group", "channel": "channel"}.get(
            self.chat_type, self.chat_type
        )
        return f"{self.platform} {where} · {who}"


@dataclass
class MessageSource:
    """Structured sidecar for a connector inbound message (UI-REFRESH §3.1).

    Attached (as a plain dict via `to_dict`) to the persisted user message for DISPLAY only —
    the GUI renders a rich card from it. The model-facing `content` stays the framed text and
    this sidecar is stripped before the message reaches any provider. `text` is the RAW message
    (what the card shows), distinct from the framed `content`.
    """

    connector: str  # platform id, e.g. "slack"
    kind: str  # "channel" | "dm"
    channel_id: str  # e.g. "C0BD7KZ1AH5"
    channel_name: str  # resolved display name; falls back to channel_id
    sender_id: str
    sender_name: str  # resolved display name; falls back to sender_id
    ts: float  # epoch seconds
    text: str  # the RAW message (what the card shows)
    target: str = ""  # opaque reply target; omitted from legacy display sidecars when empty

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        if not out["target"]:
            out.pop("target")
        return out


@dataclass
class MessageEvent:
    text: str
    source: SessionSource
    message_id: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    reply_to_message_id: Optional[str] = None
    raw: Any = None
    # The bot itself was @-mentioned (UX-DECISIONS §31 mention router). Computed from the RAW
    # platform text at mapping time — mention tokens are rewritten for display afterwards.
    mentions_me: bool = False
    attachments: list["ChannelAttachment"] = field(default_factory=list)
    context_token: str = ""
    reply_context: dict[str, Any] = field(default_factory=dict)
    # Remote media is deliberately fetched only after Gateway authorization.  Keeping the
    # loader on the event lets platform callbacks remain transport-only and prevents an
    # untrusted sender from making ChemClaw persist bytes before allow-list checks run.
    attachment_loader: Optional[Callable[[], Awaitable[list[str]]]] = field(
        default=None, repr=False, compare=False
    )

    async def prepare_attachments(self) -> list[str]:
        """Materialize remote attachments once, after the caller has authorized the sender."""
        loader, self.attachment_loader = self.attachment_loader, None
        if loader is None:
            return []
        errors = await loader()
        if errors:
            suffix = "\n".join(f"[附件处理失败] {error}" for error in errors)
            self.text = "\n".join(part for part in (self.text, suffix) if part)
        return errors

    def tagged_text(self) -> str:
        """How the message enters the super-agent thread: source + reply handle + text.

        The local GUI owner ('gui') is answered with plain assistant text (no `send_message`);
        messaging platforms carry a reply handle the agent passes back to `send_message`.
        """
        if self.source.platform == "gui":
            return f"[Owner, in the app]: {self.text}"
        return f"[{self.source.label()} | reply→{self.source.target}]: {self.text}"


@dataclass
class SendResult:
    ok: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


MessageHandler = Callable[[MessageEvent], Awaitable[None]]


@dataclass
class InteractionEvent:
    """A button click on an interactive prompt.

    Stable actor/workspace ids are security inputs; display names are presentation only.
    `response_url` is Slack's short-lived reply capability for a private rejection notice.
    """

    platform: str
    chat_id: str
    message_id: Optional[str]  # the clicked message's id/ts (to update it)
    value: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    team_id: Optional[str] = None
    response_url: Optional[str] = None


InteractionHandler = Callable[[InteractionEvent], Awaitable[None]]


class BasePlatformAdapter(ABC):
    """One messaging platform. Subclasses implement connect/disconnect/send and call
    `handle_message` for inbound events."""

    platform: str = "base"

    def __init__(self) -> None:
        self._handler: Optional[MessageHandler] = None
        self._interaction_handler: Optional[InteractionHandler] = None
        self.account_id = "default"
        self._channel_state = "disconnected"
        self._channel_authenticated = False
        self._last_received_at: Optional[float] = None
        self._last_sent_at: Optional[float] = None
        self._reconnect_count = 0
        self._last_error = ""
        self._outbound_gate = asyncio.Lock()
        self._next_outbound_at = 0.0
        # One FIFO per conversation.  A single account-wide worker made an unrelated
        # employee wait behind a long Agent turn in another chat and defeated the global
        # Channel concurrency limit.  Route-local workers preserve ordering without
        # serialising every conversation on the platform.
        self._inbound_queues: dict[
            tuple[str, str, str], asyncio.Queue[tuple[MessageEvent, asyncio.Future]]
        ] = {}
        self._inbound_workers: dict[tuple[str, str, str], asyncio.Task] = {}
        from ..channels.models import ChannelCapabilities

        self.capabilities = ChannelCapabilities()

    async def throttle_outbound(self, min_interval: float = 0.08) -> None:
        """Small per-account send gate to avoid accidental platform bursts."""
        loop = asyncio.get_running_loop()
        async with self._outbound_gate:
            delay = self._next_outbound_at - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            self._next_outbound_at = loop.time() + max(0.0, min_interval)

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._handler = handler

    def set_interaction_handler(self, handler: InteractionHandler) -> None:
        self._interaction_handler = handler

    async def send_interactive(
        self, chat_id: str, text: str, buttons, *, thread_id: Optional[str] = None
    ) -> SendResult:
        """Send a prompt with choice buttons. Default: plain text (adapters without interactive
        support just show the text — the user answers in the app)."""
        return await self.send(chat_id, text, thread_id=thread_id)

    async def handle_interaction(self, event: InteractionEvent) -> None:
        if self._interaction_handler is not None:
            await self._interaction_handler(event)

    @abstractmethod
    async def connect(self) -> bool:
        """Connect + start the inbound listener. True on success."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Stop the listener and close connections."""

    @abstractmethod
    async def send(
        self, chat_id: str, text: str, *, thread_id: Optional[str] = None
    ) -> SendResult:
        """Send an outbound message."""

    async def handle_message(self, event: MessageEvent) -> None:
        self._last_received_at = time()
        if self._handler is not None:
            await self._handler(event)

    async def enqueue_message(self, event: MessageEvent) -> asyncio.Future:
        """Enqueue one conversation in FIFO order while other chats run concurrently."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        route_key = (
            self.platform,
            self.account_id,
            str(event.source.chat_id or event.source.user_id or "unknown"),
        )
        queue = self._inbound_queues.setdefault(route_key, asyncio.Queue())
        await queue.put((event, future))
        worker = self._inbound_workers.get(route_key)
        if worker is None or worker.done():
            self._inbound_workers[route_key] = asyncio.create_task(
                self._drain_inbound(route_key),
                name=f"channel-ingress:{':'.join(route_key)}",
            )
        future.add_done_callback(
            lambda done: None if done.cancelled() else done.exception()
        )
        return future

    async def _drain_inbound(self, route_key: tuple[str, str, str]) -> None:
        queue = self._inbound_queues[route_key]
        try:
            while not queue.empty():
                event, future = await queue.get()
                try:
                    await self.handle_message(event)
                except Exception as exc:
                    self._last_error = (
                        f"{self.platform} 入站消息处理失败（{type(exc).__name__}）"
                    )
                    if not future.done():
                        future.set_exception(exc)
                else:
                    if not future.done():
                        future.set_result(None)
                finally:
                    queue.task_done()
        finally:
            self._inbound_workers.pop(route_key, None)
            if queue.empty():
                self._inbound_queues.pop(route_key, None)

    async def drain_inbound(self) -> None:
        """Wait until all of this adapter's testable conversation FIFOs are empty."""
        queues = list(self._inbound_queues.values())
        if queues:
            await asyncio.gather(*(queue.join() for queue in queues))

    async def start(self) -> bool:
        """D-193 ChannelAdapter lifecycle alias.

        ``connect()`` may leave the adapter in ``auth_required`` (e.g. Weixin QR
        pending). Do not overwrite that to ``connected`` just because start succeeded.
        """
        self._channel_state = "connecting"
        try:
            ok = await self.connect()
        except Exception as exc:
            self._channel_state = "degraded"
            # Some SDK exceptions echo credentials. Status is deliberately content-free.
            self._last_error = f"{self.platform} 连接失败（{type(exc).__name__}）"
            raise
        if not ok:
            if self._channel_state == "connecting":
                self._channel_state = "degraded"
            self._channel_authenticated = False
            return False
        if self._channel_state == "connecting":
            self._channel_state = "connected"
        self._channel_authenticated = self._channel_state == "connected"
        return True

    async def stop(self) -> None:
        await self.disconnect()
        workers = list(self._inbound_workers.values())
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
        self._inbound_workers.clear()
        self._inbound_queues.clear()
        self._channel_state = "disconnected"
        self._channel_authenticated = False

    def channel_status(self):
        """Content-free status snapshot shared by every adapter."""
        from ..channels.models import ChannelStatus

        return ChannelStatus(
            platform=self.platform,
            account_id=self.account_id,
            state=self._channel_state,
            authenticated=self._channel_authenticated,
            last_received_at=self._last_received_at,
            last_sent_at=self._last_sent_at,
            reconnect_count=self._reconnect_count,
            last_error=self._last_error,
            capabilities=self.capabilities,
        )

    def status(self):
        """Public ChannelAdapter status alias; keep channel_status for legacy callers."""
        return self.channel_status()

    async def send_envelope(self, envelope: "OutboundEnvelope") -> SendResult:
        """Compatibility bridge for legacy adapters while callers migrate to envelopes."""
        if envelope.attachments:
            return SendResult(False, error=f"{self.platform} 暂不支持附件发送")
        result = await self.send(
            envelope.conversation_id, envelope.text, thread_id=envelope.reply_to
        )
        if result.ok:
            self._last_sent_at = time()
        else:
            self._last_error = result.error or "发送失败"
        return result
