"""Read-only source identity; frozen apps use a stamp captured during packaging."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

RUNTIME_REVISION = "2026-09-26.1"


def source_build_identity(root: Path | None = None) -> dict:
    root = root or Path(__file__).resolve().parent.parent
    info = {"runtime_revision": RUNTIME_REVISION, "source_commit": "unknown", "source_dirty": None}
    try:
        opts = dict(cwd=root, timeout=5, stderr=subprocess.DEVNULL,
                    creationflags=0x08000000 if sys.platform == "win32" else 0)
        info["source_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], **opts).decode().strip()
        diff = subprocess.check_output(["git", "diff", "HEAD", "--", "coworker", "surfaces/gui/src", "packaging"], **opts)
        info["source_dirty"] = bool(diff)
        info["source_diff_sha256"] = hashlib.sha256(diff).hexdigest()
    except (OSError, subprocess.SubprocessError):
        pass
    return info


@lru_cache(maxsize=1)
def build_identity() -> dict:
    if getattr(sys, "frozen", False):
        try:
            return json.loads((Path(sys._MEIPASS) / "build-info.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"runtime_revision": RUNTIME_REVISION, "source_commit": "unknown", "source_dirty": None}
    return source_build_identity()


def write_build_stamp(destination: Path, root: Path) -> None:
    info = source_build_identity(root)
    info["built_at"] = datetime.now(timezone.utc).isoformat()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
