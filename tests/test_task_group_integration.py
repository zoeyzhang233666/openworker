"""Main/child integration uses only local files and scripted model responses."""
import asyncio

from coworker.providers import AssistantTurn, ToolCall
from coworker.server.manager import SessionManager
from tests.test_subagent_readonly import Provider, child_pair


async def consume(stream):
    return [e async for e in stream]


def test_main_and_child_share_real_model_turns_beyond_old_limit(tmp_path):
    (tmp_path / "source.txt").write_text("\n".join(str(i) for i in range(80)), encoding="utf-8")
    class ResearchProvider(Provider):
        counts = {"parent": 0, "child": 0}
        def complete(self, **kwargs):
            child = any(m.get("role") == "user" and "child work" in str(m.get("content"))
                        for m in kwargs["messages"])
            actor = "child" if child else "parent"
            self.counts[actor] += 1
            n = self.counts[actor]
            if child and n <= 34:
                return AssistantTurn(tool_calls=[ToolCall(str(n), "read_file",
                    {"path": "source.txt", "start_line": n, "max_lines": 1})], finish_reason="tool_calls")
            if not child and n == 1:
                return AssistantTurn(tool_calls=[ToolCall("explore", "explore", {"task": "child work"})], finish_reason="tool_calls")
            return AssistantTurn(text="研究结论：source.txt:1-34", finish_reason="stop")
    provider = ResearchProvider()
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "state", provider=provider)
    parent = manager.get_engine("parent", agent="code", workspace=str(tmp_path))
    manager.set_research_depth("parent", "deep")
    try:
        events = asyncio.run(consume(parent.run("parent work")))
        assert events[-1].data["status"] == "completed"
        assert provider.counts == {"parent": 2, "child": 35}
        assert parent.task_budget.snapshot()["used"] == 37
        tasks = manager.background_tasks.list(owner_session_id="parent")
        assert len(tasks) == 1 and tasks[0].status == "completed"
        child = manager._engines[tasks[0].child_session_id]
        assert child.task_budget.group == parent.task_budget.group
        assert all('"error"' not in m.get("content", "") for m in child.messages if m.get("role") == "tool")
    finally:
        manager.background_tasks.close()


def test_restart_waits_for_explicit_continue_and_does_not_repeat_unknown_write(tmp_path):
    provider = Provider([AssistantTurn(text="核对后再继续", finish_reason="stop")])
    manager, parent, _ = child_pair(tmp_path, provider)
    manager._prepare_task_budget("parent", parent, None)
    parent.messages.extend([
        {"role": "user", "content": "write"},
        {"role": "assistant", "tool_calls": [{"id": "w", "type": "function",
         "function": {"name": "write_file", "arguments": '{"path":"duplicate.txt","content":"x"}'}}]},
    ])
    parent._runtime["inflight"] = ["w"]
    asyncio.run(parent._checkpoint("tool_started"))
    manager._engines.pop("parent")
    restored = manager.get_engine("parent")
    try:
        assert restored.messages[-1]["kind"] == "blocked"
        assert restored.task_budget.snapshot()["used"] == 0
        events = asyncio.run(consume(restored.retry()))
        assert any(e.data.get("reason") == "execution_state_unknown" for e in events)
        assert not (tmp_path / "duplicate.txt").exists()
        assert restored.task_budget.snapshot()["used"] == 1
        assert restored.task_budget.snapshot()["segment"] == 1
    finally:
        manager.background_tasks.close()


def test_ordinary_message_cannot_extend_paused_budget(tmp_path):
    manager, parent, _ = child_pair(tmp_path)
    manager._prepare_task_budget("parent", parent, None)
    group = parent.task_budget.group
    parent._append_notice("budget_paused")
    manager._prepare_task_budget("parent", parent, None)
    try:
        assert parent.task_budget.group == group
        assert parent.task_budget.snapshot()["segment"] == 1
    finally:
        manager.background_tasks.close()


def test_stop_is_scoped_to_own_task_and_suppresses_late_wake(tmp_path, monkeypatch):
    manager, parent, record = child_pair(tmp_path)
    manager._prepare_task_budget("parent", parent, None)
    group = parent.task_budget.group
    other = manager.get_engine("other", workspace=str(tmp_path))
    manager._prepare_task_budget("other", other, None)
    calls = []
    monkeypatch.setattr(manager.background_tasks, "stop", lambda task_id, **kwargs: calls.append(task_id))
    manager.background_tasks.store.put(record.model_copy(update={"metadata": {"task_group": group}}))
    manager.background_tasks.store.put(record.model_copy(update={"id": "old", "metadata": {"task_group": "old"}}))
    try:
        parent.request_interrupt()
        assert calls == ["child"]
        assert parent.task_budget.snapshot()["stopped"]
        assert not other.task_budget.snapshot()["stopped"]
        # A queued notification that arrives after a stop may not run the model.
        import pytest
        with pytest.raises(ValueError, match="停止"):
            manager._prepare_task_budget("parent", parent, {"kind": "subagent_cohort_complete", "task_group": group})
    finally:
        manager.background_tasks.close()


def test_child_restores_model_roots_policy_and_refreshes_reviewed_mcp(tmp_path):
    from coworker.tool_policy import TurnToolPolicy
    from coworker.risk import RiskClass
    import aisuite as ai
    manager, parent, record = child_pair(tmp_path)
    parent.model = "test:parent-model"
    parent.model_settings = {"max_tokens": 4567, "reasoning_effort": "low"}
    parent.turn_tool_policy = TurnToolPolicy(no_external_network=True)
    record = record.model_copy(update={"metadata": manager._child_task_context("parent")})
    profile = manager.subagent_runtime.profiles.require("research")
    try:
        child = manager._build_subagent_engine(record, profile)
        assert child.model == "test:parent-model"
        assert child.model_settings["max_tokens"] == 4567
        assert child.model_settings["reasoning_effort"] == "low"
        assert child._current_tool_policy().no_external_network
        assert {r.path for r in child.permissions.roots} == {r.path for r in parent.permissions.roots}
        assert all(not r.writable for r in child.permissions.roots)
        def mcp__rare__read():
            return "data"
        parent.permissions.risk_overrides = lambda n: RiskClass.READ if n == "mcp__rare__read" else None
        child = manager._build_subagent_engine(record, profile)
        parent.registry.register(mcp__rare__read, metadata=ai.ToolMetadata(category="mcp"))
        child.refresh_tool_registry()
        assert "mcp__rare__read" in child.registry.names()
        parent.registry.retain(set(parent.registry.names()) - {"mcp__rare__read"})
        child.refresh_tool_registry()
        assert "mcp__rare__read" not in child.registry.names()
        manager._engines.pop("parent")
        child = manager._build_subagent_engine(record, profile)
        assert child.model == "test:parent-model" and child._current_tool_policy().no_external_network
    finally:
        manager.background_tasks.close()
