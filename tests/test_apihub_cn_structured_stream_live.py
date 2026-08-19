"""Opt-in live D-161 probe against ApiHub CN. Default CI skips (no network)."""

from __future__ import annotations

import os

import pytest

from tests.apihub_cn_stream_probe import (
    CN_GALLERY_MODELS,
    LIVE_ENV,
    load_fixture,
    merge_fixture_report,
    run_gallery_probe,
    selected_live_models,
    write_fixture,
)

LIVE_ENABLED = os.environ.get(LIVE_ENV) == "1"


@pytest.mark.skipif(
    not LIVE_ENABLED,
    reason=f"opt-in: real ApiHub CN stream probe (set {LIVE_ENV}=1)",
)
def test_live_apihub_cn_gallery_structured_stream():
    selected = selected_live_models()
    report = run_gallery_probe(models=selected)
    if selected != CN_GALLERY_MODELS:
        report = merge_fixture_report(load_fixture(), report)
    write_fixture(report)
    assert report["prompt_variant"] == "long_answer"
    assert report["min_answer_delta_span_ms"] == 200.0
    assert set(report["models"]) == set(CN_GALLERY_MODELS)
    allowed = {"PASS", "FAIL", "ENV_BLOCKED"}
    for name, row in report["models"].items():
        assert row["verdict"] in allowed, name
