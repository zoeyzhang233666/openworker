"""Stable, platform-neutral Channel value objects (D-193).

The contracts deliberately contain no SDK objects. Platform adapters translate their
wire payloads to these dataclasses before they enter the connector Gateway. The legacy
``InboundMessage``/``OutboundMessage`` names remain as compatibility constructors for
the first WeCom implementation (D-188).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import time
from typing import Any, Optional


@dataclass(frozen=True)
class ChannelCapabilities:
    direct_messages: bool = True
    group_chat: bool = False
    group_mentions: bool = False
    proactive_messages: bool = False
    streaming: bool = False
    receive_images: bool = False
    send_images: bool = False
    receive_files: bool = False
    send_files: bool = False
    max_inbound_bytes: Optional[int] = None
    max_outbound_bytes: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChannelStatus:
    platform: str
    account_id: str = "default"
    state: str = "disconnected"
    authenticated: bool = False
    last_received_at: Optional[float] = None
    last_sent_at: Optional[float] = None
    queue_length: int = 0
    reconnect_count: int = 0
    last_error: str = ""
    capabilities: ChannelCapabilities = field(default_factory=ChannelCapabilities)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def connected(self) -> bool:
        return self.state == "connected"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChannelAttachment:
    kind: str
    name: str = ""
    mime_type: str = ""
    size: Optional[int] = None
    remote_ref: str = ""
    local_path: str = ""
    file_ref: dict[str, Any] = field(default_factory=dict)
    encryption: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    # D-188 compatibility. New adapters prefer remote_ref/encryption.
    url: str = ""
    aes_key: str = ""

    def __post_init__(self) -> None:
        if not self.remote_ref and self.url:
            self.remote_ref = self.url
        if not self.url and self.remote_ref:
            self.url = self.remote_ref
        if self.aes_key and "aes_key" not in self.encryption:
            self.encryption["aes_key"] = self.aes_key

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InboundEnvelope:
    platform: str
    account_id: str
    conversation_id: str
    chat_type: str
    user_id: str
    message_id: str
    text: str = ""
    user_name: str = ""
    conversation_name: str = ""
    mentions_bot: bool = False
    reply_to: Optional[str] = None
    context_token: str = ""
    attachments: list[ChannelAttachment] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    received_at: float = field(default_factory=time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def channel(self) -> str:
        return self.platform

    @property
    def route_key(self) -> tuple[str, str, str]:
        return (self.platform, self.account_id or "default", self.conversation_id)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InboundMessage(InboundEnvelope):
    """Backward-compatible constructor accepting ``channel=`` instead of platform."""

    def __init__(
        self,
        channel: str,
        conversation_id: str,
        user_id: str,
        message_id: str,
        text: str = "",
        user_name: str = "",
        conversation_name: str = "",
        chat_type: str = "dm",
        mentions: Optional[list[str]] = None,
        mentions_bot: bool = False,
        attachments: Optional[list[ChannelAttachment]] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        *,
        account_id: str = "default",
        context_token: str = "",
        received_at: Optional[float] = None,
    ) -> None:
        super().__init__(
            platform=channel,
            account_id=account_id or "default",
            conversation_id=conversation_id,
            chat_type=chat_type,
            user_id=user_id,
            message_id=message_id,
            text=text,
            user_name=user_name,
            conversation_name=conversation_name,
            mentions_bot=mentions_bot,
            reply_to=reply_to,
            context_token=context_token,
            attachments=list(attachments or []),
            mentions=list(mentions or []),
            received_at=time() if received_at is None else received_at,
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        out = super().to_dict()
        out["channel"] = out["platform"]
        return out


@dataclass
class OutboundEnvelope:
    platform: str
    account_id: str
    conversation_id: str
    kind: str = "final"
    text: str = ""
    reply_to: Optional[str] = None
    attachments: list[ChannelAttachment] = field(default_factory=list)
    idempotency_key: str = ""
    context_token: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def channel(self) -> str:
        return self.platform

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OutboundMessage(OutboundEnvelope):
    """D-188 compatibility constructor accepting ``channel=``/attachment refs."""

    def __init__(
        self,
        channel: str,
        conversation_id: str,
        kind: str = "final",
        text: str = "",
        reply_to: Optional[str] = None,
        attachment_refs: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        *,
        account_id: str = "default",
        attachments: Optional[list[ChannelAttachment]] = None,
        idempotency_key: str = "",
        context_token: str = "",
    ) -> None:
        normalized = list(attachments or [])
        normalized.extend(
            ChannelAttachment(kind="file", remote_ref=ref)
            for ref in (attachment_refs or [])
        )
        super().__init__(
            platform=channel,
            account_id=account_id or "default",
            conversation_id=conversation_id,
            kind=kind,
            text=text,
            reply_to=reply_to,
            attachments=normalized,
            idempotency_key=idempotency_key,
            context_token=context_token,
            metadata=dict(metadata or {}),
        )

    @property
    def attachment_refs(self) -> list[str]:
        return [a.remote_ref or a.local_path for a in self.attachments]

    def to_dict(self) -> dict[str, Any]:
        out = super().to_dict()
        out["channel"] = out["platform"]
        out["attachment_refs"] = self.attachment_refs
        return out
