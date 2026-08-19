"""D-161: ApiHub CN exact (host, model) streaming safety table — no network."""

from __future__ import annotations

from coworker.providers.openai_provider import is_known_safe_structured_tools_streaming

APIHUB_CN = "https://apihub.chem-cloud.cn/v1"
CN_GALLERY = (
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "glm-5.2",
    "kimi-k3",
)


def test_known_safe_compat_pairs_match_live_pass_only():
    """Production allowlist is exactly the live fixture PASS set."""
    import json
    from pathlib import Path

    from coworker.providers.openai_provider import _KNOWN_SAFE_COMPAT_PAIRS
    from tests.apihub_cn_stream_probe import FIXTURE_RELATIVE, pass_pairs_from_report

    root = Path(__file__).resolve().parents[1]
    report = json.loads((root / FIXTURE_RELATIVE).read_text(encoding="utf-8"))
    assert report.get("prompt_variant") == "long_answer"
    assert _KNOWN_SAFE_COMPAT_PAIRS == pass_pairs_from_report(report)
    for model in CN_GALLERY:
        row = report["models"][model]
        assert row["verdict"] in {"PASS", "FAIL", "ENV_BLOCKED"}
        listed = is_known_safe_structured_tools_streaming(model, base_url=APIHUB_CN)
        if row["verdict"] == "PASS":
            assert listed
        else:
            assert not listed


def test_apihub_cn_gallery_not_known_safe_until_pair_table_lists_them():
    """Unlisted gallery pairs stay salvage-safe; listed pairs match the production table."""
    from coworker.providers.openai_provider import _KNOWN_SAFE_COMPAT_PAIRS

    host = "apihub.chem-cloud.cn"
    for model in CN_GALLERY:
        listed = (host, model) in _KNOWN_SAFE_COMPAT_PAIRS
        assert (
            is_known_safe_structured_tools_streaming(model, base_url=APIHUB_CN)
            is listed
        )
        assert (
            is_known_safe_structured_tools_streaming(
                f"apihub-cn:{model}", base_url=APIHUB_CN
            )
            is listed
        )


def test_known_safe_compat_pair_is_exact_host_and_model(monkeypatch):
    """A listed pair is known-safe; sibling model and other hosts are not."""
    from coworker.providers import openai_provider as m

    monkeypatch.setattr(
        m,
        "_KNOWN_SAFE_COMPAT_PAIRS",
        frozenset({("apihub.chem-cloud.cn", "deepseek-v4-flash")}),
    )
    assert m.is_known_safe_structured_tools_streaming(
        "deepseek-v4-flash", base_url=APIHUB_CN
    )
    assert m.is_known_safe_structured_tools_streaming(
        "apihub-cn:deepseek-v4-flash", base_url=APIHUB_CN
    )
    assert not m.is_known_safe_structured_tools_streaming(
        "deepseek-v4-pro", base_url=APIHUB_CN
    )
    assert not m.is_known_safe_structured_tools_streaming(
        "deepseek-v4-flash", base_url="https://custom.example/v1"
    )
    assert not m.is_known_safe_structured_tools_streaming(
        "deepseek-v4-flash", base_url="https://www.tokenfoundryx.com/v1"
    )
    assert not m.is_known_safe_structured_tools_streaming(
        "deepseek-v4-flash", base_url=None
    )


def test_salvage_would_fire_on_textual_tool_call():
    from tests.apihub_cn_stream_probe import ECHO_PROBE_TOOLS, salvage_would_fire

    blob = '{"name": "echo_probe", "arguments": {"token": "chemclaw-d161"}}'
    assert salvage_would_fire(blob, ECHO_PROBE_TOOLS)
    assert not salvage_would_fire("token received", ECHO_PROBE_TOOLS)
    assert not salvage_would_fire(None, ECHO_PROBE_TOOLS)


def test_classify_tool_run_requires_structured_echo_probe():
    from tests.apihub_cn_stream_probe import StreamRunRecord, classify_tool_run

    ok = StreamRunRecord(
        model="glm-5.2",
        phase="tool",
        tool_calls=[{"id": "c1", "name": "echo_probe", "arguments": {"token": "x"}}],
    )
    assert classify_tool_run(ok) == []
    missing = StreamRunRecord(model="glm-5.2", phase="tool", joined_text="hi")
    assert "no_structured_tool" in classify_tool_run(missing)
    leaked = StreamRunRecord(
        model="glm-5.2",
        phase="tool",
        tool_calls=[{"id": "c1", "name": "echo_probe", "arguments": {}}],
        salvage_would_fire=True,
    )
    assert "salvage_would_fire" in classify_tool_run(leaked)
    dropped = StreamRunRecord(
        model="glm-5.2",
        phase="tool",
        transport_error="incomplete chunked read",
        transport_after_progress=True,
        tool_calls=[{"id": "c1", "name": "echo_probe", "arguments": {}}],
    )
    assert "transport_after_progress" in classify_tool_run(dropped)


def test_answer_user_prompt_is_long_form_not_one_short_sentence():
    """D-163: synthesis prompt must request a long briefing; 200ms gate stays."""
    from tests.apihub_cn_stream_probe import (
        ANSWER_USER_PROMPT,
        MIN_ANSWER_DELTA_SPAN_MS,
        PROMPT_VARIANT,
    )

    lowered = ANSWER_USER_PROMPT.lower()
    assert PROMPT_VARIANT == "long_answer"
    assert MIN_ANSWER_DELTA_SPAN_MS == 200.0
    assert "one short" not in lowered
    assert "一句短" not in ANSWER_USER_PROMPT
    assert "400" in ANSWER_USER_PROMPT
    assert "12" in ANSWER_USER_PROMPT
    assert len(ANSWER_USER_PROMPT) >= 200


def test_classify_answer_run_requires_incremental_span():
    from tests.apihub_cn_stream_probe import StreamRunRecord, classify_answer_run

    ok = StreamRunRecord(
        model="kimi-k3",
        phase="answer",
        text_deltas=["确", "认"],
        text_delta_times_ms=[10.0, 250.0],
    )
    assert classify_answer_run(ok) == []
    burst = StreamRunRecord(
        model="kimi-k3",
        phase="answer",
        text_deltas=["确", "认"],
        text_delta_times_ms=[10.0, 20.0],
    )
    assert "answer_burst" in classify_answer_run(burst)
    one = StreamRunRecord(
        model="kimi-k3",
        phase="answer",
        text_deltas=["确认"],
        text_delta_times_ms=[10.0],
    )
    assert "answer_not_incremental" in classify_answer_run(one)
    reasoning = StreamRunRecord(
        model="kimi-k3",
        phase="answer",
        text_deltas=["确", "认"],
        text_delta_times_ms=[10.0, 250.0],
        reasoning="think",
    )
    assert "reasoning_not_streamed" in classify_answer_run(reasoning)


def test_verdict_for_model_pass_fail_blocked():
    from tests.apihub_cn_stream_probe import verdict_for_model

    empty = [[], [], []]
    assert verdict_for_model(tool_reasons=empty, answer_reasons=empty, blocked=[]) == (
        "PASS",
        [],
    )
    verdict, reasons = verdict_for_model(
        tool_reasons=[[], ["no_structured_tool"], []],
        answer_reasons=empty,
        blocked=[],
    )
    assert verdict == "FAIL"
    assert "no_structured_tool" in reasons
    verdict, reasons = verdict_for_model(
        tool_reasons=[[]],
        answer_reasons=[],
        blocked=["429 rate limit"],
        n=3,
    )
    assert verdict == "ENV_BLOCKED"


def test_pass_pairs_from_report_only_pass():
    from tests.apihub_cn_stream_probe import pass_pairs_from_report

    report = {
        "host": "apihub.chem-cloud.cn",
        "models": {
            "deepseek-v4-flash": {"verdict": "FAIL"},
            "glm-5.2": {"verdict": "PASS"},
            "kimi-k3": {"verdict": "ENV_BLOCKED"},
        },
    }
    assert pass_pairs_from_report(report) == frozenset(
        {("apihub.chem-cloud.cn", "glm-5.2")}
    )


def test_merge_fixture_report_overlays_flash_without_dropping_pass_siblings():
    from tests.apihub_cn_stream_probe import (
        CN_GALLERY_MODELS,
        merge_fixture_report,
        pass_pairs_from_report,
        selected_live_models,
    )

    existing = {
        "decision": "D-163",
        "host": "apihub.chem-cloud.cn",
        "prompt_variant": "long_answer",
        "models": {
            "deepseek-v4-flash": {"verdict": "FAIL"},
            "deepseek-v4-pro": {"verdict": "PASS"},
            "glm-5.2": {"verdict": "PASS"},
            "kimi-k3": {"verdict": "FAIL"},
        },
    }
    update = {
        "decision": "D-164",
        "probed_at": "2026-08-18T10:00:00Z",
        "models": {"deepseek-v4-flash": {"verdict": "PASS", "reasons": []}},
    }
    merged = merge_fixture_report(existing, update)
    assert merged["decision"] == "D-164"
    assert merged["models"]["deepseek-v4-flash"]["verdict"] == "PASS"
    assert merged["models"]["deepseek-v4-pro"]["verdict"] == "PASS"
    assert merged["models"]["glm-5.2"]["verdict"] == "PASS"
    assert merged["models"]["kimi-k3"]["verdict"] == "FAIL"
    assert pass_pairs_from_report(merged) == frozenset(
        {
            ("apihub.chem-cloud.cn", "deepseek-v4-flash"),
            ("apihub.chem-cloud.cn", "deepseek-v4-pro"),
            ("apihub.chem-cloud.cn", "glm-5.2"),
        }
    )
    assert selected_live_models("") == CN_GALLERY_MODELS
    assert selected_live_models("deepseek-v4-flash") == ("deepseek-v4-flash",)


def test_product_chemclaw_secrets_path_ignores_isolated_state_dir(tmp_path, monkeypatch):
    from tests.apihub_cn_stream_probe import product_chemclaw_secrets_path

    monkeypatch.setenv("COWORKER_STATE_DIR", str(tmp_path / "coworker-state"))
    path = product_chemclaw_secrets_path()
    assert "coworker-state" not in str(path)
    assert path.name == "secrets.json"
    assert path.parent.name in {"ChemClaw", "chemclaw"}


def test_live_probe_file_skipped_by_default():
    import os

    from tests.test_apihub_cn_structured_stream_live import LIVE_ENABLED

    if os.environ.get("CHEMCLAW_LIVE_APIHUB_CN") == "1":
        return
    assert LIVE_ENABLED is False
