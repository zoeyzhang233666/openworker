"""File-backed market cache. Never writes into the git workspace."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from coworker.secrets import state_dir

Clock = Callable[[], datetime]

TTL_SECONDS = {
    "quote": 15,
    "minute": 120,
    "daily": 7 * 86400,
    "event": 14 * 86400,
    "statement": 30 * 86400,
    "calendar": 90 * 86400,
}


def ttl_for(dataset_kind: str) -> int:
    try:
        return TTL_SECONDS[dataset_kind]
    except KeyError as exc:
        raise KeyError(f"unknown cache dataset_kind: {dataset_kind}") from exc


def default_cache_root() -> Path:
    return state_dir() / "cn_market" / "cache"


@dataclass(frozen=True)
class CacheKey:
    domain: str
    symbol: str
    dataset: str
    interval: str = ""
    adjustment: str = ""
    source_version: str = "1"

    def digest(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class CacheHit:
    payload: Any
    stored_at: datetime
    ttl_seconds: int
    fresh: bool


class MarketCache:
    def __init__(
        self,
        *,
        root: Optional[Path] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self.root = Path(root) if root is not None else default_cache_root()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _path(self, key: CacheKey) -> Path:
        return self.root / key.domain / f"{key.digest()}.json"

    def get(self, key: CacheKey) -> Optional[CacheHit]:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        stored_at = datetime.fromisoformat(raw["stored_at"])
        ttl_seconds = int(raw["ttl_seconds"])
        now = self._clock()
        if stored_at.tzinfo is None:
            stored_at = stored_at.replace(tzinfo=timezone.utc)
        age = (now - stored_at).total_seconds()
        return CacheHit(
            payload=raw.get("payload"),
            stored_at=stored_at,
            ttl_seconds=ttl_seconds,
            fresh=age <= ttl_seconds,
        )

    def put(self, key: CacheKey, payload: Any, *, dataset_kind: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "key": asdict(key),
            "payload": payload,
            "stored_at": self._clock().isoformat(),
            "ttl_seconds": ttl_for(dataset_kind),
        }
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
