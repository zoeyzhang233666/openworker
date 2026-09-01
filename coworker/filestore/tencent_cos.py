"""Tencent COS FileStorage — lazy SDK import."""

from __future__ import annotations

import logging
import mimetypes
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import quote

from .base import FileStorageError
from .models import FileRef
from .paths import (
    DEFAULT_MAX_BYTES,
    build_object_key,
    safe_upload_filename,
    validate_object_key,
    validate_upload_bytes,
)

if TYPE_CHECKING:
    from .config import CosConfig

logger = logging.getLogger("coworker.filestore.cos")


class TencentCosStorage:
    storage_id = "tencent-cos"

    def __init__(self, config: "CosConfig") -> None:
        self.config = config
        self._client: Any = None

    def configured(self) -> bool:
        return self.config.ready()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from qcloud_cos import CosConfig as SdkConfig  # type: ignore
            from qcloud_cos import CosS3Client  # type: ignore
        except ImportError as exc:
            raise FileStorageError(
                "未安装腾讯云 COS SDK。请执行：python -m pip install 'cos-python-sdk-v5==1.9.38' "
                "（或 pip install -e '.[messaging]'），然后重启。"
            ) from exc
        sdk_cfg = SdkConfig(
            Region=self.config.region,
            SecretId=self.config.secret_id,
            SecretKey=self.config.secret_key,
            Scheme="https",
        )
        self._client = CosS3Client(sdk_cfg)
        return self._client

    def public_url_for_key(self, key: str) -> str:
        base = self.config.pub_url.rstrip("/")
        return f"{base}/{quote(validate_object_key(key), safe='/')}"

    def upload(
        self,
        data: bytes,
        *,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> FileRef:
        if not self.configured():
            raise FileStorageError("腾讯云 COS 配置不完整，请检查密钥与桶设置")
        name = safe_upload_filename(filename)
        validate_upload_bytes(data, name)
        digest = hashlib.sha256(data).hexdigest()
        key = build_object_key(
            self.config.folder,
            name,
            now=datetime.now(timezone.utc),
            unique=digest[:24],
        )
        client = self._get_client()
        ctype = content_type or "application/octet-stream"
        # D-195: HTML reports must open inline in WeCom/browser, not force download.
        if ctype.startswith("text/html") or name.lower().endswith((".html", ".htm")):
            disposition = f"inline; filename*=UTF-8''{quote(name)}"
            if not ctype.startswith("text/html"):
                ctype = "text/html; charset=utf-8"
        else:
            disposition = f"attachment; filename*=UTF-8''{quote(name)}"
        try:
            client.put_object(
                Bucket=self.config.bucket,
                Body=data,
                Key=key,
                ContentType=ctype,
                ContentDisposition=disposition,
                Metadata={"sha256": digest},
                EnableMD5=True,
            )
        except FileStorageError:
            raise
        except Exception as exc:
            logger.warning("cos upload failed: %s", type(exc).__name__)
            raise FileStorageError(
                f"上传到腾讯云 COS 失败（{type(exc).__name__}）。请检查网络、桶权限与密钥。"
            ) from exc
        url = self.public_url_for_key(key)
        return FileRef(
            storage_id=self.storage_id,
            key=key,
            filename=name,
            url=url,
            content_type=ctype,
            size=len(data),
            sha256=digest,
        )

    def upload_path(self, path: Path, *, content_type: Optional[str] = None) -> FileRef:
        path = Path(path)
        if path.is_symlink() or not path.is_file():
            raise FileStorageError("文件不存在或不是普通文件")
        data = path.read_bytes()
        guessed, _ = mimetypes.guess_type(path.name)
        return self.upload(
            data,
            filename=path.name,
            content_type=content_type or guessed or "application/octet-stream",
        )

    def public_url(self, ref: FileRef) -> str:
        return ref.url or self.public_url_for_key(ref.key)

    def exists(self, ref: FileRef) -> bool:
        if not self.configured():
            return False
        try:
            client = self._get_client()
            return bool(client.object_exists(Bucket=self.config.bucket, Key=ref.key))
        except Exception:
            return False

    def download(self, ref: FileRef) -> bytes:
        if not self.configured():
            raise FileStorageError("腾讯云 COS 配置不完整，无法读取云文件")
        if ref.storage_id not in {self.storage_id, ""}:
            raise FileStorageError("FileRef 不属于当前腾讯云 COS 存储")
        key = validate_object_key(ref.key)
        try:
            response = self._get_client().get_object(
                Bucket=self.config.bucket, Key=key
            )
            body = response.get("Body") if isinstance(response, dict) else None
            if body is None:
                raise FileStorageError("腾讯云 COS 未返回文件内容")
            stream = body.get_raw_stream() if hasattr(body, "get_raw_stream") else body
            data = stream.read(DEFAULT_MAX_BYTES + 1)
        except FileStorageError:
            raise
        except Exception as exc:
            logger.warning("cos download failed: %s", type(exc).__name__)
            raise FileStorageError(
                f"从腾讯云 COS 读取文件失败（{type(exc).__name__}）"
            ) from exc
        if len(data) > DEFAULT_MAX_BYTES:
            raise FileStorageError("云文件超过 50 MB 限制")
        if ref.size and len(data) != ref.size:
            raise FileStorageError("云文件大小与 FileRef 不一致")
        if ref.sha256 and hashlib.sha256(data).hexdigest() != ref.sha256:
            raise FileStorageError("云文件完整性校验失败")
        return data
