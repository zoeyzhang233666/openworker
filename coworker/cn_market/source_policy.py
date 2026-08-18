"""Pre-encoded source policy. Runtime web/shell recovery is forbidden."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import STATUS_OK, STATUS_PARTIAL, STATUS_SOURCE_UNAVAILABLE, STATUS_UNSUPPORTED_KEYLESS

MAX_PROVIDER_ATTEMPTS = 2

FORBIDDEN_RUNTIME_FALLBACKS = frozenset(
    {"web_search", "web_fetch", "shell", "curl", "browser"}
)


@dataclass(frozen=True)
class DatasetPolicy:
    dataset: str
    primary: str
    fallback: Optional[str]
    keyless: bool
    capability_status: str


# Status values reflect Run 0 live probes (2026-08-18), not vendor marketing.
_POLICIES: dict[str, DatasetPolicy] = {
    "stock_daily": DatasetPolicy(
        "stock_daily", "sina_daily", None, True, STATUS_OK
    ),
    "stock_minute": DatasetPolicy(
        "stock_minute", "sina_minute", None, True, STATUS_PARTIAL
    ),
    "stock_quote": DatasetPolicy(
        "stock_quote", "sina_hq", None, True, STATUS_OK
    ),
    "stock_financials": DatasetPolicy(
        "stock_financials", "sina_report", None, True, STATUS_OK
    ),
    "northbound_holdings": DatasetPolicy(
        "northbound_holdings", "", None, True, STATUS_SOURCE_UNAVAILABLE
    ),
    "lhb_list": DatasetPolicy(
        "lhb_list", "eastmoney_lhb", None, True, STATUS_OK
    ),
    "margin_summary": DatasetPolicy(
        "margin_summary", "sse_margin", None, True, STATUS_PARTIAL
    ),
    "northbound_history": DatasetPolicy(
        "northbound_history", "eastmoney_hsgt", None, True, STATUS_PARTIAL
    ),
    "futures_daily": DatasetPolicy(
        "futures_daily", "sina_futures_daily", "exchange_daily", True, STATUS_OK
    ),
    "futures_minute": DatasetPolicy(
        "futures_minute", "sina_futures_minute", None, True, STATUS_OK
    ),
    "futures_l1": DatasetPolicy(
        "futures_l1", "sina_futures_realtime", None, True, STATUS_OK
    ),
    "option_sse": DatasetPolicy(
        "option_sse", "sina_option", "sse_option_list", True, STATUS_OK
    ),
    "option_greeks": DatasetPolicy(
        "option_greeks", "sina_option_greeks", None, True, STATUS_OK
    ),
    "option_exchange_stats": DatasetPolicy(
        "option_exchange_stats", "", None, True, STATUS_SOURCE_UNAVAILABLE
    ),
    "tick_l2": DatasetPolicy(
        "tick_l2", "", None, False, STATUS_UNSUPPORTED_KEYLESS
    ),
}


def policy_for(dataset: str) -> DatasetPolicy:
    try:
        return _POLICIES[dataset]
    except KeyError as exc:
        raise KeyError(f"unknown CN market dataset: {dataset}") from exc


def assert_attempt_allowed(attempt: int) -> None:
    if attempt < 1 or attempt > MAX_PROVIDER_ATTEMPTS:
        raise ValueError(
            f"provider attempt {attempt} exceeds MAX_PROVIDER_ATTEMPTS={MAX_PROVIDER_ATTEMPTS}"
        )


def is_forbidden_runtime_fallback(name: str) -> bool:
    return name in FORBIDDEN_RUNTIME_FALLBACKS
