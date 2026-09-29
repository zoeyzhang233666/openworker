"""Execution depth is persistent, budgeted, and independent of permissions."""
import asyncio
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from coworker.config import Config
from coworker.execution_profile import apply_reasoning_mode_settings
from coworker.providers import AssistantTurn, ModelCapabilities
from coworker.server import SessionManager, create_app
from coworker.sessions import SessionRecord
from coworker.task_budget import TaskBudgetStore
from coworker.turn_planner import TurnPlanner
from tests.test_engine import _collect
from tests.test_model_selection import RecordingProvider, drain
from tests.test_runtime_resume import engine, call


async def consume(stream):
    return [event async for event in stream]


def test_session_defaults_legacy_automation_and_empty_choice_restart(tmp_path):
    data = tmp_path / "data"
    mgr = SessionManager(data_dir=data, workspace=tmp_path, provider=RecordingProvider())
    mgr.session_store.save(SessionRecord("legacy", str(tmp_path), "test", "interactive", agent="chat"))
    assert mgr.get_engine("legacy").research_depth == "deep"
    assert mgr.get_engine("__run__scheduled", agent="chat").research_depth == "deep"
    e = mgr.get_engine("new", agent="chat")
    assert e.research_depth == "fast"
    mode, model = e.permissions.mode, e.model
    mgr.set_research_depth("new", "deep")
    restored = SessionManager(data_dir=data, workspace=tmp_path, provider=RecordingProvider())
    assert restored.get_engine("new").research_depth == "deep"
    assert restored.get_engine("other", agent="chat").research_depth == "fast"
    assert e.permissions.mode == mode and e.model == model and e.task_budget is None
    assert next(r for r in mgr.session_store.list() if r.session_id == "new").research_depth == "deep"


@pytest.mark.parametrize("depth", [None, "turbo", {}, [], 1])
def test_invalid_depth_does_not_mutate(tmp_path, depth):
    mgr = SessionManager(data_dir=tmp_path / "data", workspace=tmp_path, provider=RecordingProvider())
    e = mgr.get_engine("s", agent="chat")
    with pytest.raises(ValueError):
        mgr.set_research_depth("s", depth)
    assert e.research_depth == "fast"


def test_ws_choice_send_reconnect_and_running_rejection(tmp_path):
    provider = RecordingProvider()
    mgr = SessionManager(data_dir=tmp_path / "data", workspace=tmp_path, provider=provider)
    client = TestClient(create_app(mgr))
    with client.websocket_connect("/ws/session/s?agent=chat") as ws:
        assert ws.receive_json()["data"]["research_depth"] == "fast"
        ws.send_json({"type": "set_research_depth", "research_depth": "deep"})
        assert ws.receive_json()["type"] == "research_depth_selected"
        assert mgr.session_store.load("s").research_depth == "deep"
        ws.send_json({"type": "user_message", "text": "你好", "research_depth": "fast"})
        assert drain(ws)[-1]["type"] == "turn_done"
        assert mgr.get_engine("s").task_budget.snapshot()["limit"] == 6
    with client.websocket_connect("/ws/session/s?agent=chat") as ws:
        assert ws.receive_json()["data"]["research_depth"] == "fast"
        assert mgr.try_mark_running("s")
        ws.send_json({"type": "set_research_depth", "research_depth": "deep"})
        assert ws.receive_json()["type"] == "research_depth_rejected"
        assert ws.receive_json()["type"] == "input_rejected"
        assert mgr.get_engine("s").research_depth == "fast"


@pytest.mark.parametrize("ignores_tools", [False, True])
def test_fast_six_calls_deliver_answer_or_preserve_unfinished_tools(tmp_path, ignores_tools):
    final = call(5) if ignores_tools else AssistantTurn(text="核心业务、客户与收入结构如下，依据已核验资料。", finish_reason="stop")
    e, writes = engine(tmp_path, [call(i) for i in range(5)] + [final])
    seen = []
    original = e.provider.complete
    def record(**kwargs):
        seen.append(kwargs)
        return original(**kwargs)
    e.provider.complete = record
    e.task_budget = TaskBudgetStore(tmp_path / "budget.db").create("s", research_depth="fast")
    events = _collect(e, "梳理业务")
    assert len(seen) == 6 and seen[-1]["tools"] is None
    assert writes == list(range(5))
    assert events[-1].data["status"] == ("budget_paused" if ignores_tools else "completed")
    assert e.task_budget.snapshot()["used"] == 6
    assert "最终交付轮" in str(seen[-1]["messages"])
    assert "从第一轮就设计快速完成路径" in str(seen[0]["messages"])
    assert "最小完整交付" in str(seen[0]["messages"])
    assert "已进入综合阶段" not in str(seen[1]["messages"])
    assert "已进入综合阶段" in str(seen[2]["messages"])
    if ignores_tools:
        assert any(m.get("tool_call_id") == "id5" for m in e.messages)


def test_early_answer_completes_and_local_engine_also_converges(tmp_path):
    e, _ = engine(tmp_path, [AssistantTurn(text="你好", finish_reason="stop")])
    e.research_depth = "fast"
    assert _collect(e, "你好")[-1].data["status"] == "completed"
    e, writes = engine(tmp_path, [call(i) for i in range(6)])
    e.research_depth = "fast"
    assert _collect(e, "work")[-1].data["status"] == "budget_paused"
    assert writes == list(range(5))


def test_fast_reserve_is_shared_and_explicit_continue_changes_next_segment(tmp_path):
    store = TaskBudgetStore(tmp_path / "budget.db")
    parent = store.create("s", research_depth="fast")
    child = store.bind(parent.group, "s", "child")
    for _ in range(5):
        child.settle(child.acquire(), success=True)
    assert child.acquire() is None
    e, _ = engine(tmp_path, [call(5)])
    e.task_budget = parent
    assert _collect(e, "work")[-1].data["status"] == "budget_paused"
    restored, _ = engine(tmp_path, [AssistantTurn(text="补齐", finish_reason="stop")], messages=deepcopy(e.messages))
    restored.task_budget = store.bind(parent.group, "s", "s", parent=True)
    restored.research_depth = "deep"
    assert asyncio.run(consume(restored.resume()))[-1].data["status"] == "budget_paused"
    assert parent.snapshot()["limit"] == 6
    assert asyncio.run(consume(restored.retry()))[-1].data["status"] == "completed"
    snapshot = parent.snapshot()
    assert (snapshot["used"], snapshot["limit"], snapshot["reserve"], snapshot["research_depth"]) == (7, 306, 15, "deep")
    # Shrinking the next segment must not recompute or erase previous allowance.
    while (token := parent.acquire()) is not None:
        parent.settle(token, success=True)
    assert store.continue_segment(parent, 2, research_depth="fast")
    assert parent.snapshot()["limit"] == 312 and parent.snapshot()["used"] == 306


def test_choice_or_ordinary_message_cannot_renew_paused_budget(tmp_path):
    mgr = SessionManager(data_dir=tmp_path / "data", workspace=tmp_path, provider=RecordingProvider())
    e = mgr.get_engine("s", agent="chat")
    mgr._prepare_task_budget("s", e, None)
    budget = e.task_budget
    for _ in range(6):
        budget.settle(budget.acquire(), success=True)
    e._append_notice("budget_paused", "暂停")
    mgr.set_research_depth("s", "deep")
    mgr._prepare_task_budget("s", e, None)
    assert e.task_budget.group == budget.group and budget.snapshot()["limit"] == 6
    assert e._effective_research_depth() == "fast"


@pytest.mark.parametrize("depth,effort,limit", [("fast", "low", 6), ("deep", "high", 150)])
def test_planner_keeps_tool_surface_and_gates_reasoning(depth, effort, limit):
    planner = TurnPlanner(config=Config(), available_tool_names=lambda: ("web_search", "read_file", "shell"))
    plan = planner.plan("梳理卓创资讯业务", research_depth=depth)
    assert plan.execution_profile.max_iterations == limit
    assert plan.preview().research_depth == depth
    assert plan.capability_plan.selected_tool_names == ("web_search", "read_file", "shell")
    assert plan.execution_profile.allowed_tool_names is None
    assert apply_reasoning_mode_settings({}, effort) == {}
    assert apply_reasoning_mode_settings({}, effort, supports_reasoning_effort=True) == {"reasoning_effort": effort}
    assert apply_reasoning_mode_settings({"reasoning_effort": "medium"}, effort, supports_reasoning_effort=True) == {"reasoning_effort": "medium"}


@pytest.mark.parametrize("supported", [False, True])
def test_actual_provider_reasoning_parameters(tmp_path, supported):
    e, _ = engine(tmp_path, [AssistantTurn(text="done", finish_reason="stop")])
    e.research_depth = "fast"
    e.turn_planner = TurnPlanner(config=Config(), available_tool_names=lambda: ("record",))
    settings = []
    def complete(**kwargs):
        settings.append(kwargs)
        return AssistantTurn(text="done", finish_reason="stop")
    e.provider.complete = complete
    e.provider.capabilities = lambda model: ModelCapabilities(supports_reasoning_effort=supported)
    _collect(e, "你好")
    assert settings[0].get("reasoning_effort") == ("low" if supported else None)


def test_real_old_database_migrates_without_switching_depth(tmp_path):
    from coworker.conversations import ConversationStore
    store = ConversationStore(tmp_path / "old")
    store.save(SessionRecord("legacy", "", "test", "interactive", agent="chat"))
    store._conn.execute("ALTER TABLE sessions DROP COLUMN research_depth")
    store._conn.commit()
    store._conn.close()
    restored = ConversationStore(tmp_path / "old")
    assert restored.load("legacy").research_depth == "deep"


@pytest.mark.parametrize("finish,text,status", [("length", "半句", "truncated"), ("stop", "", "budget_paused"), ("error", "失败", "blocked")])
def test_final_round_never_marks_empty_or_truncated_response_complete(tmp_path, finish, text, status):
    e, _ = engine(tmp_path, [AssistantTurn(text=text, finish_reason=finish)])
    budget = TaskBudgetStore(tmp_path / "budget.db").create("s", research_depth="fast")
    for _ in range(5):
        budget.settle(budget.acquire(), success=True)
    e.task_budget = budget
    assert _collect(e, "work")[-1].data["status"] == status
    assert e.provider.calls == 1


def test_background_new_session_preserves_deep_default(tmp_path):
    mgr = SessionManager(data_dir=tmp_path / "data", workspace=tmp_path, provider=RecordingProvider())
    e = asyncio.run(mgr._prepare_engine_for_turn("channel", agent="chat"))
    assert e.research_depth == "deep"
    mgr._prepare_task_budget("channel", e, None)
    assert (e.task_budget.snapshot()["limit"], e.task_budget.snapshot()["reserve"]) == (300, 15)


def test_switch_to_fast_does_not_inherit_unused_deep_summary_allowance(tmp_path):
    store = TaskBudgetStore(tmp_path / "budget.db")
    parent = store.create("s", research_depth="deep")
    for _ in range(285):
        parent.settle(parent.acquire(), success=True)
    assert store.continue_segment(parent, 1, research_depth="fast")
    assert parent.snapshot()["used"] == 285
    assert parent.snapshot()["remaining"] == 6


def test_legacy_managed_task_adopts_choice_only_on_explicit_continue(tmp_path):
    mgr = SessionManager(data_dir=tmp_path / "data", workspace=tmp_path, provider=RecordingProvider())
    e = mgr.get_engine("s", agent="chat")
    e.task_budget = mgr.task_budgets.create("s", size=2, reserve=1)
    for _ in range(2):
        e.task_budget.settle(e.task_budget.acquire(), success=True)
    asyncio.run(e._pause("budget_paused", "暂停"))
    assert e._effective_research_depth() == "deep"
    mgr.set_research_depth("s", "fast")
    assert asyncio.run(consume(e.retry()))[-1].data["status"] == "completed"
    assert e.task_budget.snapshot()["research_depth"] == "fast"
    assert e.task_budget.snapshot()["limit"] == 8
