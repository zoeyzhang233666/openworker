import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest

from coworker.task_budget import TaskBudgetStore
from coworker.providers import AssistantTurn
from tests.test_runtime_resume import engine, call


def test_five_concurrent_actors_cannot_overspend_and_parent_has_reserve(tmp_path):
    store = TaskBudgetStore(tmp_path / "budget.db")
    parent = store.create("owner")
    children = [store.bind(parent.group, "owner", f"child{i}") for i in range(5)]
    def run(child):
        count = 0
        while (token := child.acquire()) is not None:
            child.settle(token, success=True)
            count += 1
        return count
    with ThreadPoolExecutor(5) as pool:
        assert sum(pool.map(run, children)) == 285
    assert parent.snapshot()["remaining"] == 15
    assert run(parent) == 15
    assert parent.snapshot()["used"] == 300
    assert parent.acquire() is None
    assert store.continue_segment(parent, 1)
    assert not store.continue_segment(parent, 1)
    assert parent.snapshot()["used"] == 300 and parent.snapshot()["remaining"] == 300
    with pytest.raises(ValueError):
        store.continue_segment(children[0], 2)
    with pytest.raises(ValueError):
        store.bind(parent.group, "other", "spy")


def test_restart_preserves_usage_and_uncertain_request(tmp_path):
    path = tmp_path / "budget.db"
    store = TaskBudgetStore(path)
    parent = store.create("owner")
    token = parent.acquire()
    parent.settle(token, success=True, usage={"input": 10, "output": 5})
    parent.acquire()
    reloaded = TaskBudgetStore(path).bind(parent.group, "owner", "owner", parent=True)
    assert reloaded.snapshot()["used"] == 1
    assert reloaded.snapshot()["uncertain"] == 1
    assert reloaded.snapshot()["usage"] == {"input": 10, "output": 5}


def test_engine_ignores_old_individual_cap_and_retries_without_renewing(tmp_path):
    store = TaskBudgetStore(tmp_path / "budget.db")
    root = store.create("owner", size=8, reserve=2)
    child = store.bind(root.group, "owner", "child")
    e, writes = engine(tmp_path, [call(i) for i in range(8)], limit=2)
    # This fixture's record tool is intentionally outside summary tools.
    e.task_budget = child
    async def run():
        return [event async for event in e.run("work")]
    assert asyncio.run(run())[-1].data["status"] == "budget_paused"
    assert len(writes) >= 5
    assert root.snapshot()["used"] == 6
    async def retry():
        return [event async for event in e.retry(renew_budget=False)]
    assert asyncio.run(retry())[-1].data["status"] == "budget_paused"
    assert root.snapshot()["segment"] == 1


def test_failed_request_releases_lease(tmp_path):
    store = TaskBudgetStore(tmp_path / "budget.db")
    root = store.create("owner")
    e, _ = engine(tmp_path, [])
    e.task_budget = root
    asyncio.run(_consume(e.run("work")))
    assert root.snapshot()["reserved"] == root.snapshot()["used"] == 0
    assert root.snapshot()["model_calls"] == 1


async def _consume(stream):
    return [event async for event in stream]


def test_actual_engine_reaches_300_then_explicit_continue_survives_reload(tmp_path):
    from copy import deepcopy
    from coworker.providers import ToolCall
    from tests.test_engine import ScriptedProvider
    store = TaskBudgetStore(tmp_path / "budget.db")
    root = store.create("owner")
    turns = [AssistantTurn(tool_calls=[ToolCall(id=str(i), name="read_file", arguments={"value": i})],
                           finish_reason="tool_calls") for i in range(300)]
    e, _ = engine(tmp_path, turns)
    reads = []
    def read_file(value: int):
        reads.append(value)
        return value
    e.registry.register(read_file)
    e.task_budget = root
    events = asyncio.run(_consume(e.run("long")))
    assert events[-1].data["status"] == "budget_paused"
    assert reads == list(range(300))
    restored, _ = engine(tmp_path, [AssistantTurn(text="done", finish_reason="stop")], messages=deepcopy(e.messages))
    restored.task_budget = TaskBudgetStore(tmp_path / "budget.db").bind(root.group, "owner", "owner", parent=True)
    assert asyncio.run(_consume(restored.resume()))[-1].data["status"] == "budget_paused"
    assert restored.task_budget.snapshot()["segment"] == 1
    assert asyncio.run(_consume(restored.retry()))[-1].data["status"] == "completed"
    assert restored.task_budget.snapshot()["used"] == 301
    assert restored.task_budget.snapshot()["segment"] == 2
