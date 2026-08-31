"""Object key helpers and upload safety checks."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from ..channels.media import safe_filename
from .base import FileStorageError

DEFAULT_MAX_BYTES = 50 * 1024 * 1024
_ALLOWED_EXTENSIONS = frozenset(
    {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".tsv",
        ".txt", ".md", ".json", ".png", ".jpg", ".jpeg", ".gif",
        ".webp", ".bmp", ".ppt", ".pptx", ".zip", ".html", ".htm", ".svg",
    }
)
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def safe_upload_filename(name: str) -> str:
    return safe_filename(name, fallback="file")


def validate_upload_bytes(data: bytes, filename: str, *, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    if not isinstance(data, (bytes, bytearray)):
        raise FileStorageError("文件内容无效")
    if len(data) <= 0:
        raise FileStorageError("不能上传空文件")
    if len(data) > max_bytes:
        raise FileStorageError("文件超过 50 MB 限制")
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise FileStorageError(f"不允许上传此文件类型：{ext or '无扩展名'}")


def build_object_key(
    folder: str,
    filename: str,
    *,
    now: datetime | None = None,
    unique: str,
) -> str:
    folder = (folder or "chemclaw").strip().strip("/")
    folder = _CONTROL_RE.sub("", folder) or "chemclaw"
    # Reject path traversal in folder segments.
    parts = [p for p in folder.split("/") if p and p not in {".", ".."}]
    folder = "/".join(parts) or "chemclaw"
    name = safe_upload_filename(filename)
    stamp = now or datetime.now(timezone.utc)
    return f"{folder}/{stamp:%Y}/{stamp:%m}/{unique}_{name}"


def validate_object_key(key: str) -> str:
    value = str(key or "").strip().lstrip("/")
    if not value or _CONTROL_RE.search(value):
        raise FileStorageError("FileRef 对象键无效")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise FileStorageError("FileRef 对象键包含非法路径片段")
    return value
