"""D-165 live GUI-WebSocket → SessionManager → ApiHub probe.

Manual only (uses the user's configured ApiHub credential):

    python tests/apihub_cn_d165_gui_probe.py --output path/to/result.json

The JSON contains timings/counts only; prompts, credentials and response bodies are
never persisted.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import statistics
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from coworker.compaction import estimate_tokens
from coworker.providers import (
    ProviderClient,
    ProviderRouter,
    descriptor_configured,
    get_descriptor,
)
from coworker.secrets import SecretStore
from coworker.server import SessionManager, create_app


class ShapeRecordingProvider(ProviderClient):
    def __init__(self, inner: ProviderClient) -> None:
        self.inner = inner
        self.calls: list[dict[str, Any]] = []
        self.complete_calls = 0

    def capabilities(self, model):
        return self.inner.capabilities(model)

    def complete(self, *, model, messages, tools=None, **settings):
        self.complete_calls += 1
        return self.inner.complete(
            model=model, messages=messages, tools=tools, **settings
        )

    def stream(self, *, model, messages, tools=None, **settings):
        call = {
            "model": model,
            "tool_count": 0 if tools is None else len(tools),
            "prompt_token_estimate": estimate_tokens(messages),
            "chunk_count": 0,
            "reasoning_chunk_count": 0,
            "text_chunk_count": 0,
        }
        self.calls.append(call)
        for chunk in self.inner.stream(
            model=model, messages=messages, tools=tools, **settings
        ):
            call["chunk_count"] += 1
            if chunk.reasoning_delta:
                call["reasoning_chunk_count"] += 1
            if chunk.text_delta:
                call["text_chunk_count"] += 1
            yield chunk


class PerfCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if not message.startswith("chemclaw.perf "):
            return
        try:
            _prefix, event, payload = message.split(" ", 2)
            self.rows.append({"event": event, **json.loads(payload)})
        except Exception:
            return


def _run_ws_turn(client: TestClient, session_id: str, text: str) -> dict[str, Any]:
    started = time.perf_counter()
    first_visible_ms = None
    events: list[dict[str, Any]] = []
    with client.websocket_connect(f"/ws/session/{session_id}?agent=cowork") as ws:
        ready = ws.receive_json()
        if ready.get("type") != "ready":
            raise RuntimeError(f"unexpected ready event: {ready.get('type')}")
        ws.send_json({"type": "user_message", "text": text})
        while True:
            event = ws.receive_json()
            events.append(event)
            if event.get("type") in {"reasoning_delta", "assistant_delta"}:
                if first_visible_ms is None:
                    first_visible_ms = (time.perf_counter() - started) * 1000.0
            if event.get("type") == "turn_done":
                break
    assistant = next(
        (event for event in reversed(events) if event.get("type") == "assistant_message"),
        {},
    )
    usage = (assistant.get("data") or {}).get("usage") or {}
    prompt_tokens = sum(
        int(usage.get(key, 0) or 0) for key in ("input", "cache_read", "cache_write")
    )
    errors = [event for event in events if event.get("type") == "error"]
    return {
        "first_visible_ms": first_visible_ms,
        "elapsed_ms": (time.perf_counter() - started) * 1000.0,
        "prompt_tokens": prompt_tokens or None,
        "reasoning_event_count": sum(
            event.get("type") == "reasoning_delta" for event in events
        ),
        "text_event_count": sum(
            event.get("type") == "assistant_delta" for event in events
        ),
        "errors": [
            {
                "error_type": (event.get("data") or {}).get("error_type"),
                "has_error": True,
            }
            for event in errors
        ],
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/chemclaw/fixtures/apihub_cn_d165_gui_probe.json"),
    )
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    secret = SecretStore()
    descriptor = get_descriptor("apihub-cn")
    profile = secret.get("provider:apihub-cn") or {}
    if descriptor is None or not descriptor_configured(descriptor, profile):
        payload = {"status": "ENV_BLOCKED", "reason": "missing_apihub_cn_credential"}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 2

    perf = PerfCapture()
    perf_logger = logging.getLogger("coworker.turn_instrumentation")
    perf_logger.addHandler(perf)
    perf_logger.setLevel(logging.INFO)

    inner = ProviderRouter(secret, default_provider="openai")
    provider = ShapeRecordingProvider(inner)
    state = Path(".local") / f"d165-live-{uuid.uuid4().hex[:8]}"
    manager = SessionManager(
        data_dir=state,
        model="apihub-cn:deepseek-v4-flash",
        provider=provider,
    )
    client = TestClient(create_app(manager))
    prefix = f"d165-{uuid.uuid4().hex[:8]}"
    greetings: list[dict[str, Any]] = []
    status = "PASS"
    try:
        for index in range(max(1, args.runs)):
            result = _run_ws_turn(client, f"{prefix}-hello-{index}", "你好")
            engine = manager.get_engine(f"{prefix}-hello-{index}", agent="cowork")
            plan = engine._last_turn_plan if engine is not None else None
            result.update(
                {
                    "route": (
                        plan.decision.route.value
                        if plan is not None and plan.decision is not None
                        else None
                    ),
                    "allowed_tool_count": (
                        0
                        if plan is not None
                        and plan.execution_profile is not None
                        and not plan.execution_profile.tools_enabled
                        else None
                    ),
                    "skill_count": (
                        len(plan.skill_names)
                        if plan is not None and plan.skill_names is not None
                        else None
                    ),
                }
            )
            greetings.append(result)

        long_answer = _run_ws_turn(
            client,
            f"{prefix}-long",
            "请用至少 800 字详细解释为什么海水是咸的，分成四段。",
        )
    except Exception as exc:
        status = "ENV_BLOCKED"
        long_answer = {"errors": [{"error_type": type(exc).__name__, "has_error": True}]}
    finally:
        perf_logger.removeHandler(perf)

    visible = [
        float(row["first_visible_ms"])
        for row in greetings
        if isinstance(row.get("first_visible_ms"), (int, float))
    ]
    stream_rows = [row for row in perf.rows if row.get("event") == "provider_stream"]
    direct_rows = [row for row in stream_rows if row.get("stream_mode") == "direct"]
    fallback_rows = [row for row in stream_rows if row.get("fallback_used")]
    if status == "PASS":
        checks = [
            all((row.get("prompt_tokens") or 10**9) <= 4_000 for row in greetings),
            all(row.get("allowed_tool_count") == 0 for row in greetings),
            all(row.get("skill_count") == 0 for row in greetings),
            len(direct_rows) >= len(greetings) + 1,
            not fallback_rows,
            (statistics.median(visible) if visible else 10**9) <= 3_000,
            (_percentile(visible, 0.95) or 10**9) <= 8_000,
            int(long_answer.get("text_event_count", 0) or 0) >= 3,
            not any(row.get("errors") for row in greetings),
            not long_answer.get("errors"),
        ]
        status = "PASS" if all(checks) else "FAIL"

    payload = {
        "status": status,
        "model": "apihub-cn:deepseek-v4-flash",
        "runs": len(greetings),
        "greetings": greetings,
        "ttft_p50_ms": statistics.median(visible) if visible else None,
        "ttft_p95_ms": _percentile(visible, 0.95),
        "long_answer": long_answer,
        "provider_call_shapes": provider.calls,
        "provider_stream_modes": {
            "direct": len(direct_rows),
            "fallback": len(fallback_rows),
        },
        # SessionManager generates one small non-streaming title per new session.
        # Main-answer complete fallbacks are measured by provider_stream.fallback.
        "autotitle_complete_calls": provider.complete_calls,
        "main_answer_complete_fallbacks": len(fallback_rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
