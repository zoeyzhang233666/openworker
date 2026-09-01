"""Pure wire-payload mappers for Feishu, DingTalk and official Weixin iLink."""

from __future__ import annotations

import json
from typing import Any, Optional

from .models import ChannelAttachment, InboundEnvelope


def _s(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def feishu_event_to_inbound(
    payload: dict[str, Any], *, account_id: str = "default", bot_open_id: str = ""
) -> Optional[InboundEnvelope]:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
    sender_id = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}
    message_id = _s(message.get("message_id"))
    conversation_id = _s(message.get("chat_id"))
    user_id = _s(sender_id.get("open_id") or sender_id.get("user_id") or sender_id.get("union_id"))
    if not message_id or not conversation_id or not user_id:
        return None
    raw_type = _s(message.get("message_type") or "text").lower()
    content = _json_object(message.get("content"))
    chat_type = "group" if _s(message.get("chat_type")).lower() == "group" else "dm"
    mentions = message.get("mentions") if isinstance(message.get("mentions"), list) else []
    mention_ids = [
        _s((item.get("id") or {}).get("open_id") if isinstance(item.get("id"), dict) else item.get("open_id"))
        for item in mentions
        if isinstance(item, dict)
    ]
    mentions_bot = chat_type == "dm" or bool(mentions)
    if bot_open_id and chat_type == "group":
        mentions_bot = bot_open_id in mention_ids
    # Gateway may consume an unmentioned reply to a pending ask_user prompt.
    # Ordinary group traffic remains ignored by SessionManager.

    attachments: list[ChannelAttachment] = []
    text = ""
    if raw_type == "text":
        text = _s(content.get("text"))
    elif raw_type == "image":
        key = _s(content.get("image_key"))
        attachments.append(
            ChannelAttachment(
                kind="image",
                name=f"{key or message_id}.png",
                mime_type="image/png",
                remote_ref=key,
                metadata={"message_id": message_id, "resource_type": "image"},
            )
        )
        text = "[图片]"
    elif raw_type in {"file", "audio", "media"}:
        key = _s(content.get("file_key"))
        name = _s(content.get("file_name") or content.get("name")) or f"{key or message_id}.bin"
        kind = "voice" if raw_type == "audio" else "video" if raw_type == "media" else "file"
        attachments.append(
            ChannelAttachment(
                kind=kind,
                name=name,
                remote_ref=key,
                metadata={"message_id": message_id, "resource_type": raw_type},
            )
        )
        text = f"[文件] {name}"
    elif raw_type == "post":
        title = _s(content.get("title"))
        lines: list[str] = [title] if title else []
        blocks = content.get("content") if isinstance(content.get("content"), list) else []
        for row in blocks:
            if not isinstance(row, list):
                continue
            for item in row:
                if not isinstance(item, dict):
                    continue
                if item.get("tag") == "text":
                    lines.append(_s(item.get("text")))
                if item.get("tag") == "img":
                    key = _s(item.get("image_key"))
                    attachments.append(
                        ChannelAttachment(
                            kind="image",
                            name=f"{key or message_id}.png",
                            mime_type="image/png",
                            remote_ref=key,
                            metadata={"message_id": message_id, "resource_type": "image"},
                        )
                    )
        text = "\n".join(line for line in lines if line) or "[图文消息]"
    else:
        text = f"[暂不支持的飞书消息：{raw_type}]"

    return InboundEnvelope(
        platform="feishu",
        account_id=account_id or "default",
        conversation_id=conversation_id,
        chat_type=chat_type,
        user_id=user_id,
        message_id=message_id,
        text=text,
        user_name=_s(sender.get("sender_name")) or user_id,
        conversation_name=_s(message.get("chat_name")),
        mentions_bot=mentions_bot,
        reply_to=_s(message.get("parent_id") or message.get("root_id")) or None,
        attachments=attachments,
        mentions=[m for m in mention_ids if m],
        metadata={"message_type": raw_type},
    )


def dingtalk_callback_to_inbound(
    payload: dict[str, Any], *, account_id: str = "default"
) -> Optional[InboundEnvelope]:
    message_id = _s(payload.get("msgId") or payload.get("msg_id"))
    user_id = _s(
        payload.get("senderStaffId")
        or payload.get("senderId")
        or payload.get("senderCorpId")
    )
    conversation_id = _s(
        payload.get("conversationId") or payload.get("conversation_id") or user_id
    )
    if not message_id or not user_id or not conversation_id:
        return None
    conversation_type = _s(payload.get("conversationType") or payload.get("chatbotCorpId"))
    chat_type = "group" if conversation_type in {"2", "group"} else "dm"
    if chat_type == "dm":
        conversation_id = user_id
    msg_type = _s(payload.get("msgtype") or payload.get("msgType") or "text").lower()
    text_obj = payload.get("text") if isinstance(payload.get("text"), dict) else {}
    content_obj = payload.get("content") if isinstance(payload.get("content"), dict) else {}
    raw_text = text_obj.get("content")
    if not raw_text and isinstance(payload.get("content"), str):
        raw_text = payload.get("content")
    text = _s(raw_text)
    attachments: list[ChannelAttachment] = []
    if msg_type in {"picture", "image", "file", "audio", "video"}:
        remote_ref = _s(
            content_obj.get("downloadCode")
            or content_obj.get("download_code")
            or payload.get("downloadCode")
        )
        name = _s(
            content_obj.get("fileName")
            or content_obj.get("filename")
            or payload.get("fileName")
        ) or f"{message_id}.bin"
        kind = "image" if msg_type in {"picture", "image"} else "voice" if msg_type == "audio" else msg_type
        attachments.append(
            ChannelAttachment(
                kind=kind,
                name=name,
                remote_ref=remote_ref,
                metadata={"download_code": remote_ref},
            )
        )
        text = text or ("[图片]" if kind == "image" else f"[文件] {name}")
    elif msg_type == "richtext":
        rich_items = (
            content_obj.get("richText")
            if isinstance(content_obj.get("richText"), list)
            else []
        )
        lines: list[str] = []
        for index, item in enumerate(rich_items):
            if not isinstance(item, dict):
                continue
            if item.get("text"):
                lines.append(_s(item.get("text")))
            remote_ref = _s(item.get("downloadCode"))
            if remote_ref:
                attachments.append(
                    ChannelAttachment(
                        kind="image",
                        name=f"{message_id}-{index + 1}.png",
                        mime_type="image/png",
                        remote_ref=remote_ref,
                        metadata={"download_code": remote_ref},
                    )
                )
        text = "\n".join(line for line in lines if line) or "[图文消息]"
    at_users = payload.get("atUsers") if isinstance(payload.get("atUsers"), list) else []
    mentions_bot = chat_type == "dm" or bool(payload.get("isInAtList") or at_users)
    # Gateway may consume an unmentioned reply to a pending ask_user prompt.
    # Ordinary group traffic remains ignored by SessionManager.
    return InboundEnvelope(
        platform="dingtalk",
        account_id=account_id or "default",
        conversation_id=conversation_id,
        chat_type=chat_type,
        user_id=user_id,
        message_id=message_id,
        text=text,
        user_name=_s(payload.get("senderNick") or payload.get("senderName")) or user_id,
        conversation_name=_s(payload.get("conversationTitle")),
        mentions_bot=mentions_bot,
        attachments=attachments,
        metadata={
            "message_type": msg_type,
            "session_webhook": _s(payload.get("sessionWebhook")),
            "robot_code": _s(payload.get("robotCode")),
        },
    )


def weixin_update_to_inbound(
    message: dict[str, Any], *, account_id: str = "default"
) -> Optional[InboundEnvelope]:
    user_id = _s(message.get("from_user_id"))
    message_id = _s(message.get("message_id") or message.get("seq"))
    if not user_id or not message_id:
        return None
    text_parts: list[str] = []
    attachments: list[ChannelAttachment] = []
    for item in message.get("item_list") or []:
        if not isinstance(item, dict):
            continue
        item_type = int(item.get("type") or 0)
        if item_type == 1:
            text_parts.append(_s((item.get("text_item") or {}).get("text")))
            continue
        key = {2: "image_item", 3: "voice_item", 4: "file_item", 5: "video_item"}.get(item_type)
        if not key:
            continue
        info = item.get(key) if isinstance(item.get(key), dict) else {}
        media = info.get("media") if isinstance(info.get("media"), dict) else {}
        kind = {2: "image", 3: "voice", 4: "file", 5: "video"}[item_type]
        default_ext = {2: ".jpg", 3: ".silk", 4: ".bin", 5: ".mp4"}[item_type]
        name = _s(info.get("file_name")) or f"wx_{message_id}{default_ext}"
        attachments.append(
            ChannelAttachment(
                kind=kind,
                name=name,
                remote_ref=_s(media.get("encrypt_query_param")),
                encryption={
                    "aes_key": _s(info.get("aeskey") or media.get("aes_key")),
                    "encrypt_type": media.get("encrypt_type"),
                },
            )
        )
    text = "\n".join(part for part in text_parts if part)
    if not text and attachments:
        text = "[图片]" if attachments[0].kind == "image" else f"[文件] {attachments[0].name}"
    return InboundEnvelope(
        platform="weixin",
        account_id=account_id or "default",
        conversation_id=user_id,
        chat_type="dm",
        user_id=user_id,
        message_id=message_id,
        text=text,
        mentions_bot=True,
        context_token=_s(message.get("context_token")),
        attachments=attachments,
        metadata={"create_time_ms": message.get("create_time_ms")},
    )
