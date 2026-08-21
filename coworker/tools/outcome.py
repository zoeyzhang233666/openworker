"""Compatibility normalization for legacy Tool results.

The model still receives ``raw_result``. Only the compact outcome is exposed to GUI
diagnostics and persistent Turn Trace.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ToolOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = 1
    status: Literal["success", "unavailable", "partial", "failed", "denied"]
    data: Any = None
    error_code: str | None = None
    user_message: str | None = None
    retryable: bool = False
    provider_id: str | None = None
    source_refs: tuple[str, ...] = ()


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    version: Literal[1] = 1
    raw_result: Any
    outcome: ToolOutcome


_UNAVAILABLE_CODES = {"NO_DATA", "AUTH_REQUIRED", "UNAVAILABLE", "NOT_CONFIGURED", "DOWN"}


def normalize_tool_outcome(
    raw_result: Any,
    *,
    provider_id: str | None = None,
    denied: bool = False,
    denial_message: str | None = None,
) -> ToolOutcome:
    if denied:
        return ToolOutcome(
            status="denied",
            error_code="DENIED",
            user_message=denial_message,
            provider_id=provider_id,
        )
    if not isinstance(raw_result, dict):
        return ToolOutcome(status="success", data=raw_result, provider_id=provider_id)

    code = str(
        raw_result.get("error_code")
        or raw_result.get("code")
        or raw_result.get("status_code")
        or ""
    ).upper()
    status = str(raw_result.get("status") or "").lower()
    message = raw_result.get("user_message") or raw_result.get("message")
    if code in _UNAVAILABLE_CODES or status in {"unavailable", "not_found", "no_data"}:
        kind = "unavailable"
    elif status == "partial" or raw_result.get("partial") is True:
        kind = "partial"
    elif "error" in raw_result or status in {"error", "failed", "failure"}:
        kind = "failed"
    else:
        kind = "success"
    refs = raw_result.get("source_refs") or ()
    if not isinstance(refs, (list, tuple)):
        refs = ()
    return ToolOutcome(
        status=kind,
        data=raw_result,
        error_code=code or None,
        user_message=str(message) if message else None,
        retryable=bool(raw_result.get("retryable", False)),
        provider_id=str(raw_result.get("provider_id") or provider_id or "") or None,
        source_refs=tuple(str(item) for item in refs),
    )


def execute_with_outcome(registry: Any, name: str, arguments: dict[str, Any] | None = None) -> ToolExecutionResult:
    raw = registry.execute(name, arguments)
    return ToolExecutionResult(
        raw_result=raw,
        outcome=normalize_tool_outcome(raw, provider_id=name),
    )
