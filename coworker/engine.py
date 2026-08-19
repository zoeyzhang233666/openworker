"""TurnEngine — the owned agent loop.

Async, but with blocking provider/tool calls wrapped in `asyncio.to_thread` so the loop
(and any UI consuming its events) stays responsive. One user turn spans many model↔tool
iterations until the model stops requesting tools, a rail trips, or it's interrupted.
When the model requests several tool calls in one turn, low-risk ones (reads, searches)
execute concurrently; writes/shell stay strictly ordered.

Approvals are handled out-of-band via an injected async `approver`: when the permission
engine says `needs_user`, the engine emits `PERMISSION_REQUIRED` and awaits the approver.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Awaitable, Callable, Mapping, Optional

_log = logging.getLogger(__name__)

from . import compaction as _compaction
from .events import Event, EventType
from .execution_profile import (
    ExecutionProfile,
    apply_reasoning_mode_settings,
    budget_guidance_text,
    budget_phase_for_iteration,
)
from .market_intent import MarketScope
from .permissions import Mode, PermissionEngine
from .providers import AssistantTurn, ProviderClient, ToolCall
from .providers.errors import friendly_model_error
from .tool_policy import TurnToolPolicy
from .tool_projection import project_provider_visible_schemas
from .tools import ToolRegistry
from .turn_instrumentation import (
    build_model_call_snapshot,
    build_provider_call_shape_snapshot,
    build_turn_snapshot,
    emit_instrumentation,
)
from .turn_planner import PromptProfile, TurnPlan, TurnPlanner

# HARD STOP G: outbound-only prompt for one model-only finalization at hard ceiling.
_EMERGENCY_FINALIZATION_PROMPT = """The tool-call iteration budget has been exhausted.

You may not call any more tools.

Using only the evidence and tool results already present in the conversation,
produce the best possible final answer now.

If a deliverable file was already created, reference it correctly.

If some requested work could not be completed, clearly state the remaining gap,
but still provide the most useful finished result possible."""

# Section 65 step 47: advisory only — never hard-block the tool.
_DUPLICATE_TOOL_WARNING = (
    "You have repeated an identical tool call several times.\n"
    "Do not call it again unless there is a concrete reason to expect a different result.\n"
    "Use the evidence already collected and move toward completion."
)


def _tool_call_signature(tool_call: ToolCall) -> tuple[str, str]:
    return (
        tool_call.name,
        json.dumps(
            tool_call.arguments,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        ),
    )


class ApprovalOutcome(str, Enum):
    ONCE = "once"
    ALWAYS_TOOL = "always_tool"
    ALWAYS_COMMAND = "always_command"
    DENY = "deny"


@dataclass
class PermissionRequest:
    tool_name: str
    arguments: dict[str, Any]
    metadata: Any
    reason: str
    tool_call_id: Optional[str] = None  # for durable resume (idempotent inbox item)


Approver = Callable[[PermissionRequest], Awaitable[ApprovalOutcome]]


async def _deny_all(_request: PermissionRequest) -> ApprovalOutcome:
    return ApprovalOutcome.DENY


class TurnEngine:
    def __init__(
        self,
        *,
        provider: ProviderClient,
        registry: ToolRegistry,
        permissions: PermissionEngine,
        model: str,
        instructions: Optional[str] = None,
        approver: Optional[Approver] = None,
        max_iterations: int = 12,
        model_settings: Optional[dict[str, Any]] = None,
        messages: Optional[list[dict[str, Any]]] = None,
        audit_sink: Optional[Callable[[dict[str, Any]], None]] = None,
        context_provider: Optional[Callable[[], str]] = None,
        directory_requester: Optional[
            Callable[[dict[str, Any]], "Awaitable[dict[str, Any]]"]
        ] = None,
        plan_approver: Optional[
            Callable[[dict[str, Any]], "Awaitable[dict[str, Any]]"]
        ] = None,
        question_asker: Optional[
            Callable[[dict[str, Any]], "Awaitable[dict[str, Any]]"]
        ] = None,
        # Called (thread-safe, best-effort) when the user stops the turn — e.g. the
        # executor's kill for a running shell command.
        interrupt_hooks: Optional[list[Callable[[], None]]] = None,
        # Optional route profile (HARD STOP C). None → full legacy-inert path:
        # only max_iterations / model_settings / existing state machine apply.
        # Soft targets, Converge/Deliver guidance, and route reasoning defaults
        # activate only when a caller attaches an explicit profile.
        execution_profile: Optional[ExecutionProfile] = None,
        # HARD STOP E: independent kill switch (built-in default OFF). When False,
        # provider-visible schemas stay at the full registered legacy set even if
        # a FAST_CHAT/KNOWLEDGE profile is attached.
        tool_projection_enabled: bool = False,
        # HARD STOP F / Step 58: Config built-in is candidate ON; TurnEngine ctor
        # default stays False so unit tests that omit the flag remain salvage-safe.
        # When False, tools paths stay compat-buffered + salvage-safe.
        # Production wiring passes Config (known-safe matrix still gates true stream).
        structured_tools_true_streaming_enabled: bool = False,
        # HARD STOP G: Emergency Finalization kill switch (built-in OFF).
        # When True and guards allow, one tools-disabled model call at hard ceiling.
        emergency_finalization_enabled: bool = False,
        turn_tool_policy: Optional[TurnToolPolicy] = None,
        mandatory_tool_names: Optional[set[str]] = None,
        # Optional RouteDecision for instrumentation only (Section 65 step 48).
        route_decision: Optional[Any] = None,
        router_elapsed_ms: Optional[float] = None,
        # D-165: one immutable plan is activated at run/resume start and reused by
        # retries. Static profile arguments above remain supported for direct callers.
        turn_planner: Optional[TurnPlanner] = None,
        prompt_profiles: Optional[Mapping[PromptProfile, str]] = None,
        prompt_projection_enabled: bool = False,
        prompt_policy_version: int = 1,
    ) -> None:
        self.provider = provider
        self.registry = registry
        self.permissions = permissions
        self.model = model
        self.approver = approver or _deny_all
        self.max_iterations = max_iterations
        self.model_settings = dict(model_settings or {})
        self.execution_profile = execution_profile
        self.tool_projection_enabled = bool(tool_projection_enabled)
        self.structured_tools_true_streaming_enabled = bool(
            structured_tools_true_streaming_enabled
        )
        self.emergency_finalization_enabled = bool(emergency_finalization_enabled)
        self.turn_tool_policy = turn_tool_policy
        self.mandatory_tool_names = (
            set(mandatory_tool_names) if mandatory_tool_names else set()
        )
        self.route_decision = route_decision
        self.router_elapsed_ms = router_elapsed_ms
        self.turn_planner = turn_planner
        self._active_turn_plan: Optional[TurnPlan] = None
        self._last_turn_plan: Optional[TurnPlan] = None
        self._resolved_market_scope: Optional[MarketScope] = None
        self._last_resolved_market_scope: Optional[MarketScope] = None
        self.prompt_profiles = dict(prompt_profiles or {})
        self.prompt_projection_enabled = bool(prompt_projection_enabled)
        self.prompt_policy_version = int(prompt_policy_version)
        self.messages: list[dict[str, Any]] = list(messages or [])
        self.audit_sink = audit_sink
        # 1-based iteration counter for soft-budget phase guidance (outbound only).
        self._budget_iteration = 0
        # Outbound-only: inject EF prompt / force tools=None for one finalization call.
        self._emergency_finalizing = False
        # Section 65 step 47: consecutive identical tool signatures (name+args).
        self._recent_tool_signatures: list[tuple[str, str]] = []
        # Returns an ephemeral `<system-context>` block appended to the LAST user message at
        # send-time only (never persisted). We can't reliably inject system messages mid-thread
        # across providers, so dynamic per-turn context (e.g. the live directory list) rides on
        # the latest user turn. Returns "" when there's nothing to add.
        self.context_provider = context_provider
        # Handles the `request_directory` tool: emits a DIRECTORY_REQUESTED prompt, waits for the
        # user to grant/decline a folder out-of-band, applies the grant to this live session, and
        # returns the outcome. None on surfaces that can't prompt (the tool then no-ops).
        self.directory_requester = directory_requester
        # Handles the `propose_plan` tool: emits PLAN_PROPOSED, waits for the user's decision.
        # An approving result flips the live PermissionEngine out of plan mode (same session,
        # context kept). None on surfaces that can't prompt (the tool then no-ops).
        self.plan_approver = plan_approver
        # Handles the `ask_user` tool: turns a question into an Inbox item and waits for the answer
        # (answerable inline in a live session or from the Inbox when unattended). None on surfaces
        # that can't ask (the tool then no-ops).
        self.question_asker = question_asker
        # Auto-compaction (OPE-27) — set post-construction by the surface/manager so the
        # constructor footprint stays put. `compaction_settings` is a live getter (Settings
        # changes apply without a rebuild); `is_attended` gates the failure prompt (None →
        # treat as unattended: never park a background run on internal bookkeeping).
        self.compaction_state: Optional[_compaction.CompactionState] = None
        self.compaction_settings: Optional[Callable[[], dict[str, Any]]] = None
        self.is_attended: Optional[Callable[[], bool]] = None
        self._last_context_tokens: Optional[int] = None
        self.audit_context: dict[str, Any] = {}
        existing_system = bool(
            self.messages and self.messages[0].get("role") == "system"
        )
        if instructions and not existing_system:
            system_message: dict[str, Any] = {
                "role": "system",
                "content": instructions,
            }
            if self.prompt_projection_enabled:
                system_message["_prompt_policy_version"] = self.prompt_policy_version
            self.messages.insert(0, system_message)
        self._prompt_projection_eligible = bool(
            self.prompt_projection_enabled
            and self.messages
            and self.messages[0].get("role") == "system"
            and self.messages[0].get("_prompt_policy_version")
            == self.prompt_policy_version
        )
        self._legacy_prompt_session = bool(
            self.prompt_projection_enabled
            and existing_system
            and not self._prompt_projection_eligible
        )
        self._cancel = asyncio.Event()
        # Each pending steering message: (text, optional MessageSource sidecar dict).
        self._steering: list[tuple[str, Optional[dict[str, Any]]]] = []
        # tool_call.id → the standing rule that auto-allowed it ("tool → target"), so the
        # TOOL_FINISHED event can carry the note to the tool card (§25).
        self._standing_notes: dict[str, str] = {}
        self._interrupt_hooks: list[Callable[[], None]] = list(interrupt_hooks or [])

    @property
    def target_iterations(self) -> Optional[int]:
        """Soft target from an attached ExecutionProfile; None on the legacy path."""
        profile = self._current_execution_profile()
        return None if profile is None else profile.target_iterations

    @property
    def active_turn_plan(self) -> Optional[TurnPlan]:
        return self._active_turn_plan

    @property
    def prompt_projection_active(self) -> bool:
        return self._prompt_projection_eligible

    def _current_execution_profile(self) -> Optional[ExecutionProfile]:
        if self._active_turn_plan is not None:
            return self._active_turn_plan.execution_profile
        return self.execution_profile

    def _current_tool_policy(self) -> Optional[TurnToolPolicy]:
        if self._active_turn_plan is not None:
            return self._active_turn_plan.tool_policy
        return self.turn_tool_policy

    def _current_route_decision(self) -> Optional[Any]:
        if self._active_turn_plan is not None:
            return self._active_turn_plan.decision
        return self.route_decision

    def _current_router_elapsed_ms(self) -> Optional[float]:
        if self._active_turn_plan is not None:
            return self._active_turn_plan.router_elapsed_ms
        return self.router_elapsed_ms

    def _activate_plan(
        self,
        user_input: str | list,
        *,
        source: Optional[dict[str, Any]] = None,
        display: Optional[str] = None,
        durable_resume: bool = False,
    ) -> Optional[TurnPlan]:
        if self.turn_planner is None:
            self._active_turn_plan = None
            self._resolved_market_scope = None
            self._last_resolved_market_scope = None
            return None
        if self._legacy_prompt_session:
            plan = TurnPlan.legacy()
            self._active_turn_plan = plan
            self._last_turn_plan = plan
            self._resolved_market_scope = None
            self._last_resolved_market_scope = None
            return plan
        try:
            plan = self.turn_planner.plan(
                user_input,
                source=source,
                display=display,
                durable_resume=durable_resume,
            )
        except Exception as exc:
            # Projection failure must fail open to the legacy capability surface.
            _log.warning(
                "turn planning failed; using legacy path error_type=%s",
                type(exc).__name__,
            )
            plan = TurnPlan.legacy()
        self._active_turn_plan = plan
        self._last_turn_plan = plan
        selection = plan.market_selection
        scope = selection.intent.scope if selection is not None else None
        self._resolved_market_scope = scope
        self._last_resolved_market_scope = scope
        return plan

    def _clear_active_plan(self) -> None:
        self._active_turn_plan = None
        self._resolved_market_scope = None

    def _note_tool_signatures(self, tool_calls: list[ToolCall]) -> None:
        """Record exact name+args signatures for consecutive-duplicate detection."""
        for tool_call in tool_calls:
            self._recent_tool_signatures.append(_tool_call_signature(tool_call))

    def _duplicate_tool_warning_for_outbound(self) -> str:
        """Advisory warning when the same signature repeats ≥3 times consecutively."""
        if len(self._recent_tool_signatures) < 3:
            return ""
        last = self._recent_tool_signatures[-1]
        streak = 0
        for sig in reversed(self._recent_tool_signatures):
            if sig != last:
                break
            streak += 1
        if streak < 3:
            return ""
        return _DUPLICATE_TOOL_WARNING

    def _emit_turn_instrumentation(self) -> None:
        profile = self._current_execution_profile()
        policy = self._current_tool_policy()
        tools = None
        try:
            if not self._emergency_finalizing:
                tools = project_provider_visible_schemas(
                    self.registry,
                    tool_projection_enabled=self.tool_projection_enabled,
                    profile=profile,
                    tool_policy=policy,
                    mandatory_tool_names=self.mandatory_tool_names,
                )
        except Exception:
            tools = None
        tools_enabled = tools is not None
        allowed_tool_count = 0 if tools is None else len(tools)
        snap = build_turn_snapshot(
            route_decision=self._current_route_decision(),
            execution_profile=profile,
            tool_projection_enabled=self.tool_projection_enabled,
            tools_enabled=tools_enabled,
            allowed_tool_count=allowed_tool_count,
            router_elapsed_ms=self._current_router_elapsed_ms(),
            mandatory_tool_count=len(self.mandatory_tool_names) or None,
        )
        emit_instrumentation("turn", snap)

    # -- external controls ------------------------------------------------------
    def request_interrupt(self) -> None:
        """Stop the turn as soon as possible, from ANY state: mid-stream (the producer
        thread drops the stream between chunks), mid-tool (interrupt hooks kill the
        running command), awaiting an approval/question/plan (the await resolves as
        interrupted), or between iterations (the loop checkpoint). Every pending
        tool_call still gets a tool-error result so the history never carries orphans
        (hosted templates reject them, and durable-resume would re-prompt them)."""
        self._cancel.set()
        for hook in self._interrupt_hooks:
            try:
                hook()
            except Exception:
                pass  # best-effort: a dead executor must not block the stop

    async def _interruptible(self, coro: Any, interrupted: Any) -> Any:
        """Await `coro`, but resolve early with `interrupted` if the user stops the
        turn. The pending task is cancelled so an answered-later Inbox card no-ops."""
        task = asyncio.ensure_future(coro)
        cancel_wait = asyncio.ensure_future(self._cancel.wait())
        try:
            done, _ = await asyncio.wait(
                {task, cancel_wait}, return_when=asyncio.FIRST_COMPLETED
            )
            if task in done:
                return task.result()
            task.cancel()
            return interrupted
        finally:
            cancel_wait.cancel()

    def queue_steering(
        self, text: str, source: Optional[dict[str, Any]] = None
    ) -> None:
        self._steering.append((text, source))

    # -- main loop --------------------------------------------------------------
    async def run(
        self,
        user_input: "str | list",
        *,
        source: Optional[dict[str, Any]] = None,
        display: Optional[str] = None,
    ) -> AsyncIterator[Event]:
        # `user_input` is a string, or OpenAI content-parts (text + image_url) for attachments.
        # `source` (a MessageSource dict) is a display-only sidecar for connector messages: it
        # rides on the persisted user message + the TURN_START event, but is stripped before the
        # message reaches a provider (see `_outbound_messages`). `content` stays the framed text.
        # `display` is the same split for force-run skills (SKILLS-SPEC §4.1 #3): the user's
        # literal "/skill …" line for the transcript, while `content` carries the model-facing
        # framing. `ts` (unix seconds, stamped on every appended message) is the same kind of
        # sidecar.
        self._cancel.clear()
        self._activate_plan(user_input, source=source, display=display)
        try:
            message: dict[str, Any] = {
                "role": "user",
                "content": user_input,
                "ts": time.time(),
            }
            if source is not None:
                message["source"] = source
            if display is not None:
                message["_display"] = display
            self.messages.append(message)
            data: dict[str, Any] = {"input": user_input}
            if source is not None:
                data["source"] = source
            if display is not None:
                data["display"] = display
            yield Event(EventType.TURN_START, data)
            async for event in self._loop():
                yield event
        finally:
            self._clear_active_plan()

    def switch_model(self, model: str) -> Optional[str]:
        """Rebind the session's model mid-conversation (roadmap item 3). History is
        canonical OpenAI shape and every provider converts per call, so the switch is just
        the field write — plus a persisted notice marking WHERE it happened, with a
        degradation warning when history carries images the new model can't see (those are
        sent as placeholders — see `_outbound_messages`). Returns the notice text, or None
        when nothing changed (same model, or first bind on a fresh session)."""
        if not model or model == self.model:
            return None
        had_history = any(m.get("role") != "system" for m in self.messages)
        self.model = model
        if not had_history:
            return None
        from .providers.matrix import model_labels

        text = f"Model switched to {model_labels().get(model, model)}"
        try:
            caps = self.provider.capabilities(model)
        except Exception:
            caps = None
        if (
            caps is not None
            and not getattr(caps, "vision", False)
            and self._history_has_images()
        ):
            text += " — earlier images can't be read by this model"
        self._append_notice("model_switch", text)
        return text

    def _history_has_images(self) -> bool:
        return any(
            isinstance(p, dict) and p.get("type") == "image_url"
            for msg in self.messages
            if isinstance(msg.get("content"), list)
            for p in msg["content"]
        )

    def _tail_is_retriable_error(self) -> bool:
        """True when the history tail is an error notice, looking through any model_switch
        notices appended after it (a switch must not consume the retry)."""
        for message in reversed(self.messages):
            if message.get("role") != "notice":
                return False
            if message.get("kind") == "model_switch":
                continue
            return message.get("kind") == "error"
        return False

    def _append_notice(self, kind: str, text: Optional[str] = None) -> None:
        """Persist a turn-ending marker (error/interrupted) as a display-only `notice`
        message: it survives reload like the transcript does, but `_outbound_messages`
        drops the role so no provider ever sees it."""
        notice: dict[str, Any] = {"role": "notice", "kind": kind, "ts": time.time()}
        if text:
            notice["text"] = text
        self.messages.append(notice)

    async def retry(self) -> AsyncIterator[Event]:
        """Re-run the model loop after a provider error — no new user message; the failed
        turn's input is already the tail of history. Guarded on the tail being an error
        notice so a stray retry frame can't re-answer a completed turn. Trailing
        model_switch notices don't break the guard — switching models and THEN retrying
        is the intended recovery path (owner-hit 2026-07-23)."""
        if not self._tail_is_retriable_error():
            return
        self._cancel.clear()
        # A retry is the same logical turn: reuse the immutable plan exactly.
        self._active_turn_plan = self._last_turn_plan
        self._resolved_market_scope = self._last_resolved_market_scope
        try:
            yield Event(EventType.TURN_START, {"input": ""})
            async for event in self._loop():
                yield event
        finally:
            self._clear_active_plan()

    async def resume(self) -> AsyncIterator[Event]:
        """Continue a turn that was suspended at a prompt and persisted — durable resume after a
        restart (or engine eviction). Re-process the trailing assistant message's UNANSWERED
        tool-calls (the prompt callbacks find the already-resolved Inbox item and return without
        re-prompting; answered calls are skipped, so nothing double-executes), then run the model
        loop to finish the turn."""
        pending = self._unanswered_trailing_tool_calls()
        if not pending:
            return
        self._cancel.clear()
        self._activate_plan(self._resume_plan_input(), durable_resume=True)
        try:
            yield Event(EventType.TURN_START, {"input": "(resumed)"})
            async for event in self._handle_tool_calls(pending):
                yield event
            yield Event(EventType.ITERATION_END, {"iteration": 0})
            if not self._cancel.is_set():
                async for event in self._loop():
                    yield event
        finally:
            self._clear_active_plan()

    def _resume_plan_input(self) -> str | list:
        """Recover the persisted user request for conservative resume planning.

        Durable resume still routes through the full AGENT surface; the original text is
        used only so domain guards (notably D-166 market scope) survive a restart while
        an interactive Tool is pending.
        """

        for message in reversed(self.messages):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, (str, list)):
                return content
        return "(resumed)"

    def _unanswered_trailing_tool_calls(self) -> list[ToolCall]:
        """The tool-calls of the last assistant message that don't yet have a tool result —
        i.e. the prompt we suspended on (+ any after it). Reconstructed from the persisted thread.
        """
        answered = {
            m.get("tool_call_id") for m in self.messages if m.get("role") == "tool"
        }
        for msg in reversed(self.messages):
            if msg.get("role") == "user":
                return []
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                out: list[ToolCall] = []
                for tc in msg["tool_calls"]:
                    if tc.get("id") in answered:
                        continue
                    fn = tc.get("function") or {}
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except Exception:
                        args = {}
                    out.append(
                        ToolCall(id=tc.get("id"), name=fn.get("name"), arguments=args)
                    )
                return out
        return []

    def _emergency_finalization_active(self) -> bool:
        """Kill switch: profile flag wins when a profile is attached; else engine flag."""
        profile = self._current_execution_profile()
        if profile is not None:
            return bool(profile.emergency_finalization_enabled)
        return bool(self.emergency_finalization_enabled)

    def _should_emergency_finalize(self) -> bool:
        """True only at hard ceiling in a normal terminable state (HARD STOP G guards)."""
        if not self._emergency_finalization_active():
            return False
        if self._cancel.is_set():
            return False
        # Pending ask_user / approval / plan / request_directory / durable resume:
        # unanswered trailing tool calls mean the turn is still suspended.
        if self._unanswered_trailing_tool_calls():
            return False
        return True

    async def _emergency_finalize(self, iterations: int) -> AsyncIterator[Event]:
        """One tools-disabled model call; never re-enters the agent/tool loop."""
        self._emergency_finalizing = True
        turn: Optional[AssistantTurn] = None
        streamed: list[str] = []
        streamed_reasoning: list[str] = []
        try:
            try:
                async for chunk in self._astream():
                    if chunk.reasoning_delta:
                        streamed_reasoning.append(chunk.reasoning_delta)
                        yield Event(
                            EventType.REASONING_DELTA,
                            {"text": chunk.reasoning_delta},
                        )
                    if chunk.text_delta:
                        streamed.append(chunk.text_delta)
                        yield Event(
                            EventType.ASSISTANT_DELTA, {"text": chunk.text_delta}
                        )
                    if chunk.turn is not None:
                        turn = chunk.turn
            except Exception as exc:
                if streamed or streamed_reasoning:
                    self.messages.append(
                        _assistant_message(
                            AssistantTurn(
                                text="".join(streamed) or None,
                                reasoning="".join(streamed_reasoning) or None,
                            )
                        )
                    )
                friendly = friendly_model_error(self.model, exc)
                payload = {
                    "error": friendly or str(exc),
                    "error_type": type(exc).__name__,
                }
                if friendly:
                    payload["raw"] = str(exc)
                self._append_notice("error", friendly or str(exc))
                yield Event(EventType.ERROR, payload)
                return
            if self._cancel.is_set() and turn is None:
                if streamed or streamed_reasoning:
                    self.messages.append(
                        _assistant_message(
                            AssistantTurn(
                                text="".join(streamed) or None,
                                reasoning="".join(streamed_reasoning) or None,
                            )
                        )
                    )
                self._append_notice("interrupted")
                yield Event(EventType.INTERRUPTED, {"iterations": iterations})
                return
            if turn is None:
                turn = AssistantTurn(
                    text="".join(streamed) or None,
                    reasoning="".join(streamed_reasoning) or None,
                )
            # Tools are disabled: never execute or persist tool_calls from this call.
            if turn.tool_calls:
                turn = AssistantTurn(
                    text=turn.text,
                    reasoning=turn.reasoning,
                    finish_reason="stop",
                    usage=turn.usage,
                    extras=turn.extras,
                )
            assistant_msg = _assistant_message(turn, model=self.model)
            self.messages.append(assistant_msg)
            payload: dict[str, Any] = {
                "text": turn.text,
                "tool_calls": [],
            }
            if isinstance(assistant_msg.get("ts"), (int, float)):
                payload["ts"] = assistant_msg["ts"]
            if turn.reasoning:
                payload["reasoning"] = turn.reasoning
            if turn.usage is not None:
                payload["usage"] = {"model": self.model, **turn.usage.as_dict()}
            yield Event(EventType.ASSISTANT_MESSAGE, payload)
            yield Event(
                EventType.TURN_END,
                {
                    "status": "max_iterations_exceeded",
                    "iterations": iterations,
                    "best_effort_finalized": True,
                },
            )
        finally:
            self._emergency_finalizing = False

    async def _loop(self) -> AsyncIterator[Event]:
        iterations = 0
        profile = self._current_execution_profile()
        hard_limit = self.max_iterations
        if profile is not None:
            hard_limit = min(hard_limit, profile.max_iterations)
        while True:
            if iterations >= hard_limit:
                if self._should_emergency_finalize():
                    async for event in self._emergency_finalize(iterations):
                        yield event
                    return
                yield Event(
                    EventType.TURN_END,
                    {"status": "max_iterations_exceeded", "iterations": iterations},
                )
                return
            iterations += 1
            self._budget_iteration = iterations
            if iterations == 1:
                self._emit_turn_instrumentation()
            iter_started = time.perf_counter()
            first_visible_delta_ms: Optional[float] = None
            first_provider_delta_ms: Optional[float] = None

            # Auto-compaction checkpoint (OPE-27): between tool turns and before a new
            # turn's first call. Deliberately no "wrap up" warning to the model. The
            # COMPACTING signal precedes the (multi-second) summarizer call so surfaces
            # can show progress instead of a silent stall.
            notice = None
            if self._compaction_due():
                yield Event(EventType.COMPACTING, {})
                notice = await self._compact_now()
            if notice:
                self._append_notice("compacted", notice)
                yield Event(EventType.COMPACTED, {"text": notice})

            turn: Optional[AssistantTurn] = None
            streamed: list[str] = []
            streamed_reasoning: list[str] = []
            suppress_reasoning_delta = bool(
                self._active_turn_plan is not None
                and not self._active_turn_plan.show_reasoning
            )

            def _partial_turn() -> AssistantTurn:
                # What the user watched arrive — text and thinking, NO tool calls (any
                # half-formed calls would either orphan or execute against the stop).
                return AssistantTurn(
                    text="".join(streamed) or None,
                    reasoning="".join(streamed_reasoning) or None,
                )

            try:
                async for chunk in self._astream():
                    if first_provider_delta_ms is None and (
                        chunk.reasoning_delta
                        or chunk.text_delta
                        or chunk.turn is not None
                    ):
                        first_provider_delta_ms = (
                            time.perf_counter() - iter_started
                        ) * 1000.0
                    if chunk.reasoning_delta:
                        streamed_reasoning.append(chunk.reasoning_delta)
                        if first_visible_delta_ms is None:
                            first_visible_delta_ms = (
                                time.perf_counter() - iter_started
                            ) * 1000.0
                        if not suppress_reasoning_delta:
                            yield Event(
                                EventType.REASONING_DELTA,
                                {"text": chunk.reasoning_delta},
                            )
                    if chunk.text_delta:
                        streamed.append(chunk.text_delta)
                        if first_visible_delta_ms is None:
                            first_visible_delta_ms = (
                                time.perf_counter() - iter_started
                            ) * 1000.0
                        yield Event(
                            EventType.ASSISTANT_DELTA, {"text": chunk.text_delta}
                        )
                    if chunk.turn is not None:
                        turn = chunk.turn
            except Exception as exc:  # provider failure
                # A raw context-overflow 400 (compaction mispredicted, e.g. the estimate
                # path) routes into the compaction policy instead of surfacing. The retry
                # is progress-guarded: each pass moves the boundary forward or gives up,
                # so a model that keeps overflowing still terminates in the error path.
                if _compaction.is_context_overflow(exc) and not self._cancel.is_set():
                    yield Event(EventType.COMPACTING, {})
                    notice = await self._compact_now(force=True)
                    if notice:
                        self._append_notice("compacted", notice)
                        yield Event(EventType.COMPACTED, {"text": notice})
                        continue
                # Same contract as the stop path below: the partial the user watched
                # arrive survives the failure.
                if streamed or streamed_reasoning:
                    self.messages.append(_assistant_message(_partial_turn()))
                friendly = friendly_model_error(self.model, exc)
                payload = {
                    "error": friendly or str(exc),
                    "error_type": type(exc).__name__,
                }
                if friendly:
                    payload["raw"] = str(exc)
                self._append_notice("error", friendly or str(exc))
                yield Event(EventType.ERROR, payload)
                return
            if self._cancel.is_set() and turn is None:
                # Stopped mid-stream: persist exactly what the user watched arrive.
                if streamed or streamed_reasoning:
                    self.messages.append(_assistant_message(_partial_turn()))
                self._append_notice("interrupted")
                yield Event(EventType.INTERRUPTED, {"iterations": iterations})
                return
            if turn is None:
                # Compat gateways with a wrong base_url (missing /v1) often close the
                # stream with zero chunks. Persisting a blank assistant looks like
                # "chat returned nothing"; surface it as a retriable provider error.
                if not streamed and not streamed_reasoning:
                    msg = (
                        f"Model {self.model} returned an empty response. "
                        "For OpenAI-compatible gateways, confirm the base URL ends "
                        "with /v1 and that the selected model supports streaming."
                    )
                    self._append_notice("error", msg)
                    yield Event(
                        EventType.ERROR,
                        {"error": msg, "error_type": "EmptyModelResponse"},
                    )
                    return
                turn = _partial_turn()
            if turn.usage is not None:
                # The trigger signal: the prompt-side total that actually occupied the
                # window on this round-trip (estimate fallback when never reported).
                self._last_context_tokens = turn.usage.context_tokens

            assistant_msg = _assistant_message(turn, model=self.model)
            self.messages.append(assistant_msg)
            payload: dict[str, Any] = {
                "text": turn.text,
                "tool_calls": [tc.name for tc in turn.tool_calls],
            }
            # D-074: surface server ts so the GUI can target in-place mermaid repair.
            if isinstance(assistant_msg.get("ts"), (int, float)):
                payload["ts"] = assistant_msg["ts"]
            if turn.reasoning:
                payload["reasoning"] = turn.reasoning
            if turn.usage is not None:
                payload["usage"] = {"model": self.model, **turn.usage.as_dict()}
            yield Event(EventType.ASSISTANT_MESSAGE, payload)

            # Section 65 step 48: model-call metrics (no prompt / no tool bodies).
            phase = None
            profile = self._current_execution_profile()
            if profile is not None and profile.target_iterations is not None:
                from .execution_profile import budget_phase_for_iteration as _bpf

                phase_enum = _bpf(
                    iterations,
                    hard=profile.max_iterations,
                    target=profile.target_iterations,
                )
                phase = getattr(phase_enum, "value", str(phase_enum))
            emit_instrumentation(
                "model_call",
                build_model_call_snapshot(
                    iteration=iterations,
                    budget_phase=phase,
                    elapsed_ms=(time.perf_counter() - iter_started) * 1000.0,
                    first_visible_delta_ms=first_visible_delta_ms,
                    first_provider_delta_ms=first_provider_delta_ms,
                    tool_count=len(turn.tool_calls or []),
                    finish_reason=turn.finish_reason,
                    actual_prompt_tokens=(
                        turn.usage.context_tokens if turn.usage is not None else None
                    ),
                    reasoning_received=bool(streamed_reasoning or turn.reasoning),
                    reasoning_displayed=bool(
                        (streamed_reasoning or turn.reasoning)
                        and not suppress_reasoning_delta
                    ),
                    text_delta_count=len(streamed),
                    reasoning_delta_count=len(streamed_reasoning),
                ),
            )

            if not turn.tool_calls:
                if self._steering:
                    self._inject_steering()
                    continue
                yield Event(
                    EventType.TURN_END,
                    {"status": "completed", "iterations": iterations},
                )
                return

            # Section 65 step 47: record signatures before next outbound iteration.
            self._note_tool_signatures(turn.tool_calls)
            async for event in self._handle_tool_calls(turn.tool_calls):
                yield event

            yield Event(EventType.ITERATION_END, {"iteration": iterations})

            if self._cancel.is_set():
                self._append_notice("interrupted")
                yield Event(EventType.INTERRUPTED, {"iterations": iterations})
                return
            if self._steering:
                self._inject_steering()

    # -- auto-compaction (OPE-27) ------------------------------------------------
    def _compaction_config(self) -> dict[str, Any]:
        cfg = dict(self.compaction_settings() or {}) if self.compaction_settings else {}
        if not cfg.get("context_window"):
            from .providers.matrix import model_context_windows

            cfg["context_window"] = model_context_windows().get(self.model)
        cfg.setdefault("threshold_pct", _compaction.DEFAULT_THRESHOLD_PCT)
        cfg.setdefault("cap_tokens", _compaction.DEFAULT_CAP_TOKENS)
        return cfg

    def _compaction_due(self) -> bool:
        """The trigger check alone — cheap and side-effect free, so the loop can emit
        the COMPACTING signal before committing to the (slow) summarizer call."""
        cfg = self._compaction_config()
        if cfg.get("enabled") is False:
            return False
        signal = self._last_context_tokens or _compaction.estimate_tokens(
            self._outbound_messages()
        )
        return _compaction.should_compact(
            signal,
            cfg.get("context_window"),
            threshold_pct=float(cfg["threshold_pct"]),
            cap_tokens=int(cfg["cap_tokens"]),
        )

    async def _compact_now(self, *, force: bool = False) -> Optional[str]:
        """Run the compaction policy.

        Callers gate on `_compaction_due()` (or `force`, the overflow path). Returns the
        user-facing notice text when the outbound view changed, else None.

        Failure policy: retry once (both modes) and then auto-trim + continue.
        IMPORTANT: do not park / block the turn waiting for a user decision.
        """
        cfg = self._compaction_config()
        pct = float(cfg["threshold_pct"])
        cap = int(cfg["cap_tokens"])
        window = cfg.get("context_window")
        keep = int(
            _compaction.KEEP_RECENT_FRACTION
            * _compaction.trigger_tokens(window, threshold_pct=pct, cap_tokens=cap)
        )
        model = str(cfg.get("model") or "") or self.model
        from .providers.matrix import model_context_windows

        summary_context_window = (
            cfg.get("summary_context_window")
            or model_context_windows().get(model)
            or _compaction.SUMMARY_UNKNOWN_CONTEXT_WINDOW
        )
        input_override = int(cfg.get("summary_input_tokens") or 0) or None
        timeout_seconds = float(cfg.get("timeout_seconds") or 90)

        state: Optional[_compaction.CompactionState] = None
        failed = False
        # Attempt 0: normal summarizer input. Attempt 1: tighter span clip (less likely
        # to overflow/timeout the summarizer itself). Then Trim — never block the turn.
        for attempt in range(2):
            tight = attempt > 0
            budget = _compaction.summary_budget(
                summary_context_window,
                tight=tight,
                input_override=input_override,
            )

            def _build_attempt(
                *,
                _tight: bool = tight,
                _budget: _compaction.SummaryBudget = budget,
            ) -> Optional[_compaction.CompactionState]:
                return _compaction.build_state(
                    self.messages,
                    provider=self.provider,
                    model=model,
                    keep_tokens=keep,
                    prior=self.compaction_state,
                    tight_span=_tight,
                    budget=_budget,
                )

            started = time.monotonic()
            caught: Optional[Exception] = None
            try:
                state = await asyncio.wait_for(
                    asyncio.to_thread(_build_attempt),
                    timeout=timeout_seconds,
                )
                failed = False
                break
            except asyncio.TimeoutError:
                caught = _compaction.SummaryFailure(
                    "timeout",
                    input_tokens=budget.input_tokens,
                    cause_type="TimeoutError",
                )
            except Exception as exc:
                caught = exc
            failed = True
            assert caught is not None
            failure = caught if isinstance(caught, _compaction.SummaryFailure) else None
            _log.warning(
                "context summarizer failed attempt=%s/2 tight=%s model=%s "
                "reason=%s input_budget_tokens=%s input_tokens=%s input_chars=%s "
                "elapsed_ms=%s finish_reason=%s text_chars=%s reasoning_chars=%s "
                "error_type=%s",
                attempt + 1,
                tight,
                model,
                failure.reason if failure is not None else "provider_error",
                budget.input_tokens,
                failure.input_tokens if failure is not None else 0,
                failure.input_chars if failure is not None else 0,
                int((time.monotonic() - started) * 1000),
                failure.finish_reason if failure is not None else "",
                failure.text_chars if failure is not None else 0,
                failure.reasoning_chars if failure is not None else 0,
                failure.cause_type if failure is not None else type(caught).__name__,
            )
            if attempt == 0 and failure is not None and failure.reason == "rate_limited":
                await asyncio.sleep(0.1)
        if state is not None:
            self.compaction_state = state
            self._last_context_tokens = None  # stale once the outbound view shrank
            return "上下文已自动压缩（较早轮次已摘要）"
        if failed or force:
            try:
                trimmed = _compaction.build_deterministic_state(
                    self.messages,
                    keep_tokens=keep,
                    prior=self.compaction_state,
                )
            except Exception as exc:
                _log.warning(
                    "deterministic compaction failed error_type=%s",
                    type(exc).__name__,
                )
                trimmed = _compaction.trim_state(
                    self.messages, prior=self.compaction_state
                )
            if trimmed is not None:
                self.compaction_state = trimmed
                self._last_context_tokens = None
                return "上下文已自动精简以继续"
        return None

    # -- helpers ----------------------------------------------------------------
    async def _astream(self):
        """Bridge the provider's blocking stream generator to the async loop via a
        thread + queue, so text deltas surface live without blocking the event loop."""
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        # HARD STOP G: emergency finalization is model-only (tools disabled).
        if self._emergency_finalizing:
            tools = None
        else:
            tools = project_provider_visible_schemas(
                self.registry,
                tool_projection_enabled=self.tool_projection_enabled,
                profile=self._current_execution_profile(),
                tool_policy=self._current_tool_policy(),
                mandatory_tool_names=self.mandatory_tool_names,
            )
        model = self.model
        messages = self._outbound_messages()
        settings = dict(self.model_settings)
        profile = self._current_execution_profile()
        if profile is not None:
            # Route reasoning defaults only when an explicit profile is attached.
            # Legacy path keeps caller-provided model_settings untouched.
            supports_disable = False
            try:
                caps = self.provider.capabilities(model)
                supports_disable = bool(
                    getattr(caps, "supports_disable_reasoning", False)
                )
            except Exception:
                supports_disable = False
            settings = apply_reasoning_mode_settings(
                settings,
                profile.reasoning_mode,
                supports_disable_reasoning=supports_disable,
            )
        plan = self._active_turn_plan
        skill_count: Optional[int] = None
        if plan is not None:
            if plan.skill_names is not None:
                skill_count = len(plan.skill_names)
            else:
                loader = getattr(self, "skill_loader", None)
                if loader is not None:
                    try:
                        skill_count = len(loader.names())
                    except Exception:
                        skill_count = None
        prompt_profile = (
            plan.prompt_profile.value if plan is not None else PromptProfile.LEGACY.value
        )
        prompt_char_count = len(
            json.dumps(messages, ensure_ascii=False, default=str)
        )
        system_text = next(
            (
                message.get("content", "")
                for message in messages
                if message.get("role") == "system"
                and isinstance(message.get("content"), str)
            ),
            "",
        )
        prompt_section_count = len(
            [section for section in system_text.split("\n\n") if section.strip()]
        )
        schema_count = 0 if tools is None else len(tools)
        schema_bytes = 0 if tools is None else len(
            json.dumps(tools, ensure_ascii=False, default=str).encode("utf-8")
        )
        emit_instrumentation(
            "provider_call_shape",
            build_provider_call_shape_snapshot(
                prompt_profile=prompt_profile,
                prompt_char_count=prompt_char_count,
                prompt_token_estimate=_compaction.estimate_tokens(messages),
                prompt_section_count=prompt_section_count,
                schema_count=schema_count,
                schema_bytes=schema_bytes,
                skill_count=skill_count,
                reasoning_mode=(profile.reasoning_mode if profile is not None else None),
                show_reasoning=(plan.show_reasoning if plan is not None else True),
                projected_session=self._prompt_projection_eligible,
            ),
        )
        provider = self.provider
        structured_tools_streaming = self.structured_tools_true_streaming_enabled

        def produce():
            try:
                for chunk in provider.stream(
                    model=model,
                    messages=messages,
                    tools=tools,
                    structured_tools_true_streaming_enabled=structured_tools_streaming,
                    **settings,
                ):
                    # User pressed Stop: drop the stream between chunks (reading the
                    # asyncio.Event's flag from a thread is safe; we only read).
                    if self._cancel.is_set():
                        break
                    loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk))
            except Exception as exc:  # surfaced to the awaiting consumer
                loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

        loop.run_in_executor(None, produce)
        while True:
            # Race the queue against Stop so a stalled stream (no chunks arriving —
            # the pre-first-token wait, a wedged connection) can't hold the turn.
            get_task = asyncio.ensure_future(queue.get())
            cancel_task = asyncio.ensure_future(self._cancel.wait())
            done, _ = await asyncio.wait(
                {get_task, cancel_task}, return_when=asyncio.FIRST_COMPLETED
            )
            cancel_task.cancel()
            if get_task not in done:
                get_task.cancel()
                return  # interrupted — the producer exits on its own next chunk
            kind, payload = get_task.result()
            if kind == "chunk":
                yield payload
            elif kind == "error":
                raise payload
            else:
                return

    async def _handle_tool_calls(
        self, tool_calls: list[ToolCall]
    ) -> AsyncIterator[Event]:
        """Run one assistant turn's tool calls: authorize all of them first (sequentially —
        approval prompts are interactive), then execute. Low-risk calls (reads, searches)
        run concurrently; everything else runs one at a time in call order."""
        cleared: list[ToolCall] = []
        for tool_call in tool_calls:
            if self._cancel.is_set():
                # Stopped: every remaining call still gets an answer (no orphans).
                yield self._interrupted_tool(tool_call)
                continue
            yield Event(
                EventType.TOOL_PROPOSED,
                {"name": tool_call.name, "arguments": tool_call.arguments},
            )
            self._audit(tool_call, stage="proposed")
            # `request_directory` and `propose_plan` are interactive: the user decides
            # out-of-band and that decision IS the consent, so they skip the
            # permission/registry path.
            if tool_call.name == "request_directory":
                async for event in self._handle_directory_request(tool_call):
                    yield event
                continue
            if tool_call.name == "propose_plan":
                async for event in self._handle_plan_proposal(tool_call):
                    yield event
                continue
            if tool_call.name == "ask_user":
                async for event in self._handle_ask_user(tool_call):
                    yield event
                continue
            market_guard = self._market_tool_guard(tool_call.name)
            if market_guard is not None and not market_guard[0]:
                reason = market_guard[1]
                self.messages.append(_tool_error_message(tool_call, reason))
                self._audit(
                    tool_call,
                    stage="finished",
                    status="denied",
                    reason=reason,
                )
                yield Event(
                    EventType.TOOL_FINISHED,
                    {
                        "name": tool_call.name,
                        "status": "denied",
                        "reason": reason,
                    },
                )
                continue
            allowed = False
            async for item in self._authorize(tool_call):
                if isinstance(item, Event):
                    yield item
                else:
                    allowed = item
            if allowed:
                cleared.append(tool_call)

        concurrent = (
            [tc for tc in cleared if self._parallel_safe(tc)]
            if len(cleared) > 1
            else []
        )
        serial = [tc for tc in cleared if tc not in concurrent]

        if concurrent:
            for tool_call in concurrent:
                yield Event(EventType.TOOL_STARTED, {"name": tool_call.name})
                self._audit(tool_call, stage="started")
            outcomes = await asyncio.gather(
                *[asyncio.to_thread(self._execute_sync, tc) for tc in concurrent]
            )
            for tool_call, (result, status) in zip(concurrent, outcomes):
                yield self._record_result(tool_call, result, status)

        for tool_call in serial:
            if self._cancel.is_set():
                yield self._interrupted_tool(tool_call)
                continue
            yield Event(EventType.TOOL_STARTED, {"name": tool_call.name})
            self._audit(tool_call, stage="started")
            result, status = await asyncio.to_thread(self._execute_sync, tool_call)
            yield self._record_result(tool_call, result, status)

    def _market_tool_guard(self, tool_name: str) -> tuple[bool, str] | None:
        plan = self._active_turn_plan
        selection = plan.market_selection if plan is not None else None
        if selection is None:
            return None
        return selection.guard_tool(tool_name, self._resolved_market_scope)

    def _interrupted_tool(self, tool_call: ToolCall) -> Event:
        """The stop-path answer for a call that will not run: a tool-error result in the
        history (hosted chat templates reject orphaned tool_calls, and durable-resume
        would otherwise re-prompt it) + the finished event for the tool card."""
        self.messages.append(_tool_error_message(tool_call, "interrupted by user"))
        self._audit(
            tool_call, stage="finished", status="interrupted", reason="user stop"
        )
        return Event(
            EventType.TOOL_FINISHED,
            {"name": tool_call.name, "status": "interrupted", "reason": "stopped"},
        )

    def _parallel_safe(self, tool_call: ToolCall) -> bool:
        # Only metadata-declared low-risk tools (reads, searches, git queries, read-only
        # MCP) run concurrently. Approval already ran above; do not re-block on
        # requires_approval here or authorized MCP reads stay serial forever.
        spec = self.registry.get(tool_call.name)
        metadata = spec.metadata if spec else None
        return getattr(metadata, "risk_level", "") == "low"

    async def _authorize(self, tool_call: ToolCall) -> "AsyncIterator[Event | bool]":
        """Permission flow for one call (TOOL_PROPOSED is emitted by the caller). Yields
        its events, then True/False (allowed) last. Denied/unknown calls get their
        tool-error message appended here."""
        from .permissions import standing_rule_candidate

        spec = self.registry.get(tool_call.name)
        metadata = spec.metadata if spec else None

        decision = self.permissions.evaluate(
            tool_call.name, tool_call.arguments, metadata
        )
        allowed = decision.allowed
        reason = decision.reason

        if allowed and decision.rule:
            # A task-scoped standing rule auto-allowed this call: audit the exact rule
            # (§25 invariant — every auto-allowed call cites its rule) and remember it so
            # the tool card can say "allowed by standing rule".
            self._standing_notes[tool_call.id] = decision.rule
            self._audit(
                tool_call, stage="auto_allowed", status="allowed", reason=reason
            )

        if not allowed and decision.needs_user:
            yield Event(
                EventType.PERMISSION_REQUIRED,
                {
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                    "reason": decision.reason,
                    "category": getattr(metadata, "category", ""),
                    # The exact target a standing rule could pin, or None when the call
                    # isn't eligible (no declared target arg / exec risk). Surfaces use it
                    # to offer "Allow every time" on automation-run approval cards only.
                    "standing_target": standing_rule_candidate(
                        tool_call.name,
                        tool_call.arguments,
                        metadata,
                        self.permissions.risk_overrides,
                    ),
                },
            )
            self._audit(tool_call, stage="approval_requested", reason=decision.reason)
            outcome = await self._interruptible(
                self.approver(
                    PermissionRequest(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                        metadata=metadata,
                        reason=decision.reason,
                        tool_call_id=tool_call.id,
                    )
                ),
                interrupted=ApprovalOutcome.DENY,
            )
            if outcome is ApprovalOutcome.DENY:
                allowed, reason = (
                    False,
                    "interrupted by user" if self._cancel.is_set() else "denied by user",
                )
                self._audit(
                    tool_call,
                    stage="approval_resolved",
                    status="denied",
                    approval=outcome.value,
                    reason=reason,
                )
            else:
                if outcome is ApprovalOutcome.ALWAYS_TOOL:
                    self.permissions.allow_tool_for_session(tool_call.name)
                elif outcome is ApprovalOutcome.ALWAYS_COMMAND:
                    self.permissions.allow_command_for_session(
                        str(tool_call.arguments.get("command", ""))
                    )
                allowed, reason = True, "approved by user"
                self._audit(
                    tool_call,
                    stage="approval_resolved",
                    status="approved",
                    approval=outcome.value,
                    reason=reason,
                )

        if not allowed:
            if spec is None:
                reason = f"unknown tool: {tool_call.name}"
            self.messages.append(_tool_error_message(tool_call, reason))
            yield Event(
                EventType.TOOL_FINISHED,
                {"name": tool_call.name, "status": "denied", "reason": reason},
            )
            self._audit(tool_call, stage="finished", status="denied", reason=reason)
            yield False
            return

        if spec is None:
            self.messages.append(
                _tool_error_message(tool_call, f"unknown tool: {tool_call.name}")
            )
            yield Event(
                EventType.TOOL_FINISHED,
                {"name": tool_call.name, "status": "error", "reason": "unknown tool"},
            )
            yield False
            return

        yield True

    def _execute_sync(self, tool_call: ToolCall) -> tuple[Any, str]:
        """Execute one authorized call (runs in a worker thread)."""
        try:
            return self.registry.execute(tool_call.name, tool_call.arguments), "ok"
        except Exception as exc:
            return {"error": str(exc), "error_type": type(exc).__name__}, "error"

    def _record_result(self, tool_call: ToolCall, result: Any, status: str) -> Event:
        # A `_display` key on a tool result is user-facing metadata the AGENT must
        # never see (e.g. how many gmail hits the privacy filters hid — a count
        # the model could probe around). Lift it onto the message as a sidecar
        # (like `source`), stripped from every provider feed in
        # `_outbound_messages` but persisted for the GUI's tool card.
        display: Optional[dict[str, Any]] = None
        if isinstance(result, dict) and "_display" in result:
            display = result.get("_display") or None
            result = {k: v for k, v in result.items() if k != "_display"}
        message = _tool_result_message(tool_call, result)
        if display:
            message["_display"] = display
        self.messages.append(message)
        hidden = int((display or {}).get("hidden_by_filters") or 0)
        stripped = int((display or {}).get("hidden_fields") or 0)
        if hidden or stripped:
            # The out-of-band trace the user CAN see: rule class + count, never content.
            parts = []
            if hidden:
                parts.append(f"{hidden} result(s) hidden")
            if stripped:
                parts.append(f"{stripped} field value(s) stripped")
            self._audit(
                tool_call,
                stage="filtered",
                status="hidden",
                reason=" · ".join(parts) + " by privacy filters",
            )
        self._audit(
            tool_call,
            stage="finished",
            status=status,
            result=result,
            result_preview=_preview(result),
        )
        rule = self._standing_notes.pop(tool_call.id, "")
        return Event(
            EventType.TOOL_FINISHED,
            {
                "name": tool_call.name,
                "status": status,
                "result_preview": _preview(result),
                **({"display": display} if display else {}),
                **({"standing_rule": rule} if rule else {}),
                **chart_finished_sidecar(result),
            },
        )

    def _audit(self, tool_call: ToolCall, **event: Any) -> None:
        if self.audit_sink is None:
            return
        payload = {
            **self.audit_context,
            "tool": tool_call.name,
            "arguments": tool_call.arguments,
            **event,
        }
        try:
            self.audit_sink(payload)
        except Exception:
            pass

    async def _handle_plan_proposal(self, tool_call: ToolCall) -> AsyncIterator[Event]:
        """Emit the plan for review, await the user's out-of-band decision, and apply it:
        approval flips the live PermissionEngine out of plan mode (the same session keeps
        going, with all its exploration context); rejection keeps plan mode and returns
        the user's feedback so the agent can revise."""
        args = tool_call.arguments or {}
        plan = str(args.get("plan", ""))
        if self.permissions.mode is not Mode.PLAN:
            # The tool is always registered (mode can flip mid-session), but proposing a
            # plan only means something while the session is actually in plan mode. The
            # right next step differs by mode: discuss stays read-only, so the agent
            # should talk through the change; write-capable modes should just do it.
            if self.permissions.mode is Mode.DISCUSS:
                error = (
                    "not in plan mode — this is discuss mode (read-only), so describe "
                    "the proposed changes in chat instead"
                )
            else:
                error = "not in plan mode — proceed with the work directly"
            result: dict[str, Any] = {"approved": False, "error": error}
        elif self.plan_approver is None:
            result = {
                "approved": False,
                "error": "plan approval isn't available here",
            }
        else:
            yield Event(EventType.PLAN_PROPOSED, {"plan": plan})
            self._audit(tool_call, stage="plan_proposed")
            result = await self._interruptible(
                self.plan_approver(dict(args), tool_call.id),
                interrupted={"approved": False, "error": "interrupted by user"},
            ) or {
                "approved": False,
                "error": "no response",
            }

        if result.get("approved"):
            # The approver may pick the post-plan mode ("interactive" asks per write,
            # "auto" executes the approved plan without further prompts).
            try:
                self.permissions.mode = Mode(str(result.get("mode", "interactive")))
            except ValueError:
                self.permissions.mode = Mode.INTERACTIVE
            result = {
                **result,
                "mode": self.permissions.mode.value,
                "note": "plan approved — implement it now",
            }

        status = "ok" if result.get("approved") else "denied"
        self.messages.append(_tool_result_message(tool_call, result))
        self._audit(
            tool_call,
            stage="finished",
            status=status,
            result=result,
            result_preview=_preview(result),
        )
        yield Event(
            EventType.TOOL_FINISHED,
            {
                "name": tool_call.name,
                "status": status,
                "result_preview": _preview(result),
            },
        )

    async def _handle_directory_request(
        self, tool_call: ToolCall
    ) -> AsyncIterator[Event]:
        """Emit the grant prompt, await the user's out-of-band decision (which the requester also
        applies to this session's roots), and return the outcome as the tool result."""
        args = tool_call.arguments or {}
        if self.directory_requester is None:
            result: dict[str, Any] = {
                "granted": False,
                "error": "directory requests aren't available here",
            }
        else:
            yield Event(
                EventType.DIRECTORY_REQUESTED,
                {
                    "reason": str(args.get("reason", "")),
                    "path": str(args.get("path", "")),
                    "writable": bool(args.get("writable", False)),
                },
            )
            self._audit(
                tool_call,
                stage="directory_requested",
                reason=str(args.get("reason", "")),
            )
            result = await self._interruptible(
                self.directory_requester(dict(args), tool_call.id),
                interrupted={"granted": False, "error": "interrupted by user"},
            ) or {
                "granted": False,
                "error": "no response",
            }

        status = "ok" if result.get("granted") else "denied"
        self.messages.append(_tool_result_message(tool_call, result))
        self._audit(
            tool_call,
            stage="finished",
            status=status,
            result=result,
            result_preview=_preview(result),
        )
        yield Event(
            EventType.TOOL_FINISHED,
            {
                "name": tool_call.name,
                "status": status,
                "result_preview": _preview(result),
            },
        )

    async def _handle_ask_user(self, tool_call: ToolCall) -> AsyncIterator[Event]:
        """Emit the question, await the user's out-of-band answer (inline in the live session or
        from the Inbox when unattended), and return it as the tool result."""
        args = tool_call.arguments or {}
        question = str(args.get("question", "")).strip()
        if not question:
            for entry in args.get("questions") or []:
                if isinstance(entry, dict) and str(entry.get("question", "")).strip():
                    question = str(entry["question"]).strip()
                    break
        if self.question_asker is None or not question:
            result: dict[str, Any] = {
                "answer": "",
                "error": (
                    "no question was asked"
                    if not question
                    else "asking isn't available here"
                ),
            }
        else:
            # The asker is mode-aware (attended → live inline prompt; unattended → Inbox), so it
            # owns surfacing the question. The engine just awaits the answer.
            self._audit(tool_call, stage="question_requested", reason=question)
            result = await self._interruptible(
                self.question_asker(dict(args), tool_call.id),
                interrupted={"answer": "", "error": "interrupted by user"},
            ) or {
                "answer": "",
                "error": "no response",
            }

        plan = self._active_turn_plan
        selection = plan.market_selection if plan is not None else None
        if selection is not None and selection.needs_clarification:
            answer = result.get("answer") or result.get("answers")
            resolved_scope = selection.scope_from_answer(answer)
            if resolved_scope is not None:
                self._resolved_market_scope = resolved_scope
                self._last_resolved_market_scope = resolved_scope

        status = "ok" if (result.get("answer") or result.get("answers")) else "denied"
        self.messages.append(_tool_result_message(tool_call, result))
        self._audit(
            tool_call,
            stage="finished",
            status=status,
            result=result,
            result_preview=_preview(result),
        )
        yield Event(
            EventType.TOOL_FINISHED,
            {
                "name": tool_call.name,
                "status": status,
                "result_preview": _preview(result),
            },
        )

    def _inject_steering(self) -> None:
        for text, source in self._steering:
            message: dict[str, Any] = {
                "role": "user",
                "content": text,
                "ts": time.time(),
            }
            if source is not None:
                message["source"] = source
            self.messages.append(message)
        self._steering = []

    def _outbound_messages(self) -> list[dict[str, Any]]:
        """`self.messages` prepared for the provider. The SOLE provider feed (see `_astream`).

        Every message is stripped of the display-only sidecars — `source`, `_display`, and
        `ts` — (providers reject unknown keys), unconditionally — whether or not a
        `<system-context>` block is added. When a context
        provider yields a non-empty string, an ephemeral `<system-context>` block is appended to the
        last user message. Never mutates `self.messages`, so neither the strip nor the block is
        persisted/replayed.
        """
        # Strip the display-only sidecars — `source` (connector cards), `_display`
        # (e.g. filter-hidden counts), `ts` (append-time timestamps), `reasoning`
        # (thinking text), and `usage` (token counts) — copying only messages that carry
        # one. Whole `notice` messages (error/interrupted/model-switch markers) are
        # display-only too: dropped entirely.
        _SIDECARS = (
            "source",
            "_display",
            "_prompt_policy_version",
            "ts",
            "reasoning",
            "usage",
        )
        # Auto-compaction (OPE-27): everything before the boundary is represented by the
        # compacted block. Outbound-only — the canonical history stays intact — and the
        # block+tail are byte-stable between turns, so prompt caching keeps working.
        source_messages = _compaction.apply_to_outbound(
            self.messages, self.compaction_state
        )
        out: list[dict[str, Any]] = []
        for msg in source_messages:
            if msg.get("role") == "notice":
                continue
            prepared = msg
            if msg.get("role") == "assistant":
                reasoning = msg.get("reasoning")
                openai_sc = msg.get("_openai") or {}
                if (
                    isinstance(reasoning, str)
                    and reasoning
                    and not openai_sc.get("reasoning_content")
                ):
                    prepared = dict(msg)
                    prepared["_openai"] = {
                        **openai_sc,
                        "reasoning_content": reasoning,
                    }
            if any(s in prepared for s in _SIDECARS):
                out.append(
                    {k: v for k, v in prepared.items() if k not in _SIDECARS}
                )
            else:
                out.append(prepared)

        # D-165 prompt projection is outbound-only. Canonical history retains the
        # original complete system prompt plus a private policy marker, which makes
        # restart behavior stable while old sessions (no marker) stay legacy.
        projected_prompt = self._projected_prompt_text()
        if projected_prompt is not None:
            for index, message in enumerate(out):
                if message.get("role") != "system":
                    continue
                out[index] = {**message, "content": projected_prompt}
                break
        # PDF attachments (stored as `file` parts) are adapted to the ACTIVE model right
        # here — never in the persisted history — so a mid-session model switch always
        # re-decides: native PDF models get the real document, the rest get the local
        # text-extract/page-image fallback (pdf_support.py).
        if any(
            isinstance(p, dict) and p.get("type") == "file"
            for msg in out
            if isinstance(msg.get("content"), list)
            for p in msg["content"]
        ):
            caps = self.provider.capabilities(self.model)
            if not getattr(caps, "pdf", False):
                from . import pdf_support

                out = [
                    (
                        {
                            **msg,
                            "content": pdf_support.adapt_content(msg["content"], caps),
                        }
                        if isinstance(msg.get("content"), list)
                        else msg
                    )
                    for msg in out
                ]

        # Images get the same per-turn treatment: a model without vision receives a visible
        # placeholder instead of a payload it would reject. Like the PDF path, this re-decides
        # per call, so a mid-session switch to/from a vision model always does the right thing.
        if any(
            isinstance(p, dict) and p.get("type") == "image_url"
            for msg in out
            if isinstance(msg.get("content"), list)
            for p in msg["content"]
        ):
            caps = self.provider.capabilities(self.model)
            if not getattr(caps, "vision", False):
                placeholder = {
                    "type": "text",
                    "text": "[image attachment — not viewable by this model]",
                }
                out = [
                    (
                        {
                            **msg,
                            "content": [
                                (
                                    placeholder
                                    if isinstance(p, dict)
                                    and p.get("type") == "image_url"
                                    else p
                                )
                                for p in msg["content"]
                            ],
                        }
                        if isinstance(msg.get("content"), list)
                        else msg
                    )
                    for msg in out
                ]

        # Clamp tool/MCP result sizes in the outbound view so we cannot blow the model's
        # context window due to a single massive result. Overflow goes to workspace
        # artifacts for exact recovery.
        from .outbound_clip import clip_tool_result

        id_to_name: dict[str, str] = {}
        for msg in out:
            if msg.get("role") != "assistant":
                continue
            for tc in msg.get("tool_calls") or []:
                tid = tc.get("id")
                fn = tc.get("function") or {}
                if tid and fn.get("name"):
                    id_to_name[str(tid)] = str(fn["name"])

        cap_chars = 40_000
        for i in range(len(out)):
            msg = out[i]
            if msg.get("role") != "tool":
                continue
            content = msg.get("content")
            if not isinstance(content, str):
                continue
            clipped, _ = clip_tool_result(
                content,
                workspace_root=self.permissions.workspace_root,
                cap_chars=cap_chars,
                tool_name=id_to_name.get(str(msg.get("tool_call_id") or "")),
            )
            if clipped != content:
                msg = dict(msg)
                msg["content"] = clipped
                out[i] = msg

        context = (
            self.context_provider() if self.context_provider is not None else ""
        ) or ""
        budget_notice = self._budget_guidance_for_outbound()
        if budget_notice:
            context = f"{context}\n\n{budget_notice}".strip() if context else budget_notice
        dup_notice = self._duplicate_tool_warning_for_outbound()
        if dup_notice:
            context = f"{context}\n\n{dup_notice}".strip() if context else dup_notice
        # HARD STOP G: EF prompt is outbound-only (never persisted to canonical history).
        if self._emergency_finalizing:
            ef = _EMERGENCY_FINALIZATION_PROMPT
            context = f"{context}\n\n{ef}".strip() if context else ef
        if not context:
            return out
        block = f"\n\n<system-context>\n{context}\n</system-context>"
        for i in range(len(out) - 1, -1, -1):
            if out[i].get("role") != "user":
                continue
            msg = dict(out[i])
            content = msg.get("content")
            if isinstance(content, str):
                msg["content"] = content + block
            elif isinstance(content, list):  # content-parts (text + images)
                msg["content"] = [*content, {"type": "text", "text": block}]
            else:
                msg["content"] = block
            out[i] = msg
            break
        return out

    def _projected_prompt_text(self) -> Optional[str]:
        if not self._prompt_projection_eligible or self._active_turn_plan is None:
            return None
        profile = self._active_turn_plan.prompt_profile
        prompt = self.prompt_profiles.get(profile)
        return prompt if isinstance(prompt, str) and prompt else None

    def _budget_guidance_for_outbound(self) -> str:
        """Soft-target Explore→Converge→Deliver notice. Outbound-only; never mutates
        canonical history. Completely inert when no ExecutionProfile is attached or
        budget_guidance_enabled is false.
        """
        profile = self._current_execution_profile()
        if profile is None or not profile.budget_guidance_enabled:
            return ""
        target = profile.target_iterations
        if target is None:
            return ""
        hard = profile.max_iterations
        iteration = self._budget_iteration or 1
        phase = budget_phase_for_iteration(iteration, hard=hard, target=target)
        return (
            budget_guidance_text(phase, iteration=iteration, hard=hard) or ""
        )


def _assistant_message(turn: AssistantTurn, model: Optional[str] = None) -> dict[str, Any]:
    message: dict[str, Any] = {
        "role": "assistant",
        "content": turn.text or "",
        "ts": time.time(),
    }
    if turn.usage is not None:
        # Display/aggregation sidecar (like `reasoning`): persisted with the message,
        # stripped before provider calls. Tagged with the model that produced it so
        # per-model rollups survive mid-session model switches.
        message["usage"] = {"model": model, **turn.usage.as_dict()}
    if turn.reasoning:
        # Display-only thinking text — rendered by the GUI, stripped for every provider
        # (`_outbound_messages`); provider-private replay blocks go via `extras` instead.
        message["reasoning"] = turn.reasoning
    if turn.extras:
        # Provider-private sidecars (e.g. `_gemini` thought signatures) persist with the
        # message; the owning provider reattaches them, the rest strip them (base.py).
        message.update(turn.extras)
    if turn.tool_calls:
        message["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in turn.tool_calls
        ]
    return message


def _tool_result_message(tool_call: ToolCall, result: Any) -> dict[str, Any]:
    content = result if isinstance(result, str) else json.dumps(result, default=str)
    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": content,
        "ts": time.time(),
    }


def _tool_error_message(tool_call: ToolCall, reason: str) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": json.dumps({"error": "tool call not executed", "reason": reason}),
        "ts": time.time(),
    }


def chart_finished_sidecar(result: Any) -> dict[str, Any]:
    """Compact OHLC fields for GUI short-ref resolve (not the 300-char preview)."""
    if not isinstance(result, dict):
        return {}
    extra: dict[str, Any] = {}
    spec = result.get("chart_spec")
    if isinstance(spec, dict) and spec:
        extra["chart_spec"] = spec
    symbol = result.get("symbol")
    if isinstance(symbol, str) and symbol.strip():
        extra["symbol"] = symbol.strip()
    name = result.get("name")
    if isinstance(name, str) and name.strip():
        extra["name"] = name.strip()
    aliases = result.get("aliases")
    if isinstance(aliases, list):
        extra["aliases"] = [item for item in aliases if isinstance(item, str) and item.strip()]
    plot_status = result.get("status")
    if isinstance(plot_status, str) and plot_status.strip():
        extra["plot_status"] = plot_status.strip()
    err = result.get("error")
    if isinstance(err, str) and err.strip():
        extra["plot_error"] = err.strip()
    if "chart_spec" not in extra and "plot_error" not in extra:
        return {}
    return extra


def _preview(value: Any, max_chars: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = text.replace("\n", "\\n")
    return text if len(text) <= max_chars else text[: max_chars - 3] + "..."
