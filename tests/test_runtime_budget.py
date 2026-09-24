import asyncio
from types import SimpleNamespace

import pytest

from coworker.context_budget import budget_request
from coworker.providers.model_profile import resolve_model_profile, validate_overrides
from coworker.compaction import SummaryFailure, summarize_span
from coworker.events import Event, EventType
from coworker.providers.base import TokenUsage, AssistantTurn
from coworker.tracing.recorder import TurnTraceRecorder
from tests.test_compaction_engine import CompactingProvider, long_history, make_engine, collect


def test_endpoint_scoped_override_and_estimated_unknown():
    first = resolve_model_profile("custom", provider="openai", endpoint="https://example.org/v1")
    assert first.source == "estimated"
    settings = {first.key: {"context_window": 1_000_000, "max_output_tokens": 16_000}}
    resolved = resolve_model_profile("custom", provider="openai", endpoint="https://example.org/v1/", overrides=settings)
    assert resolved.context_window == 1_000_000 and resolved.source == "override"
    assert resolve_model_profile("custom", endpoint="https://other.org/v1", overrides=settings).source == "estimated"
    assert "secret" not in resolve_model_profile("x", endpoint="https://user:secret@e.org/v1?api_key=secret").endpoint
    with pytest.raises(ValueError):
        validate_overrides({"context_window": True})


def test_budget_includes_schema_output_reserve_and_new_result_delta():
    args = dict(window=128_000, max_output=16_000, threshold=.95, cap=1_000_000)
    messages = [{"role": "user", "content": "query"}]
    schemas = [{"function": {"name": f"tool{i}", "description": "schema " * 80}} for i in range(400)]
    before = budget_request(messages, schemas, **args)
    after = budget_request(messages + [{"role": "tool", "content": "中文结果" * 2000}], schemas,
                           last_actual=before.estimated_input + 1000, last_estimate=before.estimated_input, **args)
    assert before.schema_tokens > 40_000
    assert before.trigger <= 128_000 - 16_000 - 2_048
    assert after.estimated_input > before.estimated_input + 1000


def test_trace_usage_counts_cached_context_and_cumulative_output():
    recorder = TurnTraceRecorder(session_id="test", model="test", plan=None)
    for _ in range(2):
        recorder.observe(Event(EventType.ASSISTANT_MESSAGE, {"usage": TokenUsage(input=100, cache_read=900, output=20).as_dict()}))
    result = recorder.finish()
    assert (result.input_tokens, result.output_tokens, result.total_tokens) == (2000, 40, 2040)


def test_summary_rejects_tiny_reply_and_omits_unverified_reasoning():
    seen = {}
    def complete(**kwargs):
        seen.update(kwargs)
        return AssistantTurn(text="continue")
    with pytest.raises(SummaryFailure, match="invalid_summary"):
        summarize_span(SimpleNamespace(complete=complete), "custom", [{"role": "user", "content": "task"}])
    assert "reasoning_effort" not in seen


def test_invalid_request_does_not_compact_history(tmp_path):
    class Invalid(CompactingProvider):
        def complete(self, **kwargs):
            raise RuntimeError("invalid_request_error: unsupported reasoning parameter")
    engine = make_engine(tmp_path, Invalid([]), messages=long_history(), cap=1_000_000)
    events = collect(engine)
    assert any(e.type == EventType.ERROR for e in events)
    assert not any(e.type == EventType.COMPACTING for e in events)


def test_summary_bad_request_breaker_and_safe_diagnostics(tmp_path):
    class BadRequest(Exception):
        status_code = 400
        body = {"error": {"code": "unsupported_parameter", "param": "reasoning_effort", "message": "secret"}}
    class InvalidSummary(CompactingProvider):
        def complete(self, **kwargs):
            if "compacting an AI coworker" in str(kwargs['messages'][0].get('content')):
                self.summary_calls.append(kwargs)
                raise BadRequest("secret")
            return AssistantTurn(text="done")
    provider = InvalidSummary([])
    engine = make_engine(tmp_path, provider, messages=long_history(), cap=1600)
    collect(engine)
    assert len(provider.summary_calls) == 1
    assert engine.compaction_state.diagnostics["summary_failure"]["param"] == "reasoning_effort"
    assert "secret" not in str(engine.compaction_state.diagnostics)
    assert engine.compaction_state.transcript_path
