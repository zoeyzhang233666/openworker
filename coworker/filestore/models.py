"""Stable FileRef value object — no SDK types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import time
from typing import Any, Optional


@dataclass(frozen=True)
class FileRef:
    storage_id: str
    key: str
    filename: str
    url: str
    content_type: str = "application/octet-stream"
    size: int = 0
    sha256: str = ""
    created_at: float = field(default_factory=time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileRef":
        return cls(
            storage_id=str(data.get("storage_id") or ""),
            key=str(data.get("key") or ""),
            filename=str(data.get("filename") or ""),
            url=str(data.get("url") or ""),
            content_type=str(data.get("content_type") or "application/octet-stream"),
            size=int(data.get("size") or 0),
            sha256=str(data.get("sha256") or ""),
            created_at=float(data.get("created_at") or time()),
        )
