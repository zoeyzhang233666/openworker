#!/usr/bin/env python3
"""Deterministic lexicon scanner for chem-content-policy."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_LEXICON = (
    Path(__file__).resolve().parent.parent / "references" / "lexicon" / "base.csv"
)


def load_lexicon(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def scan_content(
    text: str,
    *,
    lexicon_path: str | Path | None = None,
    platform: str | None = None,
) -> dict[str, Any]:
    path = Path(lexicon_path) if lexicon_path else DEFAULT_LEXICON
    rows = load_lexicon(path)
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
        "hit_count": len(hits),
        "blocked": blocked,
        "hits": hits,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan text against content lexicon")
    parser.add_argument("--text", default="")
    parser.add_argument("--text-file", type=Path)
    parser.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
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
