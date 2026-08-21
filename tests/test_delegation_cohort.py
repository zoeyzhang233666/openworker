"""Tests for DelegationCohortTracker (D-175)."""

from __future__ import annotations

from coworker.subagents.cohort import (
    DelegationCohortTracker,
    format_cohort_synthesis_message,
)


def test_cohort_fires_once_when_all_terminal(tmp_path):
    tracker = DelegationCohortTracker(tmp_path / "cohorts.json")
    tracker.register("s1", "a1", parent_trace_id="t1", profile_id="research")
    tracker.register("s1", "a2", parent_trace_id="t1", profile_id="research")
    assert tracker.on_terminal("a1", status="completed") is None
    ready = tracker.on_terminal("a2", status="failed", error="boom")
    assert ready is not None
    assert ready.owner_session_id == "s1"
    assert [m.task_id for m in ready.members] == ["a1", "a2"]
    assert ready.members[1].status == "failed"
    assert tracker.on_terminal("a2", status="failed") is None


def test_failed_and_cancelled_count_as_terminal(tmp_path):
    tracker = DelegationCohortTracker(tmp_path / "cohorts.json")
    tracker.register("s1", "a1", parent_trace_id="t1")
    tracker.register("s1", "a2", parent_trace_id="t1")
    tracker.on_terminal("a1", status="cancelled")
    ready = tracker.on_terminal("a2", status="interrupted")
    assert ready is not None
    msg = format_cohort_synthesis_message(ready)
    assert "子智能体汇合通知" in msg
    assert "`a1`" in msg and "cancelled" in msg


def test_new_batch_after_synthesis(tmp_path):
    tracker = DelegationCohortTracker(tmp_path / "cohorts.json")
    tracker.register("s1", "a1", parent_trace_id="t1")
    assert tracker.on_terminal("a1", status="completed") is not None
    tracker.register("s1", "a3", parent_trace_id="t1")
    assert tracker.on_terminal("a3", status="completed") is not None


def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "cohorts.json"
    tracker = DelegationCohortTracker(path)
    tracker.register("s1", "a1", parent_trace_id="t9", description="upstream")
    tracker.register("s1", "a2", parent_trace_id="t9")
    tracker.on_terminal("a1", status="completed")
    reloaded = DelegationCohortTracker(path)
    ready = reloaded.on_terminal("a2", status="completed")
    assert ready is not None
    assert ready.parent_trace_id == "t9"
