import asyncio
import pytest

from coworker.automation import TaskRun, TaskStore, Scheduler
from coworker.providers import AssistantTurn, ToolCall
from coworker.server.manager import SessionManager
from tests.test_automation import _task
from tests.test_subagent_readonly import Provider


async def consume(stream):
    return [event async for event in stream]


@pytest.mark.asyncio
async def test_scheduled_pause_uses_shared_budget_and_notification_is_deduplicated(tmp_path):
    (tmp_path / "data.txt").write_text("1\n2\n3\n", encoding="utf-8")
    provider = Provider([AssistantTurn(tool_calls=[ToolCall(str(i), "read_file",
        {"path": "data.txt", "start_line": i, "max_lines": 1})], finish_reason="tool_calls") for i in range(1, 4)])
    manager = SessionManager(data_dir=tmp_path / "state", provider=provider)
    original_create = manager.task_budgets.create
    manager.task_budgets.create = lambda owner: original_create(owner, size=3, reserve=1)
    task = _task(workspace=str(tmp_path), agent="cowork", notify_on_completion=True)
    manager.task_store.save(task)
    sent = []
    async def broadcast(sid, event):
        sent.append(event)
    manager.broadcast_session = broadcast
    try:
        run = await manager._run_scheduled_task(task, "schedule")
        engine = manager._engines[run.session_id]
        assert run.status == run.execution_status == "budget_paused" and run.resumable
        assert engine.task_budget.snapshot()["used"] == 3
        assert "start_subagent" in engine.registry.names()
        assert manager.session_store.load(run.session_id).messages[-1]["kind"] == "budget_paused"
        await manager._notify_task_done(task, run)
        assert sum(e["type"] == "task_done" for e in sent) == 1
        assert next(e for e in sent if e["type"] == "task_done")["data"]["status"] == "budget_paused"
        assert manager.task_store.find_run(run.run_id).notified_states == ["budget_paused"]
        assert not manager.is_running(run.session_id)
    finally:
        manager.background_tasks.close()


@pytest.mark.asyncio
async def test_manual_empty_and_paused_runs_are_not_completed_and_resume_updates_same_run(tmp_path):
    manager = SessionManager(data_dir=tmp_path / "state", provider=Provider([AssistantTurn(text="done", finish_reason="stop")]))
    task = _task(workspace=str(tmp_path), agent="cowork")
    manager.task_store.save(task)
    prepared = manager.prepare_manual_run(task.id)
    run_id, sid = prepared["run_id"], prepared["session_id"]
    try:
        assert manager.finalize_manual_run(task.id, run_id)["run"]["execution_status"] == "queued"
        engine = manager.get_engine(sid, workspace=str(tmp_path), agent="cowork")
        manager._prepare_task_budget(sid, engine, None)
        engine.messages.append({"role": "user", "content": "work"})
        await engine._pause("budget_paused", "需要继续")
        paused = manager.finalize_manual_run(task.id, run_id)["run"]
        assert paused["execution_status"] == "budget_paused" and paused["resumable"]
        await consume(engine.retry())
        for _ in range(2):
            result = manager.finalize_manual_run(task.id, run_id)
            assert result["run"]["execution_status"] == "completed"
        assert manager.task_store.get(task.id).run_count == 1
    finally:
        manager.background_tasks.close()


@pytest.mark.asyncio
async def test_restart_reconciles_run_and_scheduler_does_not_replay_it(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    task = store.save(_task(workspace=str(tmp_path)))
    run = store.add_run(TaskRun(task_id=task.id))
    store.reconcile_running()
    calls = []
    async def runner(*args):
        calls.append(args)
    scheduler = Scheduler(store, runner)
    try:
        recovered = store.find_run(run.run_id)
        assert recovered.execution_status == "blocked" and recovered.resumable
        assert await scheduler.run_task(task, trigger="catchup") is None
        assert not calls
        # Old successful rows remain compatible.
        assert TaskRun.from_dict({"task_id": task.id, "status": "ok"}).execution_status == "completed"
    finally:
        store.close()


@pytest.mark.asyncio
async def test_headless_approval_remains_pending_until_user_decides(tmp_path):
    provider = Provider([AssistantTurn(tool_calls=[ToolCall("shell", "run_shell", {"command": "python -c 'print(1)'"})], finish_reason="tool_calls"),
                         AssistantTurn(text="已遵从拒绝，未执行命令", finish_reason="stop")])
    manager = SessionManager(data_dir=tmp_path / "state", provider=provider)
    task = _task(workspace=str(tmp_path), agent="code", notify_on_completion=False)
    manager.task_store.save(task)
    pending = asyncio.create_task(manager._run_scheduled_task(task, "schedule"))
    try:
        for _ in range(100):
            await asyncio.sleep(.02)
            runs = manager.task_store.runs(task.id)
            if runs and manager.inbox.pending(runs[0].session_id):
                break
        run = runs[0]
        items = manager.inbox.pending(run.session_id)
        assert items and not pending.done()
        assert manager.task_store.find_run(run.run_id).execution_status == "waiting_user"
        assert manager.is_running(run.session_id)
        await manager.resolve_inbox(items[0].id, "deny")
        finished = await asyncio.wait_for(pending, timeout=5)
        assert finished.execution_status == "completed"
    finally:
        if not pending.done():
            pending.cancel()
            try:
                await pending
            except asyncio.CancelledError:
                pass
        manager.background_tasks.close()
