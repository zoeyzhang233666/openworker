"""Secure inbound/outbound Channel media handling (D-193).

Platform adapters own authentication and transport. This module owns every local-file
decision: names, roots, type/size checks, symlink rejection, session import and TTL.
"""

from __future__ import annotations

import asyncio
import base64
import mimetypes
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from .models import ChannelAttachment, InboundEnvelope

DEFAULT_MAX_INBOUND_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_OUTBOUND_BYTES = 50 * 1024 * 1024
DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60

_ALLOWED_EXTENSIONS = frozenset(
    {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".tsv",
        ".txt", ".md", ".json", ".png", ".jpg", ".jpeg", ".gif",
        ".webp", ".bmp", ".ppt", ".pptx", ".zip", ".mp3", ".wav",
        ".m4a", ".opus", ".silk", ".mp4",
    }
)
_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})
_TEXT_EXTENSIONS = frozenset({".txt", ".md", ".csv", ".tsv", ".json"})
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SAFE_ROUTE_RE = re.compile(r"[^\w.-]+", re.UNICODE)


class ChannelMediaError(ValueError):
    pass


def safe_filename(name: str, *, fallback: str = "attachment") -> str:
    name = Path(str(name or fallback).replace("\\", "/")).name
    name = _CONTROL_RE.sub("", name).strip().strip(".")
    if not name:
        name = fallback
    # Windows reserved trailing dots/spaces are removed; Chinese names remain intact.
    name = name.rstrip(" .") or fallback
    return name[:180]


def _route_component(value: str, fallback: str) -> str:
    out = _SAFE_ROUTE_RE.sub("_", str(value or "").strip()).strip("._")
    return (out or fallback)[:80]


def _assert_regular_nonlink(path: Path) -> Path:
    if path.is_symlink():
        raise ChannelMediaError("拒绝符号链接文件")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ChannelMediaError("文件不存在或无法读取") from exc
    if not resolved.is_file():
        raise ChannelMediaError("目标不是普通文件")
    return resolved


def _sniff_mime(data: bytes, name: str) -> str:
    head = data[:16]
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:6] in {b"GIF87a", b"GIF89a"}:
        return "image/gif"
    if head.startswith(b"PK\x03\x04"):
        return "application/zip"
    guessed, _ = mimetypes.guess_type(name)
    return guessed or "application/octet-stream"


def _validate_type(name: str, data: bytes, declared_mime: str = "") -> tuple[str, str]:
    ext = Path(name).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ChannelMediaError(f"不支持的文件类型：{ext or '无扩展名'}")
    sniffed = _sniff_mime(data, name)
    declared = str(declared_mime or "").split(";", 1)[0].strip().lower()
    head = data[:16]
    if ext == ".pdf" and not head.startswith(b"%PDF-"):
        raise ChannelMediaError("文件扩展名为 PDF，但内容不是 PDF")
    image_magic = (
        head.startswith(b"\x89PNG\r\n\x1a\n")
        or head.startswith(b"\xff\xd8\xff")
        or head[:6] in {b"GIF87a", b"GIF89a"}
        or (head.startswith(b"RIFF") and data[8:12] == b"WEBP")
        or head.startswith(b"BM")
    )
    if ext in _IMAGE_EXTENSIONS and not image_magic:
        raise ChannelMediaError("图片扩展名与文件内容不一致")
    if declared:
        declared_family = declared.split("/", 1)[0]
        sniffed_family = sniffed.split("/", 1)[0]
        if declared_family in {"image", "audio", "video"} and declared_family != sniffed_family:
            raise ChannelMediaError("平台 MIME 与文件内容不一致")
    return ext, sniffed if sniffed != "application/zip" else (declared or sniffed)


Downloader = Callable[[ChannelAttachment], Awaitable[Any]]


class ChannelMediaManager:
    def __init__(
        self,
        spool_root: str | Path,
        *,
        max_inbound_bytes: int = DEFAULT_MAX_INBOUND_BYTES,
        max_outbound_bytes: int = DEFAULT_MAX_OUTBOUND_BYTES,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.spool_root = Path(spool_root).expanduser().resolve()
        self.spool_root.mkdir(parents=True, exist_ok=True)
        self.max_inbound_bytes = max_inbound_bytes
        self.max_outbound_bytes = max_outbound_bytes
        self.ttl_seconds = ttl_seconds

    def _destination(self, envelope: InboundEnvelope, name: str) -> Path:
        root = self.spool_root
        for value, fallback in (
            (envelope.platform, "channel"),
            (envelope.account_id, "default"),
            (envelope.conversation_id, "conversation"),
            (envelope.message_id, "message"),
        ):
            root = root / _route_component(value, fallback)
        root.mkdir(parents=True, exist_ok=True)
        dest = root / safe_filename(name)
        candidate = dest
        index = 1
        while candidate.exists():
            candidate = dest.with_name(f"{dest.stem}-{index}{dest.suffix}")
            index += 1
        return candidate

    def store_bytes(
        self,
        envelope: InboundEnvelope,
        attachment: ChannelAttachment,
        data: bytes,
        *,
        name: str = "",
        mime_type: str = "",
    ) -> ChannelAttachment:
        if not isinstance(data, (bytes, bytearray)):
            raise ChannelMediaError("平台没有返回可用的文件数据")
        payload = bytes(data)
        if len(payload) > self.max_inbound_bytes:
            raise ChannelMediaError(
                f"附件超过 {self.max_inbound_bytes // (1024 * 1024)} MB 限制"
            )
        filename = safe_filename(name or attachment.name)
        _ext, detected = _validate_type(filename, payload, mime_type or attachment.mime_type)
        dest = self._destination(envelope, filename)
        dest.write_bytes(payload)
        attachment.name = dest.name
        attachment.mime_type = detected
        attachment.size = len(payload)
        attachment.local_path = str(dest)
        return attachment

    async def materialize(
        self, envelope: InboundEnvelope, downloader: Downloader
    ) -> list[str]:
        errors: list[str] = []
        for attachment in envelope.attachments:
            if attachment.local_path:
                try:
                    path = _assert_regular_nonlink(Path(attachment.local_path))
                    if path.stat().st_size > self.max_inbound_bytes:
                        raise ChannelMediaError("附件超过大小限制")
                    attachment.local_path = str(path)
                    attachment.size = path.stat().st_size
                except ChannelMediaError as exc:
                    attachment.local_path = ""
                    errors.append(f"{attachment.name or '附件'}：{exc}")
                continue
            try:
                result = await downloader(attachment)
                result_name = attachment.name
                result_mime = attachment.mime_type
                if isinstance(result, tuple):
                    parts = result
                    if len(parts) >= 2:
                        result_name, result = str(parts[0] or result_name), parts[1]
                    if len(parts) >= 3:
                        result_mime = str(parts[2] or result_mime)
                if isinstance(result, Path):
                    result = await asyncio.to_thread(result.read_bytes)
                self.store_bytes(
                    envelope, attachment, result, name=result_name, mime_type=result_mime
                )
            except Exception as exc:
                attachment.local_path = ""
                errors.append(f"{attachment.name or '附件'}：{exc}")
        return errors

    def import_into_workspace(
        self, attachments: list[ChannelAttachment], workspace: str | Path
    ) -> list[ChannelAttachment]:
        root = Path(workspace).expanduser().resolve() / "._chemclaw" / "inbound"
        root.mkdir(parents=True, exist_ok=True)
        out: list[ChannelAttachment] = []
        for attachment in attachments:
            if not attachment.local_path:
                out.append(attachment)
                continue
            src = _assert_regular_nonlink(Path(attachment.local_path))
            if src.stat().st_size > self.max_inbound_bytes:
                raise ChannelMediaError("附件超过大小限制")
            name = safe_filename(attachment.name or src.name)
            dest = root / name
            index = 1
            while dest.exists() and not os.path.samefile(src, dest):
                dest = root / f"{Path(name).stem}-{index}{Path(name).suffix}"
                index += 1
            if not dest.exists():
                shutil.copy2(src, dest)
            attachment.local_path = str(dest.resolve())
            attachment.name = dest.name
            attachment.size = dest.stat().st_size
            out.append(attachment)
        return out

    def prompt_parts(
        self, text: str, attachments: list[ChannelAttachment], workspace: str | Path
    ) -> tuple[str, list[dict[str, Any]]]:
        """Return framed text plus GUI-compatible image/PDF/text attachment parts."""
        imported = self.import_into_workspace(attachments, workspace)
        prompt_attachments: list[dict[str, Any]] = []
        refs: list[str] = []
        root = Path(workspace).expanduser().resolve()
        for attachment in imported:
            if not attachment.local_path:
                refs.append(f"[附件下载失败：{attachment.name or attachment.remote_ref}]")
                continue
            path = _assert_regular_nonlink(Path(attachment.local_path))
            try:
                rel = path.relative_to(root)
                display_path = str(rel)
            except ValueError:
                display_path = str(path)
            suffix = path.suffix.lower()
            data = path.read_bytes()
            if suffix in _IMAGE_EXTENSIONS and len(data) <= 9 * 1024 * 1024:
                mime = attachment.mime_type or _sniff_mime(data, path.name)
                prompt_attachments.append(
                    {
                        "kind": "image",
                        "name": path.name,
                        "mime": mime,
                        "data_url": f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}",
                    }
                )
            elif suffix == ".pdf" and len(data) <= 10 * 1024 * 1024:
                prompt_attachments.append(
                    {
                        "kind": "pdf",
                        "name": path.name,
                        "mime": "application/pdf",
                        "data_url": "data:application/pdf;base64,"
                        + base64.b64encode(data).decode("ascii"),
                    }
                )
            elif suffix in _TEXT_EXTENSIONS and len(data) <= 200_000:
                prompt_attachments.append(
                    {
                        "kind": "text",
                        "name": path.name,
                        "mime": attachment.mime_type or _sniff_mime(data, path.name),
                        "text": data.decode("utf-8", errors="replace"),
                    }
                )
            refs.append(f"[Channel 附件已保存：{display_path}]")
            if attachment.file_ref:
                storage_id = str(attachment.file_ref.get("storage_id") or "cloud")
                key = str(attachment.file_ref.get("key") or "")
                if key:
                    refs.append(f"[Channel 附件 FileRef：{storage_id}:{key}]")
        framed = "\n".join([text.strip(), *refs]).strip()
        return framed, prompt_attachments

    def resolve_outbound(self, path: str, roots: list[str | Path]) -> Path:
        bases = [Path(root).expanduser().resolve() for root in roots]
        raw = Path(path).expanduser()
        candidates = [raw] if raw.is_absolute() else [base / raw for base in bases]
        for candidate in candidates:
            if candidate.is_symlink():
                continue
            try:
                resolved = _assert_regular_nonlink(candidate)
            except ChannelMediaError:
                continue
            if not any(_within(resolved, base) for base in bases):
                continue
            size = resolved.stat().st_size
            if size > self.max_outbound_bytes:
                raise ChannelMediaError(
                    f"文件超过 {self.max_outbound_bytes // (1024 * 1024)} MB 限制"
                )
            data = resolved.read_bytes()[:64]
            _validate_type(resolved.name, data, mimetypes.guess_type(resolved.name)[0] or "")
            return resolved
        raise ChannelMediaError("文件不在当前工作区/产物目录中，或不是普通文件")

    def cleanup_expired(self, *, now: Optional[float] = None) -> int:
        cutoff = (time.time() if now is None else now) - self.ttl_seconds
        removed = 0
        for path in self.spool_root.rglob("*"):
            try:
                if path.is_file() and not path.is_symlink() and path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
            except OSError:
                continue
        for path in sorted(self.spool_root.rglob("*"), reverse=True):
            try:
                if path.is_dir() and not any(path.iterdir()):
                    path.rmdir()
            except OSError:
                pass
        return removed


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
