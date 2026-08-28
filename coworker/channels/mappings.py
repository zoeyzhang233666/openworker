"""Map WeCom AI Bot WebSocket frames ↔ InboundMessage ↔ connectors MessageEvent."""

from __future__ import annotations

from typing import Any, Optional

from ..connectors.base import MessageEvent, MessageType, SessionSource
from .models import ChannelAttachment, InboundMessage

# WeCom AI bot chat types observed in SDK / docs.
_GROUP_MARKERS = frozenset({"group", "room", "chatgroup", "groupchat"})


def _body(frame: dict[str, Any]) -> dict[str, Any]:
    body = frame.get("body")
    return body if isinstance(body, dict) else {}


def _str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def wecom_chat_type(body: dict[str, Any]) -> str:
    raw = (
        _str(body.get("chattype"))
        or _str(body.get("chat_type"))
        or _str(body.get("conversation_type"))
    ).lower()
    if raw in _GROUP_MARKERS or raw == "group":
        return "group"
    # Some payloads use chatid starting with wr/ for rooms; prefer explicit field.
    if body.get("chatid") and body.get("from") and _str(body.get("chatid")) != _str(
        body.get("from", {}).get("userid") if isinstance(body.get("from"), dict) else ""
    ):
        # Distinct chatid vs userid often means a group conversation.
        if raw in ("", "single", "single_chat", "dm", "private"):
            if raw in ("single", "single_chat", "dm", "private"):
                return "dm"
        if "group" in raw or "room" in raw:
            return "group"
    if raw in ("", "single", "single_chat", "dm", "private"):
        return "dm"
    return "group" if "group" in raw or "room" in raw else "dm"


def wecom_conversation_id(body: dict[str, Any]) -> str:
    for key in ("chatid", "chat_id", "conversation_id", "roomid"):
        v = _str(body.get(key))
        if v:
            return v
    frm = body.get("from")
    if isinstance(frm, dict):
        return _str(frm.get("userid") or frm.get("user_id"))
    return _str(body.get("userid") or body.get("from_userid"))


def wecom_user_id(body: dict[str, Any]) -> str:
    frm = body.get("from")
    if isinstance(frm, dict):
        return _str(frm.get("userid") or frm.get("user_id") or frm.get("id"))
    return _str(body.get("from_userid") or body.get("userid") or body.get("sender"))


def wecom_user_name(body: dict[str, Any]) -> str:
    frm = body.get("from")
    if isinstance(frm, dict):
        return _str(frm.get("name") or frm.get("alias") or frm.get("userid"))
    return ""


def wecom_text_content(body: dict[str, Any], msgtype: str) -> str:
    if msgtype == "text":
        text = body.get("text")
        if isinstance(text, dict):
            return _str(text.get("content"))
        return _str(text)
    if msgtype == "voice":
        voice = body.get("voice") if isinstance(body.get("voice"), dict) else {}
        return _str(voice.get("content") or voice.get("recognition") or "[语音]")
    if msgtype == "mixed":
        parts: list[str] = []
        mixed = body.get("mixed") if isinstance(body.get("mixed"), dict) else body
        items = mixed.get("msg_item") or mixed.get("items") or []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("msgtype") == "text" or "text" in item:
                    t = item.get("text")
                    if isinstance(t, dict):
                        parts.append(_str(t.get("content")))
                    else:
                        parts.append(_str(t))
                elif item.get("msgtype") == "image" or "image" in item:
                    parts.append("[图片]")
        return "\n".join(p for p in parts if p) or "[图文消息]"
    if msgtype == "image":
        return "[图片]"
    if msgtype == "file":
        f = body.get("file") if isinstance(body.get("file"), dict) else {}
        name = _str(f.get("filename") or f.get("name"))
        return f"[文件] {name}".strip() if name else "[文件]"
    return _str(body.get("content"))


def wecom_attachments(body: dict[str, Any], msgtype: str) -> list[ChannelAttachment]:
    out: list[ChannelAttachment] = []
    if msgtype == "image":
        img = body.get("image") if isinstance(body.get("image"), dict) else {}
        out.append(
            ChannelAttachment(
                kind="image",
                url=_str(img.get("url")),
                aes_key=_str(img.get("aeskey") or img.get("aes_key")),
                name=_str(img.get("filename") or "image"),
            )
        )
    elif msgtype == "file":
        f = body.get("file") if isinstance(body.get("file"), dict) else {}
        size = f.get("filesize") or f.get("size")
        out.append(
            ChannelAttachment(
                kind="file",
                url=_str(f.get("url")),
                aes_key=_str(f.get("aeskey") or f.get("aes_key")),
                name=_str(f.get("filename") or f.get("name") or "file"),
                size=int(size) if isinstance(size, (int, float)) else None,
            )
        )
    return out


def wecom_mentions_bot(body: dict[str, Any], *, chat_type: str) -> bool:
    """Group traffic: prefer explicit flags; default True (AI Bot usually only pushes @ msgs)."""
    if chat_type == "dm":
        return True
    if body.get("is_mentioned") is False or body.get("mentioned") is False:
        return False
    if body.get("is_mentioned") is True or body.get("mentioned") is True:
        return True
    for key in ("mentioned_list", "mention_list", "at_list"):
        lst = body.get(key)
        if isinstance(lst, list) and lst:
            return True
    # Platform long-connection typically delivers group frames only when the bot
    # is addressed; treat those as mentions unless explicitly marked otherwise.
    return True


def frame_to_inbound(frame: dict[str, Any]) -> Optional[InboundMessage]:
    """Convert a WeCom AI Bot callback frame to InboundMessage, or None if not a user message."""
    if not isinstance(frame, dict):
        return None
    body = _body(frame)
    msgtype = _str(body.get("msgtype") or body.get("msg_type") or frame.get("msgtype"))
    if not msgtype:
        # Event frames (enter_chat etc.) are not user messages.
        if _str(frame.get("cmd") or "").startswith("aibot_event") or body.get("event_type"):
            return None
        msgtype = "text"
    if msgtype in ("event", "template_card_event", "feedback_event"):
        return None

    chat_type = wecom_chat_type(body)
    conversation_id = wecom_conversation_id(body)
    user_id = wecom_user_id(body)
    if not conversation_id and not user_id:
        return None
    if not conversation_id:
        conversation_id = user_id

    message_id = _str(
        body.get("msgid")
        or body.get("msg_id")
        or frame.get("req_id")
        or frame.get("id")
    )
    text = wecom_text_content(body, msgtype)
    mentions_bot = wecom_mentions_bot(body, chat_type=chat_type)
    if chat_type == "group" and not mentions_bot:
        return None  # explicit is_mentioned=false

    return InboundMessage(
        channel="wecom",
        conversation_id=conversation_id,
        user_id=user_id or "?",
        message_id=message_id,
        text=text,
        user_name=wecom_user_name(body),
        conversation_name=_str(body.get("chatname") or body.get("chat_name")),
        chat_type=chat_type,
        mentions_bot=mentions_bot,
        attachments=wecom_attachments(body, msgtype),
        metadata={"msgtype": msgtype, "raw_cmd": _str(frame.get("cmd"))},
    )


def inbound_to_message_event(
    inbound: InboundMessage, *, raw: Any = None
) -> MessageEvent:
    source = SessionSource(
        platform=inbound.channel,
        chat_id=inbound.conversation_id,
        user_id=inbound.user_id if inbound.user_id != "?" else None,
        user_name=inbound.user_name or None,
        chat_name=inbound.conversation_name or None,
        chat_type=inbound.chat_type,
    )
    mtype = MessageType.TEXT
    if inbound.attachments and not (inbound.text or "").strip():
        mtype = MessageType.MEDIA
    return MessageEvent(
        text=inbound.text or "",
        source=source,
        message_id=inbound.message_id or None,
        message_type=mtype,
        raw=raw,
        mentions_me=inbound.mentions_bot,
    )


def wecom_frame_to_message_event(frame: dict[str, Any]) -> Optional[MessageEvent]:
    inbound = frame_to_inbound(frame)
    if inbound is None:
        return None
    return inbound_to_message_event(inbound, raw=frame)
