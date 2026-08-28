"""Thin channel message contracts — unified inbound/outbound for IM adapters.

Phase 6 (D-188): WeCom AI Bot maps through these types into the existing
connectors Gateway `MessageEvent` / `SessionSource`. Slack/Telegram stay on the
legacy path; future Feishu/DingTalk should reuse this seam.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class ChannelAttachment:
    kind: str  # "image" | "file" | "voice" | "other"
    url: str = ""
    name: str = ""
    aes_key: str = ""
    size: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InboundMessage:
    channel: str  # platform id, e.g. "wecom"
    conversation_id: str
    user_id: str
    message_id: str
    text: str = ""
    user_name: str = ""
    conversation_name: str = ""
    chat_type: str = "dm"  # "dm" | "group" | "channel"
    mentions: list[str] = field(default_factory=list)
    mentions_bot: bool = False
    attachments: list[ChannelAttachment] = field(default_factory=list)
    reply_to: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class OutboundMessage:
    channel: str
    conversation_id: str
    kind: str = "final"  # "progress" | "final" | "error"
    text: str = ""
    reply_to: Optional[str] = None
    attachment_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
