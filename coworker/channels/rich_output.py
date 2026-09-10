"""Safe rich-output delivery for text-only messaging Channels (D-199 / D-199b).

Desktop ChemClaw renders fenced ``chart``/Mermaid blocks. Messaging clients do not, so
those renderer inputs must never be treated as ordinary chat text. This module is the
single policy seam used by live drafts, automatic terminal replies, and ``send_message``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..filestore.base import FileStorage, FileStorageError, NullFileStorage
from ..report_html.chart_spec import normalize_chart_spec_dict
from ..report_html.cook import cook_report_html, find_report_markdown
from ..report_html.preview import PreviewRenderer, render_chart_preview_png
from .wecom_reply import (
    strip_md_artifacts_for_wecom,
    truncate_summary,
    wants_full_bubble,
    wants_image_only,
)

_FENCE_OPEN = re.compile(
    r"(?m)^(?P<indent>[ \t]*)```(?P<lang>[A-Za-z0-9_-]*)[^\r\n]*\r?\n"
)
_FENCE_CLOSE = re.compile(r"(?m)^[ \t]*```[ \t]*(?:\r?\n|$)")
_RENDER_LANGS = frozenset({"chart", "mermaid", "mmd"})


@dataclass
class ChannelRichReply:
    text: str
    has_rich_blocks: bool = False
    html_url: Optional[str] = None
    html_path: Optional[Path] = None
    html_bytes: bytes = b""
    filename: str = "ChemClaw-交互图表.html"
    preview_image_bytes: bytes = b""
    preview_image_path: Optional[Path] = None
    preview_filename: str = "ChemClaw-图表预览.png"
    delivery_mode: str = "summary_only"
    error: str = ""
    image_only: bool = False


def has_renderer_blocks(text: str) -> bool:
    return any(
        (match.group("lang") or "").strip().lower() in _RENDER_LANGS
        for match in _FENCE_OPEN.finditer(text or "")
    )


def needs_channel_html_delivery(
    assistant_text: str,
    workspace: Path | str | None,
) -> bool:
    return has_renderer_blocks(assistant_text) or find_report_markdown(
        assistant_text or "", workspace
    ) is not None


def channel_visible_text(text: str, *, final: bool = False) -> str:
    """Return only text safe for a client that cannot render ChemClaw blocks."""
    raw = text or ""
    out: list[str] = []
    cursor = 0
    while True:
        opening = _FENCE_OPEN.search(raw, cursor)
        if opening is None:
            out.append(raw[cursor:])
            break
        lang = (opening.group("lang") or "").strip().lower()
        closing = _FENCE_CLOSE.search(raw, opening.end())
        if lang not in _RENDER_LANGS:
            if closing is None:
                out.append(raw[cursor:])
                break
            out.append(raw[cursor : closing.end()])
            cursor = closing.end()
            continue
        out.append(raw[cursor : opening.start()])
        if closing is None:
            break
        cursor = closing.end()
    visible = "".join(out)
    visible = re.sub(r"[ \t]+\r?\n", "\n", visible)
    visible = re.sub(r"\n{3,}", "\n\n", visible)
    visible = visible.strip()
    if final and has_renderer_blocks(raw) and not visible:
        return "图表已整理为可打开的 HTML 网页。"
    return visible


def compose_channel_rich_reply(
    *,
    assistant_text: str,
    workspace: Path | str | None,
    file_storage: FileStorage | None,
    chart_tool_results: list[dict[str, Any]] | None = None,
    user_text: str = "",
    title: str = "ChemClaw 交互图表",
    render_preview: Optional[PreviewRenderer] = None,
) -> ChannelRichReply:
    """Build IM-safe bubble text plus optional preview PNG and a single HTML link."""
    raw = _salvage_chart_markdown(assistant_text or "", chart_tool_results)
    stripped = strip_md_artifacts_for_wecom(raw)
    image_only = wants_image_only(user_text)
    if wants_full_bubble(user_text):
        return ChannelRichReply(
            text=stripped or "（无正文）",
            has_rich_blocks=has_renderer_blocks(raw),
            delivery_mode="full_bubble",
        )

    visible = channel_visible_text(raw, final=True)
    summary = truncate_summary(visible) if visible else "本轮已完成。"
    md_path = find_report_markdown(raw, workspace)
    inline_blocks = has_renderer_blocks(raw)

    if md_path is None and not inline_blocks:
        return ChannelRichReply(text=summary, delivery_mode="summary_only")

    link_label = "查看完整版" if md_path is not None else "查看交互图表"
    cook_title = title
    cook_markdown = raw
    if md_path is not None:
        try:
            cook_markdown = md_path.read_text(encoding="utf-8")
            cook_title = md_path.stem
        except OSError:
            if not inline_blocks:
                return ChannelRichReply(
                    text=f"{summary}\n\n（完整版报告文件无法读取）",
                    delivery_mode="summary_only",
                )
            cook_markdown = raw
            link_label = "查看交互图表"

    try:
        cooked = cook_report_html(
            cook_markdown,
            title=cook_title,
            chart_tool_results=chart_tool_results,
            workspace=workspace,
            write_local=workspace is not None,
        )
    except Exception as exc:
        note = f"（网页生成失败：{type(exc).__name__}；原始数据已隐藏）"
        return ChannelRichReply(
            text=f"{summary}\n\n{note}".strip(),
            has_rich_blocks=True,
            delivery_mode="summary_only",
            error=note,
        )

    filename = _html_filename(cooked.title or cook_title)
    html_bytes = cooked.html.encode("utf-8")
    preview_bytes = b""
    preview_path: Optional[Path] = None
    if cooked.chart_count > 0:
        preview_bytes = (
            render_chart_preview_png(
                cooked.local_path or "",
                render=render_preview,
                html_bytes=html_bytes if cooked.local_path is None else None,
                chart_specs=list(cooked.charts),
            )
            or b""
        )
        if preview_bytes and cooked.local_path is not None:
            preview_path = _write_preview_png(
                preview_bytes, cooked.local_path, cooked.title or cook_title
            )
        elif preview_bytes:
            preview_path = _write_preview_png_bytes(
                preview_bytes, workspace, cooked.title or cook_title
            )

    storage = file_storage or NullFileStorage()
    upload_error = ""
    if storage.configured() and not image_only:
        try:
            ref = storage.upload(
                html_bytes,
                filename=filename,
                content_type="text/html; charset=utf-8",
            )
            url = storage.public_url(ref)
            return ChannelRichReply(
                text=f"{summary}\n\n[{link_label}]({url})".strip(),
                has_rich_blocks=True,
                html_url=url,
                html_path=cooked.local_path,
                html_bytes=html_bytes,
                filename=filename,
                preview_image_bytes=preview_bytes,
                preview_image_path=preview_path,
                delivery_mode="summary_link",
                image_only=image_only,
            )
        except FileStorageError as exc:
            upload_error = str(exc)
        except Exception as exc:
            upload_error = f"{type(exc).__name__}"

    if image_only:
        if preview_bytes:
            note = "（图表预览见上方图片）"
            return ChannelRichReply(
                text=f"{summary}\n\n{note}".strip(),
                has_rich_blocks=True,
                html_path=cooked.local_path,
                html_bytes=html_bytes,
                filename=filename,
                preview_image_bytes=preview_bytes,
                preview_image_path=preview_path,
                delivery_mode="image_only",
                image_only=True,
            )
        note = "（未能生成图表预览图；请确认 sidecar 已包含 Matplotlib）"
        if cooked.chart_count == 0:
            note = "（未能解析图表数据；请确认工具返回了有效时间序列）"
        return ChannelRichReply(
            text=f"{summary}\n\n{note}".strip(),
            has_rich_blocks=True,
            html_path=cooked.local_path,
            html_bytes=html_bytes,
            filename=filename,
            delivery_mode="summary_only",
            image_only=True,
            error=note,
        )

    if cooked.local_path is not None:
        note = f"{link_label}已整理为 HTML 文件。"
        if upload_error:
            note += "（云端链接不可用，已改用附件）"
        return ChannelRichReply(
            text=f"{summary}\n\n{note}".strip(),
            has_rich_blocks=True,
            html_path=cooked.local_path,
            html_bytes=html_bytes,
            filename=filename,
            preview_image_bytes=preview_bytes,
            preview_image_path=preview_path,
            delivery_mode="summary_link",
            error=upload_error,
        )

    note = "（网页无法生成可发送的文件；原始数据已隐藏）"
    return ChannelRichReply(
        text=f"{summary}\n\n{note}".strip(),
        has_rich_blocks=True,
        html_bytes=html_bytes,
        filename=filename,
        preview_image_bytes=preview_bytes,
        preview_image_path=preview_path,
        delivery_mode="summary_only",
        error=upload_error or note,
    )


def rich_reply_attachments(reply: ChannelRichReply) -> list:
    """Build attachment payloads for OutboundEnvelope (image preview + optional HTML file)."""
    from .models import ChannelAttachment

    attachments: list[ChannelAttachment] = []
    if reply.preview_image_path is not None and reply.preview_image_bytes:
        attachments.append(
            ChannelAttachment(
                kind="image",
                name=reply.preview_filename,
                mime_type="image/png",
                size=len(reply.preview_image_bytes),
                local_path=str(reply.preview_image_path),
            )
        )
    if reply.html_path is not None and reply.html_url is None and reply.html_bytes:
        if not reply.image_only:
            attachments.append(
                ChannelAttachment(
                    kind="file",
                    name=reply.filename,
                    mime_type="text/html; charset=utf-8",
                    size=len(reply.html_bytes),
                    local_path=str(reply.html_path),
                )
            )
    return attachments


def rich_delivery_failure_text(reply: ChannelRichReply, reason: str = "") -> str:
    """Readable terminal fallback after an HTML attachment/link cannot be delivered."""
    base = channel_visible_text(reply.text, final=True)
    detail = f"：{reason}" if reason else ""
    return f"{base}\n\n（网页发送失败{detail}；原始数据已隐藏）".strip()


def deliver_rich_reply_files(
    *,
    platform: str,
    chat_id: str,
    thread_id: Optional[str],
    token: str,
    reply: ChannelRichReply,
    comment: str,
    file_storage: FileStorage | None,
    file_senders: dict,
    text_senders: dict,
) -> dict[str, Any]:
    """Send preview PNG and/or HTML file before the final text bubble."""
    from ..connectors.file_delivery import deliver_file

    sent_preview = False
    if reply.preview_image_bytes:
        preview = deliver_file(
            platform=platform,
            chat_id=chat_id,
            thread_id=thread_id,
            token=token,
            filename=reply.preview_filename,
            data=reply.preview_image_bytes,
            title="ChemClaw 图表预览",
            comment=None,
            file_storage=file_storage,
            file_senders=file_senders,
            text_senders=text_senders,
        )
        if not preview.ok:
            comment = rich_delivery_failure_text(reply, preview.error or "")
        else:
            sent_preview = True

    if reply.html_url is None and reply.html_bytes and not reply.image_only:
        delivered = deliver_file(
            platform=platform,
            chat_id=chat_id,
            thread_id=thread_id,
            token=token,
            filename=reply.filename,
            data=reply.html_bytes,
            title="ChemClaw 交互图表",
            comment=comment if not sent_preview else None,
            file_storage=file_storage,
            file_senders=file_senders,
            text_senders=text_senders,
        )
        if delivered.ok:
            return {
                "ok": True,
                "message_id": delivered.message_id,
                "delivery": delivered.delivery,
                "preview": sent_preview,
            }
        return {
            "ok": False,
            "error": delivered.error or "send failed",
            "text": rich_delivery_failure_text(reply, delivered.error or ""),
            "preview": sent_preview,
        }
    return {"ok": True, "preview": sent_preview}


def _salvage_chart_markdown(
    raw: str,
    chart_tool_results: list[dict[str, Any]] | None,
) -> str:
    """Append a ```chart block from tool sidecars when the model forgot to emit one."""
    if has_renderer_blocks(raw):
        return raw
    for row in reversed(chart_tool_results or []):
        if not isinstance(row, dict):
            continue
        spec = row.get("chart_spec")
        normalized = normalize_chart_spec_dict(spec)
        if normalized:
            block = json.dumps(normalized, ensure_ascii=False)
            return f"{raw.rstrip()}\n\n```chart\n{block}\n```"
    return raw


def _write_preview_png_bytes(
    data: bytes, workspace: Path | str | None, title: str
) -> Path:
    import tempfile

    base = Path(workspace) if workspace else Path(tempfile.gettempdir()) / "chemclaw-reports"
    base.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", title or "")[:60].strip("_")
    out = base / f"{safe or 'ChemClaw-图表预览'}-preview.png"
    out.write_bytes(data)
    return out


def _html_filename(title: str) -> str:
    safe = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", title or "")[:60].strip("_")
    return f"{safe or 'ChemClaw-交互图表'}.html"


def _write_preview_png(data: bytes, html_path: Path, title: str) -> Path:
    safe = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", title or "")[:60].strip("_")
    out = html_path.with_name(f"{safe or 'ChemClaw-图表预览'}-preview.png")
    out.write_bytes(data)
    return out
