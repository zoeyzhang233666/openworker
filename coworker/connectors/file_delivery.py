"""Channel file delivery matrix (D-194).

Always prefer a FileRef when cloud storage is configured. Native platform upload
is used when registered and successful; otherwise send the public COS URL.
"""

from __future__ import annotations

from dataclasses import dataclass
import mimetypes
from typing import Any, Callable, Optional

from ..filestore.base import FileStorage, FileStorageError, NullFileStorage
from ..filestore.models import FileRef
from .base import SendResult
from .senders import DEFAULT_FILE_SENDERS, DEFAULT_SENDERS, FileSender, Sender

# Platforms without a reliable native FileSender — COS URL is the primary path.
URL_PRIMARY_PLATFORMS = frozenset({"telegram"})
# Try native attachment first; fall back to URL on failure.
NATIVE_PREFERRED_PLATFORMS = frozenset(
    {"slack", "wecom", "feishu", "dingtalk", "weixin"}
)


@dataclass
class DeliveryResult:
    ok: bool
    delivery: str = ""  # native | cos_url
    message_id: Optional[str] = None
    error: Optional[str] = None
    file_ref: Optional[FileRef] = None
    warning: Optional[str] = None


def format_cos_url_message(
    *,
    filename: str,
    url: str,
    title: Optional[str] = None,
    comment: Optional[str] = None,
) -> str:
    head = (title or filename or "文件").strip()
    parts = [f"📎 {head}", url]
    if comment and comment.strip():
        parts.insert(1, comment.strip())
    return "\n".join(parts)


def deliver_file(
    *,
    platform: str,
    chat_id: str,
    thread_id: Optional[str],
    token: str,
    filename: str,
    data: bytes,
    title: Optional[str] = None,
    comment: Optional[str] = None,
    file_storage: Optional[FileStorage] = None,
    file_senders: Optional[dict[str, FileSender]] = None,
    text_senders: Optional[dict[str, Sender]] = None,
) -> DeliveryResult:
    """Upload to FileStorage when needed, then deliver via native or COS URL."""
    file_senders = file_senders if file_senders is not None else DEFAULT_FILE_SENDERS
    text_senders = text_senders if text_senders is not None else DEFAULT_SENDERS
    storage = file_storage or NullFileStorage()

    needs_url = platform in URL_PRIMARY_PLATFORMS or platform not in file_senders
    prefer_native = platform in NATIVE_PREFERRED_PLATFORMS and platform in file_senders

    file_ref: Optional[FileRef] = None
    storage_warning: Optional[str] = None
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    if storage.configured() and (needs_url or prefer_native):
        try:
            file_ref = storage.upload(
                data, filename=filename, content_type=content_type
            )
        except FileStorageError as exc:
            if needs_url and not prefer_native:
                return DeliveryResult(False, error=str(exc))
            # Native-preferred platforms can still try without COS.
            file_ref = None
            storage_warning = str(exc)
        except Exception as exc:
            if needs_url and not prefer_native:
                return DeliveryResult(
                    False, error=f"云文件上传失败（{type(exc).__name__}）"
                )
            file_ref = None
            storage_warning = f"云文件上传失败（{type(exc).__name__}）"

    if needs_url and not prefer_native:
        if file_ref is None:
            if not storage.configured():
                return DeliveryResult(
                    False,
                    error=(
                        "该平台需要通过腾讯云 COS 发送文件链接，但尚未配置云文件存储。"
                        "请在设置中配置 COS 后重试。"
                    ),
                )
            return DeliveryResult(False, error="云文件上传未返回可用链接")
        return _send_url(
            platform=platform,
            token=token,
            chat_id=chat_id,
            thread_id=thread_id,
            filename=filename,
            file_ref=file_ref,
            title=title,
            comment=comment,
            text_senders=text_senders,
        )

    # Native preferred (or wecom dual-try when native is also registered).
    if platform in file_senders:
        # WeCom: try native first even though URL is also a supported path.
        native = file_senders[platform](
            token, chat_id, thread_id, filename, data, title, comment
        )
        if native.ok:
            return DeliveryResult(
                True,
                delivery="native",
                message_id=native.message_id,
                file_ref=file_ref,
                warning=storage_warning,
            )
        # Fall through to URL if we have a ref or can upload now.
        if file_ref is None and storage.configured():
            try:
                file_ref = storage.upload(
                    data, filename=filename, content_type=content_type
                )
            except FileStorageError as exc:
                return DeliveryResult(
                    False,
                    error=(
                        f"平台原生发送失败：{native.error or '未知错误'}；"
                        f"云文件降级也失败：{exc}"
                    ),
                )
        if file_ref is not None:
            url_result = _send_url(
                platform=platform,
                token=token,
                chat_id=chat_id,
                thread_id=thread_id,
                filename=filename,
                file_ref=file_ref,
                title=title,
                comment=comment
                or f"（原生附件发送失败，已改为链接：{native.error or '未知错误'}）",
                text_senders=text_senders,
            )
            if url_result.ok:
                return url_result
            return DeliveryResult(
                False,
                error=(
                    f"平台原生发送失败：{native.error or '未知错误'}；"
                    f"链接降级也失败：{url_result.error or '未知错误'}"
                ),
            )
        return DeliveryResult(
            False,
            error=(
                f"平台原生发送失败：{native.error or '未知错误'}。"
                "请配置腾讯云 COS 以通过链接降级发送。"
            ),
        )

    return DeliveryResult(False, error=f"{platform} 尚不支持发送文件")


def _send_url(
    *,
    platform: str,
    token: str,
    chat_id: str,
    thread_id: Optional[str],
    filename: str,
    file_ref: FileRef,
    title: Optional[str],
    comment: Optional[str],
    text_senders: dict[str, Sender],
) -> DeliveryResult:
    sender = text_senders.get(platform)
    if sender is None:
        return DeliveryResult(False, error=f"{platform} 无法发送文本链接")
    text = format_cos_url_message(
        filename=filename, url=file_ref.url, title=title, comment=comment
    )
    result = sender(token, chat_id, text, thread_id)
    if result.ok:
        return DeliveryResult(
            True,
            delivery="cos_url",
            message_id=result.message_id,
            file_ref=file_ref,
        )
    return DeliveryResult(
        False,
        error=result.error or "发送文件链接失败",
        file_ref=file_ref,
    )
