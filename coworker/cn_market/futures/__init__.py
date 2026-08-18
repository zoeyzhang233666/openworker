"""Domestic futures helpers (dominant selection + theoretical margin)."""

from .continuous import select_dominant_contract
from .margin import CONTRACT_MULTIPLIER, calculate_theoretical_margin

__all__ = [
    "CONTRACT_MULTIPLIER",
    "calculate_theoretical_margin",
    "select_dominant_contract",
]
