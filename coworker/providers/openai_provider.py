"""OpenAI Chat Completions provider — the compat workhorse.

Uses the OpenAI Python SDK `chat.completions` API only, which is what the entire
OpenAI-compatible world implements: the compat vendors (DeepSeek, Z AI, Kimi, …),
resellers, Ollama, custom endpoints (Azure OpenAI, vLLM), and the Bedrock/Vertex MaaS
paths. Native OpenAI models (the `openai` provider with no custom endpoint) route to
`openai_responses.OpenAIResponsesProvider` instead — Chat Completions rejects function
tools combined with reasoning on GPT-5.6+, so reasoning + tools needs `/v1/responses`.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

from .base import (
    AssistantTurn,
    ModelCapabilities,
    ProviderClient,
    StreamChunk,
    TokenUsage,
    ToolCall,
)
from .capabilities import capabilities_for

_log = logging.getLogger(__name__)


def resolve_api_key(secrets: Any = None) -> Optional[str]:
    """Resolve the OpenAI API key: env `OPENAI_API_KEY` first, else the SecretStore
    `provider:openai` profile (`{api_key}`). Lets a Tauri-launched sidecar — which does NOT
    inherit the shell env — still find a key the user entered in Settings. The value never
    enters the model context; it only configures the SDK client.
    """
    import os

    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    if secrets is not None:
        profile = secrets.get("provider:openai") or {}
        return profile.get("api_key") or None
    return None


# GPT-5.6 (2026-07) defaults reasoning_effort to "medium" server-side, and
# /v1/chat/completions rejects function tools combined with any effort other than
# "none" ("use /v1/responses"). Native OpenAI now routes to the Responses provider,
# but GPT-5.6 can still land here through a custom endpoint (Azure OpenAI serves the
# same wire), so keep pinning effort to none whenever tools ride along on these
# models — and when the API rejects a call with that exact complaint anyway (a future
# generation, an alias we didn't list), retry once at effort none so the user gets a
# working turn instead of a 400.
_EFFORT_ERROR = "function tools with reasoning_effort are not supported"


def _pin_reasoning_effort(kwargs: dict[str, Any]) -> None:
    if kwargs.get("tools") and str(kwargs.get("model", "")).startswith("gpt-5.6"):
        kwargs.setdefault("reasoning_effort", "none")


def _delta_reasoning(obj: Any) -> Optional[str]:
    """Thinking text off a delta/message: `reasoning_content` (DeepSeek, GLM, Kimi, and
    most compat vendors) or `reasoning` (xAI, OpenRouter). Extra response fields survive
    the OpenAI SDK's models (extra="allow"), so plain getattr sees them."""
    value = getattr(obj, "reasoning_content", None) or getattr(obj, "reasoning", None)
    return value if isinstance(value, str) and value else None


def _reasoning_extras(reasoning: Optional[str]) -> dict[str, Any]:
    """Persist thinking text for DeepSeek-style replay (`reasoning_content` on the wire)."""
    return {"_openai": {"reasoning_content": reasoning}} if reasoning else {}


def _replay_reasoning(message: dict[str, Any]) -> Optional[str]:
    """Thinking text to send back on the Chat Completions wire."""
    sidecar = (message.get("_openai") or {}).get("reasoning_content")
    if isinstance(sidecar, str) and sidecar:
        return sidecar
    legacy = message.get("reasoning")
    return legacy if isinstance(legacy, str) and legacy else None


def _prepare_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """OpenAI-chat history → wire-safe messages for `/v1/chat/completions`.

    DeepSeek thinking mode requires prior assistant `reasoning_content` on follow-up
    turns (especially with tools). Replay from the `_openai` sidecar, with a fallback
    to the display-only `reasoning` sidecar for older sessions. Strip underscore-prefixed
    provider keys and display sidecars before the HTTP call.
    """
    _DISPLAY = frozenset({"reasoning"})
    prepared: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") == "assistant":
            replay = _replay_reasoning(message)
            if replay or any(
                k.startswith("_") or k in _DISPLAY for k in message
            ):
                wire = {
                    k: v
                    for k, v in message.items()
                    if not k.startswith("_") and k not in _DISPLAY
                }
                if replay:
                    wire["reasoning_content"] = replay
                prepared.append(wire)
                continue
        if any(k.startswith("_") for k in message):
            prepared.append({k: v for k, v in message.items() if not k.startswith("_")})
        else:
            prepared.append(message)
    return prepared


_MAX_TOKENS_ERROR = "'max_tokens' is not supported"
_UNSUPPORTED_PARAM = re.compile(r"unsupported (?:parameter|value)s?:?\s*'([^']+)'")


def _param_fix_retry(kwargs: dict[str, Any], exc: Exception) -> dict[str, Any]:
    """Kwargs for the one retry an unsupported-parameter error earns, or re-raise.

    Reasoning-routed OpenAI models reject `max_tokens` outright (they want
    `max_completion_tokens`) — but compat servers (Ollama's /v1) know ONLY
    `max_tokens`, so the swap must happen on rejection, never up front. Same
    contract as the reasoning_effort retry: fix exactly what the server named.
    """
    msg = str(exc).lower()
    if _EFFORT_ERROR in msg and kwargs.get("reasoning_effort") != "none":
        return {**kwargs, "reasoning_effort": "none"}
    if _MAX_TOKENS_ERROR in msg and "max_tokens" in kwargs:
        fixed = dict(kwargs)
        fixed["max_completion_tokens"] = fixed.pop("max_tokens")
        return fixed
    if "stream_options" in msg and "stream_options" in kwargs:
        # Older compat servers don't know the usage opt-in; drop it, lose only metering.
        fixed = dict(kwargs)
        fixed.pop("stream_options")
        return fixed
    match = _UNSUPPORTED_PARAM.search(msg)
    if match:
        param = match.group(1).split(".", 1)[0].split("[", 1)[0]
        if param in kwargs and param not in ("model", "messages"):
            fixed = dict(kwargs)
            fixed.pop(param, None)
            return fixed
    raise exc


def _usage_from(usage: Any) -> Optional[TokenUsage]:
    """chat.completions usage → normalized counts. `prompt_tokens` INCLUDES cached
    tokens, so the cached share is subtracted into `cache_read`; no write-side split
    exists on this API shape."""
    if usage is None:
        return None
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    details = getattr(usage, "prompt_tokens_details", None)
    cached = int(getattr(details, "cached_tokens", 0) or 0)
    return TokenUsage(
        input=max(prompt - cached, 0),
        output=int(getattr(usage, "completion_tokens", 0) or 0),
        cache_read=cached,
    )


# ChemClaw owns streaming transport retry (progress-gated). Keep attempts conservative so we
# do not stack SDK retries + many ChemClaw attempts + complete() fallback.
MAX_STREAM_ATTEMPTS = 2

# HARD STOP F: ChemClaw-internal stream() kwarg — never forwarded to the OpenAI API.
_STRUCTURED_TOOLS_STREAMING_SETTING = "structured_tools_true_streaming_enabled"

# Per-conversation transport context for OpenCode Go. The engine/router may pass this
# through ProviderClient settings, but this adapter must consume it before SDK kwargs are
# built so it can never become part of the Chat Completions JSON body.
_OPENCODE_SESSION_SETTING = "_opencode_session_id"
_OPENCODE_SESSION_HEADER = "x-opencode-session"


def _is_opencode_go_endpoint(base_url: Optional[str]) -> bool:
    """Match the OpenCode Go API by parsed host and path, not a broad substring."""
    if not base_url:
        return False
    parsed = urlparse(base_url)
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    if (parsed.hostname or "").lower() != "opencode.ai":
        return False
    path = "/" + "/".join(part for part in parsed.path.split("/") if part)
    return path == "/zen/go/v1" or path.startswith("/zen/go/v1/")


def _apply_opencode_session_header(
    settings: dict[str, Any], *, base_url: Optional[str], session_id: Any
) -> None:
    """Add the conversation header as a per-request OpenAI SDK option when required."""
    value = str(session_id or "").strip()
    if not value or not _is_opencode_go_endpoint(base_url):
        return
    headers = dict(settings.get("extra_headers") or {})
    headers[_OPENCODE_SESSION_HEADER] = value
    settings["extra_headers"] = headers

# Conservative known-safe matrix for tools-enabled true streaming. Being
# "OpenAI-compatible" alone is never enough — unknown/custom hosts stay salvage-safe.
_KNOWN_SAFE_STRUCTURED_TOOL_MODEL_PREFIXES = ("gpt-4", "gpt-5", "o1", "o3", "o4")

# D-161/D-163/D-164: exact (hostname, bare model id) pairs verified by live probe.
# Never prefix-match. D-164 Flash long-answer N=3 PASS; D-163 Pro/GLM PASS;
# kimi-k3 unpriced.
_KNOWN_SAFE_COMPAT_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("apihub.chem-cloud.cn", "deepseek-v4-flash"),
        ("apihub.chem-cloud.cn", "deepseek-v4-pro"),
        ("apihub.chem-cloud.cn", "glm-5.2"),
    }
)


def is_known_safe_structured_tools_streaming(
    model: str, *, base_url: Optional[str] = None
) -> bool:
    """True only for explicitly allowlisted provider/model hosts.

    Stock OpenAI Chat Completions (``base_url is None`` / ``api.openai.com``) and
    Azure OpenAI hosts with GPT-/o-family model names qualify. Reseller / ApiHub /
    Ollama / DashScope / arbitrary custom endpoints do not — even when the model
    string looks like ``gpt-*`` — unless the exact ``(hostname, model)`` pair is
    listed in ``_KNOWN_SAFE_COMPAT_PAIRS`` (D-161/D-163/D-164 live PASS only).
    """
    name = model.split(":", 1)[-1].lower()
    host = (urlparse(base_url).hostname or "").lower() if base_url else ""
    if host and (host, name) in _KNOWN_SAFE_COMPAT_PAIRS:
        return True
    if not name.startswith(_KNOWN_SAFE_STRUCTURED_TOOL_MODEL_PREFIXES):
        return False
    if not base_url:
        return True
    if host == "api.openai.com":
        return True
    if host == "openai.azure.com" or host.endswith(".openai.azure.com"):
        return True
    return False


def _should_true_stream_with_tools(
    *,
    model: str,
    base_url: Optional[str],
    enabled: bool,
) -> bool:
    """Kill switch ON + known-safe matrix → tools-enabled true streaming; else compat."""
    return bool(enabled) and is_known_safe_structured_tools_streaming(
        model, base_url=base_url
    )


def _sdk_client_kwargs(
    *,
    api_key: str,
    base_url: Optional[str] = None,
    streaming_retry_owned: bool = False,
) -> dict[str, Any]:
    """Shared OpenAI SDK constructor kwargs.

    Streaming clients set ``max_retries=0`` so ChemClaw's provider_progress gate is the only
    retry owner. Non-stream / ``complete()`` clients omit that override and keep SDK defaults.
    """
    import httpx

    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "timeout": httpx.Timeout(
            connect=15.0,
            read=300.0,
            write=30.0,
            pool=15.0,
        ),
    }
    if base_url:
        kwargs["base_url"] = base_url
    if streaming_retry_owned:
        kwargs["max_retries"] = 0
    return kwargs


class OpenAIProvider(ProviderClient):
    def __init__(
        self,
        client: Any = None,
        *,
        default_model: str = "gpt-5.6-sol",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        secrets: Any = None,
    ):
        # The SDK client is built lazily on first use, NOT at construction. This lets an engine
        # be assembled before any key exists — the desktop app lets you enter the key in Settings
        # *after* launch — and the super-agent engine to be built at startup with no key. The key
        # is resolved at call time: explicit `api_key` → env `OPENAI_API_KEY` → SecretStore. Tests
        # inject a `client` directly, bypassing all of this.
        #
        # `base_url` points the same OpenAI SDK at any OpenAI-compatible endpoint — used by the
        # provider router for Ollama (`http://localhost:11434/v1`, with a placeholder key) and,
        # later, other OpenAI-shaped backends. When None, behavior is identical to stock OpenAI.
        self._client = client
        self._client_injected = client is not None
        self._api_key = api_key
        self._base_url = base_url
        self._secrets = secrets
        self.default_model = default_model

    def _make_sdk_client(self, *, streaming_retry_owned: bool = False) -> Any:
        """Build a new OpenAI SDK client from current key/base_url settings."""
        from openai import OpenAI

        key = self._api_key or resolve_api_key(self._secrets)
        if not key:
            raise RuntimeError(
                "No model API key configured. Set OPENAI_API_KEY in the environment, "
                "or add your key in Manage → Settings."
            )
        return OpenAI(
            **_sdk_client_kwargs(
                api_key=key,
                base_url=self._base_url,
                streaming_retry_owned=streaming_retry_owned,
            )
        )

    def _ensure_client(self) -> Any:
        if self._client is None:
            # Lazy import so the SDK is only required when actually talking to OpenAI.
            # Non-stream path keeps SDK retry ownership (streaming_retry_owned=False).
            self._client = self._make_sdk_client(streaming_retry_owned=False)
        return self._client

    def _stream_client(self) -> tuple[Any, bool]:
        """Client for one stream() call.

        Injected test clients are reused. Production builds a fresh SDK client per stream so
        concurrent session turns (each on a thread-pool worker via TurnEngine._astream) do not
        share one httpx connection pool — overlapping chunked bodies on a shared client show up
        as APIConnectionError("Connection error.") on the background turn.
        Returns (client, close_after).
        """
        if self._client_injected:
            return self._client, False
        return self._make_sdk_client(streaming_retry_owned=True), True

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        **settings: Any,
    ) -> AssistantTurn:
        opencode_session_id = settings.pop(_OPENCODE_SESSION_SETTING, None)
        _apply_opencode_session_header(
            settings, base_url=self._base_url, session_id=opencode_session_id
        )
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _prepare_messages(messages),
            **settings,
        }
        if tools:
            kwargs["tools"] = tools
        _pin_reasoning_effort(kwargs)

        client = self._ensure_client()
        # Up to two param-fix retries: effort and max_tokens can BOTH need fixing.
        for _ in range(2):
            try:
                response = client.chat.completions.create(**kwargs)
                break
            except Exception as exc:
                kwargs = _param_fix_retry(kwargs, exc)
        else:
            response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message
        text = getattr(message, "content", None)
        tool_calls = _parse_tool_calls(getattr(message, "tool_calls", None))
        text, tool_calls = _maybe_salvage_tool_calls(text, tool_calls, tools=tools)
        reasoning = _delta_reasoning(message)
        return AssistantTurn(
            text=text,
            tool_calls=tool_calls,
            finish_reason=getattr(choice, "finish_reason", None),
            raw=response,
            reasoning=reasoning,
            extras=_reasoning_extras(reasoning),
            usage=_usage_from(getattr(response, "usage", None)),
        )

    def capabilities(self, model: str) -> ModelCapabilities:
        return capabilities_for(model)

    def stream(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        **settings: Any,
    ):
        # ChemClaw-internal kill switch — never forward to the OpenAI request body.
        structured_tools_streaming = bool(
            settings.pop(_STRUCTURED_TOOLS_STREAMING_SETTING, False)
        )
        opencode_session_id = settings.pop(_OPENCODE_SESSION_SETTING, None)
        _apply_opencode_session_header(
            settings, base_url=self._base_url, session_id=opencode_session_id
        )
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _prepare_messages(messages),
            "stream": True,
            # Usage on the final chunk (empty choices). Compat servers that reject
            # the option get a one-shot retry without it (_param_form_retry).
            "stream_options": {"include_usage": True},
            **settings,
        }
        if tools:
            kwargs["tools"] = tools
        _pin_reasoning_effort(kwargs)
        client, close_after = self._stream_client()

        # Transport retry is ChemClaw-owned and progress-gated:
        # - no semantic provider progress → at most one retry, then optional complete()
        # - any text / reasoning / structured tool / textual-tool candidate → never regenerate
        #
        # Streaming path selection (HARD STOP B + F):
        # - tools=None → always true streaming
        # - tools enabled + kill switch ON + known-safe → true streaming (structured only)
        # - otherwise → compat-buffered + textual salvage
        true_stream_tools = tools is not None and _should_true_stream_with_tools(
            model=model,
            base_url=self._base_url,
            enabled=structured_tools_streaming,
        )
        try:
            last_transport: Optional[BaseException] = None
            for attempt in range(MAX_STREAM_ATTEMPTS):
                progress = {"seen": False}
                if tools is None:
                    stream_mode = "direct"
                elif true_stream_tools:
                    stream_mode = "structured"
                else:
                    stream_mode = "compat_buffered"
                try:
                    from ..turn_instrumentation import (
                        build_provider_stream_snapshot,
                        emit_instrumentation,
                    )

                    emit_instrumentation(
                        "provider_stream",
                        build_provider_stream_snapshot(
                            stream_attempt=attempt + 1,
                            stream_mode=stream_mode,
                        ),
                    )
                except Exception:
                    pass
                try:
                    if tools is None or true_stream_tools:
                        yield from _iter_true_stream_chunks(
                            client, kwargs, progress=progress
                        )
                    else:
                        buffered = _collect_stream_chunks(
                            client, kwargs, tools=tools, progress=progress
                        )
                        for chunk in buffered:
                            yield chunk
                    return
                except Exception as exc:
                    if not _is_stream_transport_error(exc):
                        raise
                    last_transport = exc
                    try:
                        from ..turn_instrumentation import (
                            build_provider_stream_snapshot,
                            emit_instrumentation,
                        )

                        emit_instrumentation(
                            "provider_stream",
                            build_provider_stream_snapshot(
                                stream_attempt=attempt + 1,
                                stream_mode=stream_mode,
                                provider_progress_seen=bool(progress.get("seen")),
                                transport_failure_type=type(exc).__name__,
                                retried=attempt + 1 < MAX_STREAM_ATTEMPTS
                                and not progress.get("seen"),
                            ),
                        )
                    except Exception:
                        pass
                    if progress["seen"]:
                        raise
                    continue

            turn = self.complete(
                model=model,
                messages=messages,
                tools=tools,
                **{**settings, _OPENCODE_SESSION_SETTING: opencode_session_id},
            )
            if last_transport is not None and not (
                turn.text or turn.tool_calls or turn.reasoning
            ):
                raise last_transport
            yield StreamChunk(turn=turn)
        finally:
            if close_after:
                close = getattr(client, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass



def _is_stream_transport_error(exc: BaseException) -> bool:
    """True when a compat gateway dropped the chunked HTTP body mid-stream."""
    text = str(exc).lower()
    name = type(exc).__name__.lower()
    markers = (
        "incomplete chunked read",
        "peer closed connection",
        "remoteprotocolerror",
        "server disconnected",
        "connection reset",
        "incompleteread",
        # OpenAI SDK APIConnectionError default message; also common when a shared
        # httpx client loses a concurrent stream mid-body.
        "connection error",
        # Gateway / SDK read budget exceeded before first semantic progress (D-184).
        "timed out",
        "apitimeouterror",
        "readtimeout",
        "request timeout",
    )
    if any(m in text for m in markers) or any(m in name for m in markers):
        return True
    if name.endswith("timeouterror") or name.endswith("timeout"):
        return True
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if cause is not None and cause is not exc:
        return _is_stream_transport_error(cause)
    return False


def _open_chat_completion_stream(client: Any, kwargs: dict[str, Any]) -> Any:
    """Open one upstream chat.completions stream with param-form retries only."""
    req = dict(kwargs)
    # Up to two param-form retries: effort and max_tokens can BOTH need fixing.
    for _ in range(2):
        try:
            return client.chat.completions.create(**req)
        except Exception as exc:
            if _is_stream_transport_error(exc):
                raise
            req = _param_fix_retry(req, exc)
    return client.chat.completions.create(**req)


def _mark_provider_progress(progress: Optional[dict[str, bool]]) -> None:
    if progress is not None:
        progress["seen"] = True


def _accumulate_structured_tool_delta(
    tool_accum: dict[int, dict[str, str]], tc: Any
) -> None:
    acc = tool_accum.setdefault(
        getattr(tc, "index", 0), {"id": "", "name": "", "args": ""}
    )
    if getattr(tc, "id", None):
        acc["id"] = tc.id
    fn = getattr(tc, "function", None)
    if fn is not None:
        if getattr(fn, "name", None):
            acc["name"] = fn.name
        if getattr(fn, "arguments", None):
            acc["args"] += fn.arguments


def _finalize_tool_calls(
    tool_accum: dict[int, dict[str, str]],
) -> list[ToolCall]:
    tool_calls: list[ToolCall] = []
    for index in sorted(tool_accum):
        acc = tool_accum[index]
        try:
            arguments = json.loads(acc["args"]) if acc["args"] else {}
        except (TypeError, json.JSONDecodeError):
            arguments = {"_raw": acc["args"]}
        tool_calls.append(
            ToolCall(id=acc["id"], name=acc["name"], arguments=arguments)
        )
    return tool_calls


def _iter_true_stream_chunks(
    client: Any,
    kwargs: dict[str, Any],
    *,
    progress: Optional[dict[str, bool]] = None,
):
    """``tools is None`` path: parse and yield each semantic delta immediately."""
    chunks = _open_chat_completion_stream(client, kwargs)

    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_accum: dict[int, dict[str, str]] = {}
    finish_reason = None
    usage: Optional[TokenUsage] = None

    for chunk in chunks:
        chunk_usage = _usage_from(getattr(chunk, "usage", None))
        if chunk_usage is not None:
            usage = chunk_usage
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue
        choice = choices[0]
        delta = getattr(choice, "delta", None)
        if delta is not None:
            reasoning = _delta_reasoning(delta)
            if reasoning:
                _mark_provider_progress(progress)
                reasoning_parts.append(reasoning)
                yield StreamChunk(reasoning_delta=reasoning)
            content = getattr(delta, "content", None)
            if content:
                _mark_provider_progress(progress)
                text_parts.append(content)
                yield StreamChunk(text_delta=content)
            for tc in getattr(delta, "tool_calls", None) or []:
                _mark_provider_progress(progress)
                _accumulate_structured_tool_delta(tool_accum, tc)
        if getattr(choice, "finish_reason", None):
            finish_reason = choice.finish_reason

    tool_calls = _finalize_tool_calls(tool_accum)
    reasoning = "".join(reasoning_parts) or None
    yield StreamChunk(
        turn=AssistantTurn(
            text="".join(text_parts) or None,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            reasoning=reasoning,
            extras=_reasoning_extras(reasoning),
            usage=usage,
        )
    )


def _collect_stream_chunks(
    client: Any,
    kwargs: dict[str, Any],
    *,
    tools: Optional[list[dict[str, Any]]],
    progress: Optional[dict[str, bool]] = None,
) -> list[StreamChunk]:
    """Tools-enabled compatibility path: buffer one attempt, then salvage-safe yield.

    Param-form retries (effort / max_tokens / stream_options) still apply on create().
    Transport errors during iteration propagate to the caller for retry/fallback.
    Intermediate text deltas that are salvaged into tool_calls are dropped so potential
    tool-call text never reaches the UI as assistant deltas.
    """
    chunks = _open_chat_completion_stream(client, kwargs)

    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_accum: dict[int, dict[str, str]] = {}
    finish_reason = None
    usage: Optional[TokenUsage] = None
    out: list[StreamChunk] = []

    for chunk in chunks:
        chunk_usage = _usage_from(getattr(chunk, "usage", None))
        if chunk_usage is not None:
            usage = chunk_usage
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue
        choice = choices[0]
        delta = getattr(choice, "delta", None)
        if delta is not None:
            reasoning = _delta_reasoning(delta)
            if reasoning:
                _mark_provider_progress(progress)
                reasoning_parts.append(reasoning)
                out.append(StreamChunk(reasoning_delta=reasoning))
            content = getattr(delta, "content", None)
            if content:
                # Text while tools were offered counts as semantic progress even before
                # salvage — may be prose or a textual tool-call candidate.
                _mark_provider_progress(progress)
                text_parts.append(content)
                out.append(StreamChunk(text_delta=content))
            for tc in getattr(delta, "tool_calls", None) or []:
                _mark_provider_progress(progress)
                _accumulate_structured_tool_delta(tool_accum, tc)
        if getattr(choice, "finish_reason", None):
            finish_reason = choice.finish_reason

    tool_calls = _finalize_tool_calls(tool_accum)
    text, tool_calls = _maybe_salvage_tool_calls(
        "".join(text_parts) or None, tool_calls, tools=tools
    )
    if text is None and tool_calls:
        # Salvaged textual tool calls must not have leaked as ASSISTANT_DELTA fodder.
        out = [c for c in out if not c.text_delta]
    reasoning = "".join(reasoning_parts) or None
    out.append(
        StreamChunk(
            turn=AssistantTurn(
                text=text,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                reasoning=reasoning,
                extras=_reasoning_extras(reasoning),
                usage=usage,
            )
        )
    )
    return out



def _parse_tool_calls(raw_tool_calls: Any) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for tc in raw_tool_calls or []:
        function = tc.function
        raw_args = getattr(function, "arguments", None)
        try:
            arguments = json.loads(raw_args) if raw_args else {}
        except (TypeError, json.JSONDecodeError):
            # Surface unparseable arguments rather than dropping the call; the engine
            # can return a tool-error so the model corrects itself.
            arguments = {"_raw": raw_args}
        calls.append(
            ToolCall(id=getattr(tc, "id", ""), name=function.name, arguments=arguments)
        )
    return calls


# Some OpenAI-compatible backends — notably Ollama for several local models (qwen, etc.) —
# fail to populate the structured `tool_calls` field and instead emit the call as TEXT, in
# wildly varied shapes: a `<tool_call>{…}</tool_call>` block, a bare `{"name","arguments"}` object
# (often mixed in with prose), or a `toolname {args}` / `toolname [args]` shorthand. Our agent
# loop needs structured calls, so we recover them — using the requested tool SCHEMAS to recognize
# tool-name forms and to filter out anything whose name isn't a real tool (no false positives).
# Gated on: tools were requested AND no structured calls came back. Never fires for OpenAI.
_TOOLCALL_OPEN = re.compile(r"<tool_call>\s*", re.IGNORECASE)

# Qwen/Hermes native tool-call template — NOT JSON. The model writes the call as nested XML:
#   <function=write_file><parameter=path>hello.txt</parameter><parameter=content>hi</parameter></function>
# (usually wrapped in <tool_call>…</tool_call>). qwen3-coder emits exactly this, so we parse the
# function/parameter tags directly. Values are taken verbatim (stripped); only no-whitespace JSON
# tokens (numbers, bools, objects/arrays) are coerced, so free-text content stays a string.
_FUNCTION_BLOCK = re.compile(
    r"<function\s*=\s*(?P<name>[^>\s]+)\s*>(?P<body>.*?)</function\s*>",
    re.IGNORECASE | re.DOTALL,
)
_PARAM_BLOCK = re.compile(
    r"<parameter\s*=\s*(?P<key>[^>\s]+)\s*>(?P<val>.*?)</parameter\s*>",
    re.IGNORECASE | re.DOTALL,
)


def _coerce_param(raw: str) -> Any:
    """Keep free-text verbatim (the common case: file content), but recover real JSON values when
    the whole token is unambiguous JSON (no embedded whitespace) — e.g. `3`, `true`, `{"a":1}`.
    """
    s = raw.strip()
    if s and not any(c.isspace() for c in s):
        v = _loads(s)
        if isinstance(v, (dict, list, int, float, bool)):
            return v
    return s


def _maybe_salvage_tool_calls(
    text: Optional[str],
    tool_calls: list[ToolCall],
    *,
    tools: Optional[list[dict[str, Any]]],
) -> tuple[Optional[str], list[ToolCall]]:
    """If the model returned tool calls as text, convert them. Returns (text, tool_calls):
    on success the salvaged calls replace `tool_calls` and `text` is cleared."""
    if tool_calls or not tools or not text:
        return text, tool_calls
    salvaged = _salvage_tool_calls_from_text(text, tools)
    if salvaged:
        try:
            from ..turn_instrumentation import (
                build_provider_stream_snapshot,
                emit_instrumentation,
            )

            emit_instrumentation(
                "provider_stream",
                build_provider_stream_snapshot(
                    stream_attempt=0,
                    stream_mode="compat_buffered",
                    tool_progress_seen=True,
                    textual_tool_salvage_used=True,
                ),
            )
        except Exception:
            pass
        return None, salvaged
    return text, tool_calls


def _tool_index(
    tools: Optional[list[dict[str, Any]]],
) -> tuple[Optional[set[str]], dict[str, Optional[str]]]:
    """(known tool names, {name: sole-parameter-name}) from OpenAI tool schemas. The sole-param
    map lets us map a bare `toolname [args]` to `{param: args}` when a tool has one parameter.
    """
    if not tools:
        return None, {}
    names: set[str] = set()
    single: dict[str, Optional[str]] = {}
    for t in tools:
        fn = (t or {}).get("function") or {}
        name = fn.get("name")
        if not isinstance(name, str) or not name:
            continue
        names.add(name)
        params = fn.get("parameters") or {}
        props = params.get("properties") or {}
        if len(props) == 1:
            single[name] = next(iter(props))
        else:
            required = params.get("required") or []
            single[name] = required[0] if len(required) == 1 else None
    return names, single


def _loads(s: str) -> Any:
    try:
        return json.loads(s)
    except (TypeError, json.JSONDecodeError):
        return None


def _extract_balanced(text: str, start: int) -> Optional[str]:
    """Return the balanced `{…}`/`[…]` substring beginning at `text[start]` (string-aware), or
    None if it doesn't close — so nested braces/brackets are handled correctly."""
    open_ch = text[start]
    close_ch = "]" if open_ch == "[" else "}"
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _iter_top_objects(text: str):
    """Yield balanced `{…}` substrings at brace-depth 0 (array brackets ignored), so embedded
    JSON objects are found even amid surrounding prose."""
    i = 0
    while i < len(text):
        if text[i] == "{":
            sub = _extract_balanced(text, i)
            if sub:
                yield sub
                i += len(sub)
                continue
        i += 1


def _call_from_dict(d: Any, names: Optional[set[str]]) -> Optional[ToolCall]:
    """Build a ToolCall from a `{"name","arguments"}` dict, or None if it isn't one / the name
    isn't a known tool."""
    if not isinstance(d, dict):
        return None
    name = d.get("name")
    if not isinstance(name, str) or not name:
        return None
    if names is not None and name not in names:
        return None
    args = d.get("arguments", d.get("parameters"))
    if args is None:
        args = {}
    if isinstance(args, str):
        args = _loads(args)
        if not isinstance(args, dict):
            args = {"_raw": d.get("arguments")}
    if not isinstance(args, dict):
        args = {"_raw": args}
    return ToolCall(id="", name=name, arguments=args)


def _renumber(calls: list[ToolCall]) -> list[ToolCall]:
    return [
        ToolCall(id=f"call_salvaged_{i}", name=c.name, arguments=c.arguments)
        for i, c in enumerate(calls)
    ]


def _salvage_tool_calls_from_text(
    content: str, tools: Optional[list[dict[str, Any]]] = None
) -> list[ToolCall]:
    """Best-effort recovery of tool calls embedded in assistant text. Tries, in order:
    1. `<tool_call>…</tool_call>` blocks (anywhere, balanced); 2. embedded `{"name","arguments"}`
    objects (even mixed with prose); 3. `toolname {args}` / `toolname [args]` for known tools.
    Returns [] (treat as plain text) when nothing tool-shaped is found."""
    text = (content or "").strip()
    if not text:
        return []
    names, single = _tool_index(tools)

    # 1) <tool_call> … </tool_call> blocks.
    calls: list[ToolCall] = []
    for m in _TOOLCALL_OPEN.finditer(text):
        j = m.end()
        if j < len(text) and text[j] in "{[":
            sub = _extract_balanced(text, j)
            parsed = _loads(sub) if sub else None
            for d in parsed if isinstance(parsed, list) else [parsed]:
                c = _call_from_dict(d, names)
                if c:
                    calls.append(c)
    if calls:
        return _renumber(calls)

    # 1b) Qwen/Hermes XML calls: <function=NAME><parameter=KEY>VAL</parameter>…</function>.
    for fm in _FUNCTION_BLOCK.finditer(text):
        name = fm.group("name").strip()
        if names is not None and name not in names:
            continue
        args = {
            pm.group("key").strip(): _coerce_param(pm.group("val"))
            for pm in _PARAM_BLOCK.finditer(fm.group("body"))
        }
        calls.append(ToolCall(id="", name=name, arguments=args))
    if calls:
        return _renumber(calls)

    # 2) Embedded {"name": …, "arguments": …} objects, even surrounded by prose.
    for sub in _iter_top_objects(text):
        d = _loads(sub)
        if isinstance(d, dict) and "name" in d:
            c = _call_from_dict(d, names)
            if c:
                calls.append(c)
    if calls:
        return _renumber(calls)

    # 3) `toolname {args}` / `toolname [args]` shorthand — only for tools we actually offered.
    if names:
        for name in names:
            for m in re.finditer(re.escape(name) + r"\s*[:=]?\s*", text):
                j = m.end()
                if j >= len(text) or text[j] not in "{[":
                    continue
                sub = _extract_balanced(text, j)
                parsed = _loads(sub) if sub else None
                if parsed is None:
                    continue
                if isinstance(parsed, dict):
                    args = parsed
                else:
                    param = single.get(name)
                    if not param:
                        continue
                    args = {param: parsed}
                calls.append(ToolCall(id="", name=name, arguments=args))
                break  # one salvaged call per tool name
    return _renumber(calls)
