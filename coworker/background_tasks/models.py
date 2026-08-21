"""Immutable contracts for unified Agent and Shell background tasks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TaskKind = Literal["agent", "shell"]
TaskChangeKind = Literal["created", "status", "output"]
TaskStatus = Literal[
    "queued", "running", "completed", "failed", "cancelled", "interrupted"
]
TERMINAL_TASK_STATUSES = frozenset(
    {"completed", "failed", "cancelled", "interrupted"}
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class BackgroundTaskSpec(_FrozenModel):
    version: Literal[1] = 1
    kind: TaskKind
    owner_session_id: str = Field(min_length=1)
    description: str = Field(min_length=1, max_length=240)
    workspace: str = ""
    profile_id: str | None = None
    child_session_id: str | None = None
    parent_task_id: str | None = None
    parent_trace_id: str | None = None
    model: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class BackgroundTaskRecord(_FrozenModel):
    version: Literal[1] = 1
    id: str
    kind: TaskKind
    status: TaskStatus
    owner_session_id: str
    description: str
    workspace: str = ""
    profile_id: str | None = None
    child_session_id: str | None = None
    parent_task_id: str | None = None
    parent_trace_id: str | None = None
    model: str | None = None
    created_at: float
    updated_at: float
    started_at: float | None = None
    finished_at: float | None = None
    run_count: int = 0
    output_size: int = 0
    exit_code: int | None = None
    error: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class TaskOutputChunk(_FrozenModel):
    version: Literal[1] = 1
    task_id: str
    seq: int = Field(ge=1)
    stream: Literal["assistant", "stdout", "stderr", "event", "system"]
    text: str
    created_at: float


class TaskOutputPage(_FrozenModel):
    version: Literal[1] = 1
    task_id: str
    chunks: tuple[TaskOutputChunk, ...] = ()
    next_cursor: int = 0
    truncated: bool = False


class AgentRunResult(_FrozenModel):
    version: Literal[1] = 1
    report: str = ""
    status: Literal["completed", "failed", "cancelled"] = "completed"
    error: str | None = None


class BackgroundTaskChange(_FrozenModel):
    version: Literal[1] = 1
    change: TaskChangeKind
    task: BackgroundTaskRecord
