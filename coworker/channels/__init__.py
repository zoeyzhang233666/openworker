"""ChemClaw's platform-neutral Channel seam (D-188, deepened by D-193)."""

from .base import ChannelAdapter
from .media import ChannelMediaError, ChannelMediaManager
from .runtime import ChannelDeliveryCoordinator, MessageDeduplicator
from .mappings import (
    frame_to_inbound,
    inbound_to_message_event,
    wecom_frame_to_message_event,
)
from .models import (
    ChannelAttachment,
    ChannelCapabilities,
    ChannelStatus,
    InboundEnvelope,
    InboundMessage,
    OutboundEnvelope,
    OutboundMessage,
)
from .platform_mappings import (
    dingtalk_callback_to_inbound,
    feishu_event_to_inbound,
    weixin_update_to_inbound,
)

__all__ = [
    "ChannelAdapter",
    "ChannelDeliveryCoordinator",
    "ChannelAttachment",
    "ChannelCapabilities",
    "ChannelStatus",
    "ChannelMediaError",
    "ChannelMediaManager",
    "MessageDeduplicator",
    "InboundEnvelope",
    "InboundMessage",
    "OutboundEnvelope",
    "OutboundMessage",
    "frame_to_inbound",
    "inbound_to_message_event",
    "wecom_frame_to_message_event",
    "feishu_event_to_inbound",
    "dingtalk_callback_to_inbound",
    "weixin_update_to_inbound",
]
