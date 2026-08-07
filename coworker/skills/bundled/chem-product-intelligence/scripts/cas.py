"""Small, dependency-free CAS Registry Number syntax and checksum helpers."""

from __future__ import annotations

import json
import re
import sys

_CAS = re.compile(r"^(\d{2,7})-(\d{2})-(\d)$")


def normalize_cas(value: str) -> str:
    """Return canonical ASCII-hyphen CAS text or reject non-CAS input."""
    if not isinstance(value, str):
        raise TypeError("CAS must be a string")
    candidate = value.strip().replace("–", "-").replace("—", "-")
    if not _CAS.fullmatch(candidate):
        raise ValueError("CAS must use NNNNN-NN-N format")
    return candidate


def is_valid_cas(value: str) -> bool:
    """Return whether a syntactically valid CAS text has a correct checksum."""
    try:
        normalized = normalize_cas(value)
    except (TypeError, ValueError):
        return False
    digits = normalized.replace("-", "")
    expected = sum(int(digit) * index for index, digit in enumerate(reversed(digits[:-1]), 1)) % 10
    return expected == int(digits[-1])


def main(argv: list[str] | None = None) -> int:
    """Validate one CAS argument and emit a small machine-readable result."""
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        sys.stderr.write("usage: cas.py CAS\n")
        return 2
    try:
        normalized = normalize_cas(arguments[0])
    except (TypeError, ValueError) as error:
        sys.stderr.write(f"invalid CAS format: {error}\n")
        return 2
    if not is_valid_cas(normalized):
        sys.stderr.write("CAS checksum is invalid\n")
        return 1
    sys.stdout.write(json.dumps({"normalized": normalized, "valid": True}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
