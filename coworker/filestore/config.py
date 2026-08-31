"""COS config loading from SecretStore + prefs (no secrets in prefs)."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Optional
from urllib.parse import urlparse

from ..secrets import SecretStore
from .base import FileStorage, NullFileStorage
from .tencent_cos import TencentCosStorage

FILESTORE_SECRET_PROFILE = "filestore:cos"
DEFAULT_FOLDER = "chemclaw"
DEFAULT_BUCKET = "chemcloud-1304660855"
DEFAULT_REGION = "ap-shanghai"
DEFAULT_PUB_URL = "https://chemcloud-1304660855.cos.ap-shanghai.myqcloud.com/"
_BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
_REGION_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")


@dataclass(frozen=True)
class CosConfig:
    secret_id: str
    secret_key: str
    bucket: str
    region: str
    pub_url: str
    folder: str = DEFAULT_FOLDER
    enabled: bool = True

    def ready(self) -> bool:
        return bool(
            self.enabled
            and self.secret_id.strip()
            and self.secret_key.strip()
            and self.bucket.strip()
            and self.region.strip()
            and self.pub_url.strip()
            and validate_public_config(
                self.bucket, self.region, self.pub_url, self.folder
            ) is None
        )


def validate_public_config(
    bucket: str, region: str, pub_url: str, folder: str
) -> Optional[str]:
    if not _BUCKET_RE.fullmatch(str(bucket or "").strip()):
        return "COS bucket 格式无效"
    if not _REGION_RE.fullmatch(str(region or "").strip()):
        return "COS region 格式无效"
    parsed = urlparse(str(pub_url or "").strip())
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        return "COS 公开 URL 必须是无账号、查询参数或片段的 HTTPS 地址"
    parts = str(folder or "").strip().strip("/").split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return "COS folder 包含非法路径片段"
    return None


def load_cos_config(
    secrets: SecretStore,
    prefs: Optional[dict[str, Any]] = None,
) -> Optional[CosConfig]:
    prefs = prefs or {}
    public = prefs.get("filestore_cos") if isinstance(prefs.get("filestore_cos"), dict) else {}
    enabled = bool(public.get("enabled", True))
    bucket = str(public.get("bucket") or DEFAULT_BUCKET).strip()
    region = str(public.get("region") or DEFAULT_REGION).strip()
    pub_url = str(public.get("pub_url") or DEFAULT_PUB_URL).strip()
    folder = str(public.get("folder") or DEFAULT_FOLDER).strip() or DEFAULT_FOLDER

    creds = secrets.get(FILESTORE_SECRET_PROFILE) or {}
    secret_id = str(creds.get("secret_id") or "").strip()
    secret_key = str(creds.get("secret_key") or "").strip()
    if not secret_id and not secret_key and not public:
        return None
    return CosConfig(
        secret_id=secret_id,
        secret_key=secret_key,
        bucket=bucket,
        region=region,
        pub_url=pub_url,
        folder=folder,
        enabled=enabled,
    )


def load_file_storage(
    secrets: SecretStore,
    prefs: Optional[dict[str, Any]] = None,
) -> FileStorage:
    cfg = load_cos_config(secrets, prefs)
    if cfg is None or not cfg.ready():
        return NullFileStorage()
    return TencentCosStorage(cfg)


def filestore_public_status(
    secrets: SecretStore,
    prefs: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Settings payload — never includes secret values."""
    cfg = load_cos_config(secrets, prefs)
    has_secrets = bool(
        (secrets.get(FILESTORE_SECRET_PROFILE) or {}).get("secret_id")
        and (secrets.get(FILESTORE_SECRET_PROFILE) or {}).get("secret_key")
    )
    public = (prefs or {}).get("filestore_cos") if isinstance((prefs or {}).get("filestore_cos"), dict) else {}
    return {
        "enabled": bool(public.get("enabled", True)) if public or has_secrets else False,
        "configured": bool(cfg and cfg.ready()),
        "has_secrets": has_secrets,
        "bucket": str(public.get("bucket") or DEFAULT_BUCKET),
        "region": str(public.get("region") or DEFAULT_REGION),
        "pub_url": str(public.get("pub_url") or DEFAULT_PUB_URL),
        "folder": str(public.get("folder") or DEFAULT_FOLDER),
        "blurb": "仅在向 Channel 发送文件时上传；本机对话产物默认只保存在本地。",
    }
