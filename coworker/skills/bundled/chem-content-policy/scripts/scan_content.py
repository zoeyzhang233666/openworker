#!/usr/bin/env python3
"""Deterministic lexicon scanner for chem-content-policy (M3: managed + user)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


RULE_SET_ID = "chem-content-policy"

_LEXICON_DIR = Path(__file__).resolve().parent.parent / "references" / "lexicon"
DEFAULT_MANAGED_LEXICON = _LEXICON_DIR / "managed" / "base.csv"
DEFAULT_USER_LEXICON = _LEXICON_DIR / "user.csv"
DEFAULT_RULE_VERSION_FILE = _LEXICON_DIR / "managed" / "rule_version.txt"
# Pre-M3 single-file layout (installed copies may still have this).
_LEGACY_LEXICON = _LEXICON_DIR / "base.csv"

_FIELDNAMES = (
    "rule_id",
    "term",
    "platform",
    "locale",
    "category",
    "severity",
    "action",
    "replacement_strategy",
    "notes",
)

# Back-compat alias used by older callers / docs.
DEFAULT_LEXICON = DEFAULT_MANAGED_LEXICON


def load_lexicon(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_rule_version(version_file: Path | None = None, *, managed_csv: Path | None = None) -> str:
    """Read managed rule_version.txt; fall back to sibling of managed CSV."""
    candidates: list[Path] = []
    if version_file is not None:
        candidates.append(version_file)
    if managed_csv is not None:
        candidates.append(managed_csv.parent / "rule_version.txt")
    candidates.append(DEFAULT_RULE_VERSION_FILE)
    for path in candidates:
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return text
    return "0.0.0"


def resolve_managed_lexicon(lexicon_path: str | Path | None = None) -> Path:
    if lexicon_path is not None:
        return Path(lexicon_path)
    if DEFAULT_MANAGED_LEXICON.is_file():
        return DEFAULT_MANAGED_LEXICON
    if _LEGACY_LEXICON.is_file():
        return _LEGACY_LEXICON
    return DEFAULT_MANAGED_LEXICON


def merge_lexicon_rows(
    managed_rows: list[dict[str, str]],
    user_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Merge managed + user: same rule_id → user wins; action=suppress drops the rule."""
    by_id: dict[str, dict[str, str]] = {}
    extras: list[dict[str, str]] = []

    for row in managed_rows:
        rid = (row.get("rule_id") or "").strip()
        if rid:
            by_id[rid] = dict(row)
        else:
            extras.append(dict(row))

    for row in user_rows:
        rid = (row.get("rule_id") or "").strip()
        action = (row.get("action") or "").strip().lower()
        if action == "suppress":
            if rid:
                by_id.pop(rid, None)
            continue
        if rid:
            by_id[rid] = dict(row)
        else:
            extras.append(dict(row))

    return list(by_id.values()) + extras


def scan_content(
    text: str,
    *,
    lexicon_path: str | Path | None = None,
    lexicon_user: str | Path | None = None,
    platform: str | None = None,
    rule_version: str | None = None,
) -> dict[str, Any]:
    managed_path = resolve_managed_lexicon(lexicon_path)
    if lexicon_user is not None:
        user_path = Path(lexicon_user)
    elif lexicon_path is not None:
        # Explicit managed-only path (tests / one-off): do not auto-merge skill user.csv
        # unless caller passes lexicon_user.
        user_path = None
    else:
        user_path = DEFAULT_USER_LEXICON

    managed_rows = load_lexicon(managed_path)
    user_rows = load_lexicon(user_path) if user_path is not None else []
    rows = merge_lexicon_rows(managed_rows, user_rows)

    version = rule_version or read_rule_version(managed_csv=managed_path)

    hits: list[dict[str, str]] = []
    for row in rows:
        term = (row.get("term") or "").strip()
        if not term or term not in text:
            continue
        row_platform = (row.get("platform") or "all").strip()
        if platform and row_platform not in ("all", platform):
            continue
        hits.append(
            {
                "rule_id": row.get("rule_id", ""),
                "term": term,
                "platform": row_platform,
                "locale": row.get("locale", ""),
                "category": row.get("category", ""),
                "severity": row.get("severity", "warning"),
                "action": row.get("action", "review"),
                "replacement_strategy": row.get("replacement_strategy", ""),
                "notes": row.get("notes", ""),
            }
        )
    blocked = any(h.get("severity") == "block" for h in hits)
    return {
        "schema_version": "chemclaw.content-scan.v1",
        "rule_set": {"id": RULE_SET_ID, "version": version},
        "hit_count": len(hits),
        "blocked": blocked,
        "hits": hits,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan text against content lexicon")
    parser.add_argument("--text", default="")
    parser.add_argument("--text-file", type=Path)
    parser.add_argument("--lexicon", type=Path, default=None)
    parser.add_argument("--lexicon-user", type=Path, default=None)
    parser.add_argument("--platform", default="")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if args.text_file:
        text = args.text_file.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    result = scan_content(
        text,
        lexicon_path=args.lexicon,
        lexicon_user=args.lexicon_user,
        platform=args.platform or None,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 2 if result["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
