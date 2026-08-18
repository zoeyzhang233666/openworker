"""Deterministic dominant-contract selection. No HTTP, no LLM."""

from __future__ import annotations

import re
from typing import Any, Optional

_CONTRACT_RE = re.compile(r"^[A-Za-z]{1,2}\d{3,4}$")
_CONTINUOUS_RE = re.compile(r"^[A-Za-z]+0$")
_SKIP_NAME = ("小计", "合计")


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def select_dominant_contract(rows: list[Any]) -> Optional[dict[str, Any]]:
    """Pick today's dominant among listed contracts.

    Rule: skip expired/summary/continuous/illegal rows; max open interest;
    if OI missing, max volume; then lexicographically smaller symbol.
    """
    candidates: list[tuple[Optional[float], Optional[float], str, dict[str, Any]]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        if any(token in name for token in _SKIP_NAME):
            continue
        symbol = str(row.get("symbol") or "").strip()
        if not symbol or _CONTINUOUS_RE.fullmatch(symbol):
            continue
        if not _CONTRACT_RE.fullmatch(symbol):
            continue
        oi = _num(row.get("open_interest", row.get("position")))
        volume = _num(row.get("volume"))
        candidates.append((oi, volume, symbol.upper(), row))
    if not candidates:
        return None
    with_oi = [item for item in candidates if item[0] is not None]
    pool = with_oi if with_oi else candidates

    def sort_key(
        item: tuple[Optional[float], Optional[float], str, dict[str, Any]]
    ) -> tuple[float, float, str]:
        oi, volume, symbol, _row = item
        oi_rank = -(oi if oi is not None else float("-inf"))
        vol_rank = -(volume if volume is not None else float("-inf"))
        return (oi_rank, vol_rank, symbol)

    pool.sort(key=sort_key)
    return pool[0][3]
