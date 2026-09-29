"""Best-effort aggregation of safe Event metadata into one TurnTrace."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ..events import Event, EventType
from ..provider_timing import CallTiming
from ..turn_planner import TurnPlan
from .models import ModelCallTiming, TurnTrace


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
        clock=None,
    ) -> None:
        self.trace_id = uuid.uuid4().hex
        self.parent_trace_id = parent_trace_id
        self.session_id = session_id
        self.model = model
        self.plan = plan
        self.source_kind = source_kind
        self.started_at = _now()
        self._clock = clock or time.perf_counter
        self._started = self._clock()
        self.model_call_timings: list[ModelCallTiming] = []
        self.stage_elapsed_ms: dict[str, float] = {}
        self._phase_starts: dict[str, float] = {}
        self.model_calls = 0
        self._has_request_events = False
        self.recovery_retries = 0
        self.current_context_tokens = 0
        self.tool_calls = 0
        self.web_calls = 0
        self.subagent_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.cache_read_tokens = 0
        self.cache_write_tokens = 0
        self.usage_reported_calls = 0
        self.invoked_tools: list[str] = []
        self.outcomes: dict[str, int] = {}
        self.status = "running"

    def start_model_call(self) -> CallTiming:
        return CallTiming(offset_ms=self._elapsed(), clock=self._clock)

    def finish_model_call(self, timing: CallTiming, status: str) -> None:
        self.model_call_timings.append(ModelCallTiming.model_validate(timing.finish(status)))

    def _elapsed(self) -> float:
        return round(max(0, (self._clock() - self._started) * 1000), 3)

    def _close_phase(self, name: str) -> None:
        start = self._phase_starts.pop(name, None)
        if start is not None:
            self.stage_elapsed_ms[name] = self.stage_elapsed_ms.get(name, 0) + self._elapsed() - start

    def observe(self, event: Event) -> None:
        data = event.data or {}
        if event.type in {EventType.ASSISTANT_DELTA, EventType.ASSISTANT_MESSAGE} and data.get("text"):
            # An engine text event may be narration; it is NOT screen paint or a useful answer.
            self.stage_elapsed_ms.setdefault("first_engine_text", self._elapsed())
        if event.type is EventType.COMPACTING:
            self._phase_starts.setdefault("compaction", self._elapsed())
        elif event.type is EventType.COMPACTED:
            self._close_phase("compaction")
        elif event.type is EventType.TOOL_PROPOSED:
            self._phase_starts.setdefault("tools_and_approval", self._elapsed())
        elif event.type is EventType.ITERATION_END:
            self._close_phase("tools_and_approval")
        if event.type is EventType.MODEL_REQUEST:
            self._has_request_events = True
            self.model_calls += 1
        elif event.type is EventType.CONTINUATION:
            self.recovery_retries += 1
        elif event.type is EventType.ASSISTANT_MESSAGE:
            if not self._has_request_events:
                self.model_calls += 1
            usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
            if usage:
                self.usage_reported_calls += 1
            self.cache_read_tokens += _usage_int(usage, "cache_read")
            self.cache_write_tokens += _usage_int(usage, "cache_write")
            prompt = (_usage_int(usage, "input") + _usage_int(usage, "cache_read")
                      + _usage_int(usage, "cache_write")) if "input" in usage else _usage_int(
                          usage, "input_tokens", "prompt_tokens", "context_tokens")
            output = _usage_int(usage, "output", "output_tokens", "completion_tokens")
            self.current_context_tokens = prompt
            self.input_tokens += prompt
            self.output_tokens += output
            self.total_tokens += _usage_int(usage, "total_tokens") or prompt + output
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
            self.status = raw if raw in {"completed", "max_iterations_exceeded", "budget_paused", "truncated", "blocked"} else "failed"
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
            status = "failed"
        if self.outcomes.get("denied") and not self.outcomes.get("success") and status == "completed":
            status = "denied"
        if not self.total_tokens:
            self.total_tokens = self.input_tokens + self.output_tokens
        elapsed = self._elapsed()
        for phase in list(self._phase_starts):
            self._close_phase(phase)
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
            recovery_retries=self.recovery_retries,
            current_context_tokens=self.current_context_tokens,
            tool_calls=self.tool_calls,
            web_calls=self.web_calls,
            subagent_calls=self.subagent_calls,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
            cache_read_tokens=self.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens,
            usage_reported_calls=self.usage_reported_calls,
            model_call_timings=tuple(self.model_call_timings),
            stage_elapsed_ms={
                **{k: round(v, 3) for k, v in self.stage_elapsed_ms.items()},
                "model_calls": round(sum(t.elapsed_ms for t in self.model_call_timings), 3),
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
