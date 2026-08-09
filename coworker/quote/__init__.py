"""Deterministic quote calculation (platform Tool)."""

from __future__ import annotations

from .calc import QuoteCalcResult, QuoteLineResult, calculate_quote
from .tool import make_calculate_quote_tool

__all__ = [
    "QuoteCalcResult",
    "QuoteLineResult",
    "calculate_quote",
    "make_calculate_quote_tool",
]
