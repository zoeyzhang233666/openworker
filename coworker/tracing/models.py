"""Persistent trace schema. No message, prompt, arguments, results, or reasoning text."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HttpTiming(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    request_ms: float = Field(ge=0)
    headers_ms: float | None = Field(default=None, ge=0)


class ModelCallTiming(BaseModel):
    """Offsets are relative to this model call, except offset_ms (relative to trace)."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    offset_ms: float = Field(ge=0)
    elapsed_ms: float = Field(ge=0)
    provider_start_ms: float | None = Field(default=None, ge=0)
    upstream_first_content_ms: float | None = Field(default=None, ge=0)
    upstream_first_reasoning_ms: float | None = Field(default=None, ge=0)
    provider_first_text_ms: float | None = Field(default=None, ge=0)
    engine_first_text_ms: float | None = Field(default=None, ge=0)
    http_requests: tuple[HttpTiming, ...] = ()
    http_request_count: int = Field(default=0, ge=0)
    status: Literal["completed", "failed", "interrupted"]


class TurnTrace(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = 1
    trace_id: str
    parent_trace_id: str | None = None
    session_id: str
    source_kind: str = "user"
    started_at: str
    finished_at: str
    scenario_id: str | None = None
    scenario_source: str | None = None
    scenario_confidence: float | None = None
    route: str
    capability_ids: tuple[str, ...] = ()
    selected_tool_names: tuple[str, ...] = ()
    invoked_tool_names: tuple[str, ...] = ()
    model: str
    model_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    web_calls: int = Field(default=0, ge=0)
    subagent_calls: int = Field(default=0, ge=0)
    recovery_retries: int = Field(default=0, ge=0)
    current_context_tokens: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)
    usage_reported_calls: int = Field(default=0, ge=0)
    model_call_timings: tuple[ModelCallTiming, ...] = ()
    stage_elapsed_ms: dict[str, float] = Field(default_factory=dict)
    fallback: tuple[str, ...] = ()
    outcome_counts: dict[str, int] = Field(default_factory=dict)
    status: Literal[
        "running",
        "completed",
        "failed",
        "denied",
        "interrupted",
        "max_iterations_exceeded",
        "budget_paused", "truncated", "blocked",
    ] = "completed"
