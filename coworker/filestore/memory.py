"""In-memory FileStorage for tests."""

from __future__ import annotations

import mimetypes
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from .base import FileStorageError
from .models import FileRef
from .paths import build_object_key, safe_upload_filename, validate_upload_bytes


class MemoryFileStorage:
    storage_id = "memory"

    def __init__(self, *, pub_url: str = "https://example.test/", folder: str = "chemclaw"):
        self.pub_url = pub_url.rstrip("/") + "/"
        self.folder = folder.strip("/") or "chemclaw"
        self.objects: dict[str, bytes] = {}

    def configured(self) -> bool:
        return True

    def upload(
        self,
        data: bytes,
        *,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> FileRef:
        name = safe_upload_filename(filename)
        validate_upload_bytes(data, name)
        now = datetime.now(timezone.utc)
        digest = hashlib.sha256(data).hexdigest()
        key = build_object_key(self.folder, name, now=now, unique=digest[:24])
        self.objects[key] = data
        url = f"{self.pub_url.rstrip('/')}/{quote(key, safe='/')}"
        return FileRef(
            storage_id=self.storage_id,
            key=key,
            filename=name,
            url=url,
            content_type=content_type or "application/octet-stream",
            size=len(data),
            sha256=digest,
        )

    def upload_path(self, path: Path, *, content_type: Optional[str] = None) -> FileRef:
        path = Path(path)
        if not path.is_file():
            raise FileStorageError("文件不存在或无法读取")
        data = path.read_bytes()
        guessed, _ = mimetypes.guess_type(path.name)
        return self.upload(
            data,
            filename=path.name,
            content_type=content_type or guessed or "application/octet-stream",
        )

    def public_url(self, ref: FileRef) -> str:
        return ref.url or f"{self.pub_url.rstrip('/')}/{quote(ref.key, safe='/')}"

    def exists(self, ref: FileRef) -> bool:
        return ref.key in self.objects

    def download(self, ref: FileRef) -> bytes:
        try:
            data = self.objects[ref.key]
        except KeyError as exc:
            raise FileStorageError("云文件不存在或已被清理") from exc
        if ref.sha256 and hashlib.sha256(data).hexdigest() != ref.sha256:
            raise FileStorageError("云文件完整性校验失败")
        return data
