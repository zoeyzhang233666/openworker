"""D-161 live/offline helpers: classify ApiHub CN tools-enabled streaming.

No production import side effects. Live calls are opt-in via
``CHEMCLAW_LIVE_APIHUB_CN=1`` (see ``test_apihub_cn_structured_stream_live.py``).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from coworker.providers.base import StreamChunk
from coworker.providers.openai_provider import (
    _is_stream_transport_error,
    _salvage_tool_calls_from_text,
)

APIHUB_CN_HOST = "apihub.chem-cloud.cn"
APIHUB_CN_BASE_URL = "https://apihub.chem-cloud.cn/v1"
CN_GALLERY_MODELS = (
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "glm-5.2",
    "kimi-k3",
)
PROBE_TOKEN = "chemclaw-d161"
PROBE_RUNS = 3
MIN_ANSWER_DELTA_SPAN_MS = 200.0
PROMPT_VARIANT = "long_answer"
LIVE_ENV = "CHEMCLAW_LIVE_APIHUB_CN"
LIVE_MODELS_ENV = "CHEMCLAW_LIVE_APIHUB_CN_MODELS"
FIXTURE_RELATIVE = Path("docs/chemclaw/fixtures/apihub_cn_stream_capability.json")
ANSWER_USER_PROMPT = (
    f"echo_probe 已返回 token {PROBE_TOKEN}。本轮禁止再调用任何工具。"
    "请用简体中文写一份至少 12 句、合计至少 400 个汉字的简报。"
    "必须：第一句完整复述该 token；随后解释这次回声探针做了什么、"
    "为什么本轮不得再调工具；再列出五条带工具真流式安全检查"
    "（结构化 tool_calls、禁止把工具调用写进正文、text_delta 须增量到达、"
    "若有思考过程则须有 reasoning_delta、出现进度后不得断流）；"
    "最后用一句话再次重复该 token 作结。"
    "除 token 与工具名 echo_probe 外不要写英文。不要写短句敷衍。"
)

ECHO_PROBE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "echo_probe",
            "description": "Echo a token. No side effects. For streaming capability probes only.",
            "parameters": {
                "type": "object",
                "properties": {"token": {"type": "string"}},
                "required": ["token"],
            },
        },
    }
]


class ProbeBlocked(RuntimeError):
    """Missing key / rate limit / unreachable — ENV_BLOCKED, not a capability FAIL."""


@dataclass
class StreamRunRecord:
    model: str
    phase: str
    text_deltas: list[str] = field(default_factory=list)
    text_delta_times_ms: list[float] = field(default_factory=list)
    reasoning_deltas: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    joined_text: Optional[str] = None
    reasoning: Optional[str] = None
    salvage_would_fire: bool = False
    transport_error: Optional[str] = None
    transport_after_progress: bool = False
    blocked: bool = False
    blocked_reason: Optional[str] = None


def salvage_would_fire(text: Optional[str], tools: list[dict[str, Any]]) -> bool:
    if not text:
        return False
    return bool(_salvage_tool_calls_from_text(text, tools))


def text_delta_span_ms(rec: StreamRunRecord) -> float:
    times = rec.text_delta_times_ms
    if len(times) < 2:
        return 0.0
    return float(times[-1] - times[0])


def classify_tool_run(rec: StreamRunRecord) -> list[str]:
    """Return failure codes; empty means this tool round is clean."""
    if rec.blocked:
        return []
    reasons: list[str] = []
    if rec.transport_after_progress:
        reasons.append("transport_after_progress")
    elif rec.transport_error:
        reasons.append("transport_error")
    names = [c.get("name") for c in rec.tool_calls]
    if "echo_probe" not in names:
        reasons.append("no_structured_tool")
    if rec.salvage_would_fire:
        reasons.append("salvage_would_fire")
    return reasons


def classify_answer_run(rec: StreamRunRecord) -> list[str]:
    if rec.blocked:
        return []
    reasons: list[str] = []
    if rec.transport_after_progress:
        reasons.append("transport_after_progress")
    elif rec.transport_error:
        reasons.append("transport_error")
    if rec.salvage_would_fire:
        reasons.append("salvage_would_fire")
    if len(rec.text_deltas) < 2:
        reasons.append("answer_not_incremental")
    elif text_delta_span_ms(rec) < MIN_ANSWER_DELTA_SPAN_MS:
        reasons.append("answer_burst")
    if rec.reasoning and not rec.reasoning_deltas:
        reasons.append("reasoning_not_streamed")
    return reasons


def verdict_for_model(
    *,
    tool_reasons: list[list[str]],
    answer_reasons: list[list[str]],
    blocked: list[str],
    n: int = PROBE_RUNS,
) -> tuple[str, list[str]]:
    """Return (PASS|FAIL|ENV_BLOCKED, flattened reasons)."""
    if blocked and len(tool_reasons) < n:
        return "ENV_BLOCKED", list(blocked)
    flat: list[str] = []
    if len(tool_reasons) != n or len(answer_reasons) != n:
        flat.append("incomplete_runs")
    for batch in (*tool_reasons, *answer_reasons):
        flat.extend(batch)
    if flat:
        return "FAIL", flat
    return "PASS", []


def record_from_chunks(
    chunks: list[StreamChunk],
    *,
    model: str,
    phase: str,
    times_ms: Optional[list[tuple[str, float]]] = None,
) -> StreamRunRecord:
    rec = StreamRunRecord(model=model, phase=phase)
    time_iter = iter(times_ms or [])
    turn = None
    for chunk in chunks:
        if chunk.text_delta:
            rec.text_deltas.append(chunk.text_delta)
            stamped = next(time_iter, None)
            rec.text_delta_times_ms.append(
                stamped[1] if stamped and stamped[0] == "text" else 0.0
            )
        if chunk.reasoning_delta:
            rec.reasoning_deltas.append(chunk.reasoning_delta)
        if chunk.turn is not None:
            turn = chunk.turn
    if turn is not None:
        rec.joined_text = turn.text
        rec.reasoning = turn.reasoning
        rec.tool_calls = [
            {"id": c.id, "name": c.name, "arguments": c.arguments} for c in turn.tool_calls
        ]
    rec.salvage_would_fire = salvage_would_fire(rec.joined_text, ECHO_PROBE_TOOLS)
    return rec


def _is_env_blocked_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    markers = (
        "429",
        "rate limit",
        "401",
        "403",
        "invalid api key",
        "incorrect api key",
        "no apihub",
        "no api key",
        "connect timeout",
        "connection timed out",
        "name or service not known",
        "temporary failure in name resolution",
    )
    return any(m in text for m in markers)


def consume_forced_true_stream(
    provider: Any,
    *,
    model: str,
    messages: list[dict[str, Any]],
    phase: str,
) -> StreamRunRecord:
    """Run one Chat Completions stream with tools, forcing the true-stream path."""
    from coworker.providers import openai_provider as m

    original = m.is_known_safe_structured_tools_streaming
    rec = StreamRunRecord(model=model, phase=phase)
    t0 = time.perf_counter()
    progress = False
    try:
        m.is_known_safe_structured_tools_streaming = lambda *a, **k: True  # type: ignore[method-assign]
        for chunk in provider.stream(
            model=model,
            messages=messages,
            tools=ECHO_PROBE_TOOLS,
            structured_tools_true_streaming_enabled=True,
        ):
            now = (time.perf_counter() - t0) * 1000.0
            if chunk.text_delta:
                progress = True
                rec.text_deltas.append(chunk.text_delta)
                rec.text_delta_times_ms.append(now)
            if chunk.reasoning_delta:
                progress = True
                rec.reasoning_deltas.append(chunk.reasoning_delta)
            if chunk.turn is not None:
                rec.joined_text = chunk.turn.text
                rec.reasoning = chunk.turn.reasoning
                rec.tool_calls = [
                    {
                        "id": c.id,
                        "name": c.name,
                        "arguments": c.arguments,
                    }
                    for c in chunk.turn.tool_calls
                ]
                if chunk.turn.tool_calls:
                    progress = True
        rec.salvage_would_fire = salvage_would_fire(rec.joined_text, ECHO_PROBE_TOOLS)
        return rec
    except ProbeBlocked as exc:
        rec.blocked = True
        rec.blocked_reason = str(exc)
        return rec
    except Exception as exc:
        if _is_env_blocked_error(exc):
            rec.blocked = True
            rec.blocked_reason = type(exc).__name__ + ": " + str(exc)[:200]
            return rec
        rec.transport_error = type(exc).__name__ + ": " + str(exc)[:200]
        rec.transport_after_progress = bool(
            progress and _is_stream_transport_error(exc)
        )
        rec.salvage_would_fire = salvage_would_fire(rec.joined_text, ECHO_PROBE_TOOLS)
        return rec
    finally:
        m.is_known_safe_structured_tools_streaming = original


def product_chemclaw_secrets_path() -> Path:
    """Machine-global ChemClaw secrets.json, ignoring test COWORKER_STATE_DIR isolation."""
    import sys

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "ChemClaw" / "secrets.json"
    return Path.home() / ".config" / "chemclaw" / "secrets.json"


def build_apihub_cn_provider(*, product_store: bool = False) -> Any:
    from coworker.providers.registry import (
        build_provider_client,
        descriptor_configured,
        get_descriptor,
    )
    from coworker.secrets import SecretStore

    secrets = SecretStore(product_chemclaw_secrets_path() if product_store else None)
    profile = dict(secrets.get("provider:apihub-cn") or {})
    descriptor = get_descriptor("apihub-cn")
    if descriptor is None:
        raise ProbeBlocked("missing apihub-cn descriptor")
    if not descriptor_configured(descriptor, profile):
        raise ProbeBlocked("no ApiHub CN API key")
    return build_provider_client("apihub-cn", profile, secrets)


def _assistant_tool_message(calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": c.get("id") or f"call_{i}",
                "type": "function",
                "function": {
                    "name": c["name"],
                    "arguments": json.dumps(c.get("arguments") or {}, ensure_ascii=False),
                },
            }
            for i, c in enumerate(calls)
        ],
    }


def probe_model(provider: Any, model: str, *, n: int = PROBE_RUNS) -> dict[str, Any]:
    tool_reasons: list[list[str]] = []
    answer_reasons: list[list[str]] = []
    blocked: list[str] = []
    runs: list[dict[str, Any]] = []
    user_tool = (
        "Call echo_probe with token exactly "
        f"'{PROBE_TOKEN}'. Do not write other text."
    )
    user_answer = ANSWER_USER_PROMPT
    for _ in range(n):
        tool_rec = consume_forced_true_stream(
            provider,
            model=model,
            messages=[{"role": "user", "content": user_tool}],
            phase="tool",
        )
        runs.append(asdict(tool_rec))
        if tool_rec.blocked:
            blocked.append(tool_rec.blocked_reason or "blocked")
            break
        reasons = classify_tool_run(tool_rec)
        tool_reasons.append(reasons)
        echo = next((c for c in tool_rec.tool_calls if c.get("name") == "echo_probe"), None)
        if echo is None:
            answer_reasons.append(["skipped_no_tool"])
            continue
        tool_id = echo.get("id") or "call_echo"
        token = (echo.get("arguments") or {}).get("token", "")
        answer_rec = consume_forced_true_stream(
            provider,
            model=model,
            messages=[
                {"role": "user", "content": user_tool},
                _assistant_tool_message([echo]),
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": f"ok:{token or PROBE_TOKEN}",
                },
                {"role": "user", "content": user_answer},
            ],
            phase="answer",
        )
        runs.append(asdict(answer_rec))
        if answer_rec.blocked:
            blocked.append(answer_rec.blocked_reason or "blocked")
            break
        answer_reasons.append(classify_answer_run(answer_rec))
    verdict, reasons = verdict_for_model(
        tool_reasons=tool_reasons,
        answer_reasons=answer_reasons,
        blocked=blocked,
        n=n,
    )
    return {
        "verdict": verdict,
        "reasons": reasons,
        "runs": runs,
    }


def selected_live_models(raw: Optional[str] = None) -> tuple[str, ...]:
    """Gallery subset from ``CHEMCLAW_LIVE_APIHUB_CN_MODELS`` (comma-separated)."""
    text = (raw if raw is not None else os.environ.get(LIVE_MODELS_ENV, "")).strip()
    if not text:
        return CN_GALLERY_MODELS
    chosen = tuple(part.strip() for part in text.split(",") if part.strip())
    unknown = [name for name in chosen if name not in CN_GALLERY_MODELS]
    if unknown:
        raise ValueError(f"unknown ApiHub CN gallery model(s): {unknown}")
    return chosen


def run_gallery_probe(
    *,
    n: int = PROBE_RUNS,
    models: Optional[tuple[str, ...]] = None,
) -> dict[str, Any]:
    from datetime import datetime, timezone

    gallery = models or CN_GALLERY_MODELS
    stamped = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision = "D-164" if gallery != CN_GALLERY_MODELS else "D-163"
    try:
        provider = build_apihub_cn_provider(product_store=True)
    except ProbeBlocked as exc:
        blocked_models = {
            model: {
                "verdict": "ENV_BLOCKED",
                "reasons": [str(exc)],
                "runs": [],
            }
            for model in gallery
        }
        return {
            "decision": decision,
            "host": APIHUB_CN_HOST,
            "probed_at": stamped,
            "n_runs": n,
            "prompt_variant": PROMPT_VARIANT,
            "min_answer_delta_span_ms": MIN_ANSWER_DELTA_SPAN_MS,
            "reprobe_models": list(gallery),
            "models": blocked_models,
        }
    rows = {}
    for model in gallery:
        print(f"{decision} probe: {model}", flush=True)
        rows[model] = probe_model(provider, model, n=n)
        print(f"{decision} probe: {model} -> {rows[model]['verdict']}", flush=True)
    return {
        "decision": decision,
        "host": APIHUB_CN_HOST,
        "probed_at": stamped,
        "n_runs": n,
        "prompt_variant": PROMPT_VARIANT,
        "min_answer_delta_span_ms": MIN_ANSWER_DELTA_SPAN_MS,
        "reprobe_models": list(gallery),
        "models": rows,
    }


def load_fixture(path: Optional[Path] = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    dest = path or (root / FIXTURE_RELATIVE)
    return json.loads(dest.read_text(encoding="utf-8"))


def merge_fixture_report(existing: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Overlay probed model rows onto the existing gallery fixture."""
    merged = dict(existing)
    for key in (
        "decision",
        "host",
        "probed_at",
        "n_runs",
        "prompt_variant",
        "min_answer_delta_span_ms",
        "reprobe_models",
    ):
        if key in update:
            merged[key] = update[key]
    models = dict(existing.get("models") or {})
    models.update(update.get("models") or {})
    merged["models"] = models
    return merged


def pass_pairs_from_report(report: dict[str, Any]) -> frozenset[tuple[str, str]]:
    host = str(report.get("host") or APIHUB_CN_HOST)
    out: set[tuple[str, str]] = set()
    for model, row in (report.get("models") or {}).items():
        if (row or {}).get("verdict") == "PASS":
            out.add((host, str(model)))
    return frozenset(out)


def write_fixture(report: dict[str, Any], path: Optional[Path] = None) -> Path:
    root = Path(__file__).resolve().parents[1]
    dest = path or (root / FIXTURE_RELATIVE)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dest
