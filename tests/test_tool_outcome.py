from __future__ import annotations

from coworker.tools.outcome import normalize_tool_outcome


def test_tool_outcome_classifies_legacy_payloads_without_losing_raw_data() -> None:
    success = normalize_tool_outcome({"value": 42, "source_refs": ["s1"]})
    unavailable = normalize_tool_outcome({"error_code": "NO_DATA", "message": "empty"})
    partial = normalize_tool_outcome({"status": "partial", "items": [1]})
    failed = normalize_tool_outcome({"error": "boom", "error_type": "RuntimeError"})
    denied = normalize_tool_outcome(None, denied=True, denial_message="blocked")

    assert success.status == "success" and success.data["value"] == 42
    assert unavailable.status == "unavailable"
    assert partial.status == "partial"
    assert failed.status == "failed"
    assert denied.status == "denied"
