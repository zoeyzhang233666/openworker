"""FileStorage protocol and null implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from .models import FileRef


class FileStorageError(ValueError):
    """User-facing storage failure (Chinese message, no credentials)."""


@runtime_checkable
class FileStorage(Protocol):
    storage_id: str

    def configured(self) -> bool: ...

    def upload(
        self,
        data: bytes,
        *,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> FileRef: ...

    def upload_path(self, path: Path, *, content_type: Optional[str] = None) -> FileRef: ...

    def public_url(self, ref: FileRef) -> str: ...

    def exists(self, ref: FileRef) -> bool: ...

    def download(self, ref: FileRef) -> bytes: ...


class NullFileStorage:
    """Present when COS is not configured — local chat stays unaffected."""

    storage_id = "null"

    def configured(self) -> bool:
        return False

    def upload(
        self,
        data: bytes,
        *,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> FileRef:
        raise FileStorageError(
            "未配置腾讯云 COS 云文件存储。请在设置中填写桶与密钥后，再向 Telegram/企业微信等发送文件。"
        )

    def upload_path(self, path: Path, *, content_type: Optional[str] = None) -> FileRef:
        raise FileStorageError(
            "未配置腾讯云 COS 云文件存储。请在设置中填写桶与密钥后，再向 Telegram/企业微信等发送文件。"
        )

    def public_url(self, ref: FileRef) -> str:
        return ref.url

    def exists(self, ref: FileRef) -> bool:
        return False

    def download(self, ref: FileRef) -> bytes:
        raise FileStorageError("未配置云文件存储，无法读取 FileRef")
