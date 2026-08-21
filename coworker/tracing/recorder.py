"""Best-effort aggregation of safe Event metadata into one TurnTrace."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ..events import Event, EventType
from ..turn_planner import TurnPlan
from .models import TurnTrace


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TurnTraceRecorder:
    def __init__(
        self,
        *,
        session_id: str,
        model: str,
        plan: TurnPlan | None,
        source_kind: str = "user",
        parent_trace_id: str | None = None,
    ) -> None:
        self.trace_id = uuid.uuid4().hex
        self.parent_trace_id = parent_trace_id
        self.session_id = session_id
        self.model = model
        self.plan = plan
        self.source_kind = source_kind
        self.started_at = _now()
        self._started = time.perf_counter()
        self.model_calls = 0
        self.tool_calls = 0
        self.web_calls = 0
        self.subagent_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.invoked_tools: list[str] = []
        self.outcomes: dict[str, int] = {}
        self.status = "running"

    def observe(self, event: Event) -> None:
        data = event.data or {}
        if event.type is EventType.ASSISTANT_MESSAGE:
            self.model_calls += 1
            usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
            self.input_tokens += _usage_int(usage, "input_tokens", "prompt_tokens", "context_tokens")
            self.output_tokens += _usage_int(usage, "output_tokens", "completion_tokens")
            self.total_tokens += _usage_int(usage, "total_tokens")
        elif event.type is EventType.TOOL_PROPOSED:
            name = str(data.get("name") or "")
            if name:
                self.tool_calls += 1
                self.invoked_tools.append(name)
                if name in {"web_search", "web_fetch"}:
                    self.web_calls += 1
                if name in {"explore", "start_subagent"}:
                    self.subagent_calls += 1
        elif event.type is EventType.TOOL_FINISHED:
            outcome = data.get("outcome") if isinstance(data.get("outcome"), dict) else {}
            status = str(outcome.get("status") or data.get("status") or "failed")
            normalized = "success" if status == "ok" else status
            self.outcomes[normalized] = self.outcomes.get(normalized, 0) + 1
        elif event.type is EventType.TURN_END:
            raw = str(data.get("status") or "completed")
            self.status = raw if raw in {"completed", "max_iterations_exceeded"} else "failed"
        elif event.type is EventType.ERROR:
            self.status = "failed"
        elif event.type is EventType.INTERRUPTED:
            self.status = "interrupted"

    def finish(self) -> TurnTrace:
        plan = self.plan
        scenario = plan.scenario_resolution if plan is not None else None
        capability = plan.capability_plan if plan is not None else None
        route = (
            plan.decision.route.value
            if plan is not None and plan.decision is not None
            else "legacy"
        )
        status = self.status
        if status == "running":
            status = "completed"
        if self.outcomes.get("denied") and not self.outcomes.get("success") and status == "completed":
            status = "denied"
        if not self.total_tokens:
            self.total_tokens = self.input_tokens + self.output_tokens
        elapsed = (time.perf_counter() - self._started) * 1000.0
        router_elapsed = plan.router_elapsed_ms if plan is not None else None
        return TurnTrace(
            trace_id=self.trace_id,
            parent_trace_id=self.parent_trace_id,
            session_id=self.session_id,
            source_kind=self.source_kind,
            started_at=self.started_at,
            finished_at=_now(),
            scenario_id=scenario.scenario_id if scenario is not None else None,
            scenario_source=scenario.source if scenario is not None else None,
            scenario_confidence=scenario.confidence if scenario is not None else None,
            route=route,
            capability_ids=tuple(
                item.capability_id for item in (capability.resolutions if capability else ())
            ),
            selected_tool_names=capability.selected_tool_names if capability else (),
            invoked_tool_names=tuple(dict.fromkeys(self.invoked_tools)),
            model=self.model,
            model_calls=self.model_calls,
            tool_calls=self.tool_calls,
            web_calls=self.web_calls,
            subagent_calls=self.subagent_calls,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
            stage_elapsed_ms={
                "router": round(float(router_elapsed or 0.0), 3),
                "total": round(elapsed, 3),
            },
            fallback=capability.fallback if capability else (),
            outcome_counts=dict(sorted(self.outcomes.items())),
            status=status,
        )


def _usage_int(usage: dict[str, Any], *names: str) -> int:
    for name in names:
        value = usage.get(name)
        if isinstance(value, (int, float)) and value >= 0:
            return int(value)
    return 0
