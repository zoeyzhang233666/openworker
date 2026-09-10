"""Deterministic chem-data-hub product name normalization (D-202)."""

from __future__ import annotations

_ALIASES: dict[str, str] = {
    "液化气": "液化石油气",
    "lpg": "液化石油气",
    "液化石油气": "液化石油气",
    "民用气": "液化石油气",
    "进口气": "液化石油气",
    "甲醇": "甲醇",
    "methanol": "甲醇",
    "meoh": "甲醇",
}


def resolve_chem_product_name(name: str) -> str:
    """Map common user/colloquial names to chem-data-hub canonical product names."""
    raw = (name or "").strip()
    if not raw:
        return raw
    key = raw.lower().replace(" ", "")
    if key in _ALIASES:
        return _ALIASES[key]
    for alias, canonical in _ALIASES.items():
        if alias.lower() in key or key in alias.lower():
            return canonical
    return raw
