"""Typed errors for the CN market layer."""

from __future__ import annotations

from .models import (
    STATUS_INVALID_REQUEST,
    STATUS_INVALID_SYMBOL,
    STATUS_SOURCE_UNAVAILABLE,
    STATUS_UNSUPPORTED,
    STATUS_UNSUPPORTED_KEYLESS,
)


class CNMarketError(Exception):
    status: str = STATUS_SOURCE_UNAVAILABLE

    def __init__(self, message: str, *, status: str | None = None) -> None:
        super().__init__(message)
        if status is not None:
            self.status = status


class InvalidSymbolError(CNMarketError):
    status = STATUS_INVALID_SYMBOL


class InvalidRequestError(CNMarketError):
    status = STATUS_INVALID_REQUEST


class SourceUnavailableError(CNMarketError):
    status = STATUS_SOURCE_UNAVAILABLE


class UnsupportedKeylessError(CNMarketError):
    status = STATUS_UNSUPPORTED_KEYLESS


class UnsupportedCapabilityError(CNMarketError):
    status = STATUS_UNSUPPORTED
