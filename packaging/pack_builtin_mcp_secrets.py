#!/usr/bin/env python3
"""Encode packaging/builtin_mcp.secrets.json into an obfuscated bundle.

Writes:
  - packaging/builtin_mcp.bundle
  - coworker/mcp/builtin_mcp.bundle  (picked up by PyInstaller datas / source runs)

Never commit the secrets JSON or the bundle. Example file is safe to commit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from coworker.mcp.builtin import encode_secrets_file  # noqa: E402


def main() -> int:
    secrets_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "packaging" / "builtin_mcp.secrets.json"
    if not secrets_path.is_file():
        print(f"missing secrets file: {secrets_path}", file=sys.stderr)
        return 1
    raw = json.loads(secrets_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        print("secrets file must be a JSON object", file=sys.stderr)
        return 1
    blob = encode_secrets_file(raw)
    targets = [
        ROOT / "packaging" / "builtin_mcp.bundle",
        ROOT / "coworker" / "mcp" / "builtin_mcp.bundle",
    ]
    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(blob, encoding="utf-8")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
