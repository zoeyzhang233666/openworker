"""Declarative Subagent profiles and public runtime results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SubagentProfile(_FrozenModel):
    version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    title: str
    description: str
    agent_id: str
    mode: Literal["plan", "interactive"] = "plan"
    model: str | None = None
    effort: Literal["none", "low", "medium", "high", "xhigh"] | None = None
    max_turns: int = Field(default=16, ge=1, le=150)
    tool_allowlist: tuple[str, ...] | None = None
    disallowed_tools: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    mcp_servers: tuple[str, ...] = ()
    background: bool = True
    isolation: Literal["read_only", "shared_workspace"] = "read_only"
    allow_nested: bool = False
    instructions: str

    @model_validator(mode="after")
    def validate_authority(self) -> "SubagentProfile":
        if self.isolation == "read_only" and self.mode != "plan":
            raise ValueError("read_only profiles must use plan mode")
        overlap = set(self.tool_allowlist or ()) & set(self.disallowed_tools)
        if overlap:
            raise ValueError(f"tools cannot be both allowed and disallowed: {sorted(overlap)}")
        return self


class ForegroundSubagentResult(_FrozenModel):
    version: Literal[1] = 1
    task_id: str
    profile_id: str
    status: Literal["completed", "failed", "cancelled", "interrupted"]
    report: str = ""
    error: str | None = None
