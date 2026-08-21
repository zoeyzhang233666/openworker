from __future__ import annotations

from coworker.background_tasks import BackgroundTaskManager, BackgroundTaskStore
from coworker.events import Event, EventType
from coworker.subagents import SubagentRuntime, builtin_subagent_profiles
from coworker.subagents.tools import subagent_tools
from coworker.tools import ToolRegistry
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient


class FakeEngine:
    def __init__(self):
        self.inputs = []
        self.steering = []
        self.interrupted = False

    async def run(self, value, **_kwargs):
        self.inputs.append(value)
        yield Event(EventType.ASSISTANT_MESSAGE, {"text": f"report:{value}"})
        yield Event(EventType.TURN_END, {"status": "completed"})

    def queue_steering(self, value):
        self.steering.append(value)

    def request_interrupt(self):
        self.interrupted = True


def _runtime(tmp_path):
    manager = BackgroundTaskManager(BackgroundTaskStore(tmp_path / "coworker.db"))
    engines = []
    saved = []

    def build(_record, _profile):
        engine = FakeEngine()
        engines.append(engine)
        return engine

    runtime = SubagentRuntime(
        manager,
        engine_factory=build,
        engine_saver=lambda record, engine: saved.append((record.id, engine)),
    )
    manager.agent_adapter_factory = runtime.adapter_for_record
    return runtime, engines, saved


def test_builtin_profiles_are_declarative_and_readonly_profiles_are_narrow():
    registry = builtin_subagent_profiles()
    assert [p.id for p in registry.list()] == ["explore", "research", "worker"]
    explore = registry.require("explore")
    assert explore.mode == "plan" and explore.isolation == "read_only"
    assert "grep" in explore.tool_allowlist and "run_shell" not in explore.tool_allowlist
    research = registry.require("research")
    assert research.mode == "interactive" and research.isolation == "shared_workspace"
    assert {
        "grep",
        "read_file",
        "list_files",
        "write_file",
        "lookup_cn_futures_ohlc",
        "web_search",
    } <= set(research.tool_allowlist)
    assert "start_subagent" in research.disallowed_tools
    worker = registry.require("worker")
    assert worker.mode == "interactive" and worker.allow_nested is False


def test_runtime_foreground_and_followup_reuse_one_engine(tmp_path):
    runtime, engines, saved = _runtime(tmp_path)
    result = runtime.run_foreground(
        task="first",
        profile_id="explore",
        owner_session_id="s1",
        workspace=str(tmp_path),
    )
    assert result.status == "completed" and result.report == "report:first"
    task = runtime.task_manager.get(result.task_id, owner_session_id="s1")
    assert task is not None and task.child_session_id.startswith("__subagent__")

    runtime.task_manager.send_message(result.task_id, "second", owner_session_id="s1")
    done = runtime.task_manager.wait(result.task_id, timeout=3)
    assert done.run_count == 2
    assert len(engines) == 1 and engines[0].inputs == ["first", "second"]
    assert len(saved) == 2
    runtime.task_manager.close()


def test_subagent_tools_are_owner_scoped_and_gather_reports(tmp_path):
    runtime, _engines, _saved = _runtime(tmp_path)
    reg = ToolRegistry()
    reg.register_all(
        subagent_tools(runtime, owner_session_id="s1", workspace=str(tmp_path))
    )
    started = reg.execute(
        "start_subagent",
        {"task": "one", "profile": "explore", "background": True},
    )
    task_id = started["id"]
    gathered = reg.execute(
        "background_task_gather",
        {"task_ids": [task_id], "timeout_seconds": 3},
    )
    assert gathered["tasks"][0]["report"] == "report:one"

    defaulted = reg.execute(
        "start_subagent",
        {"task": "default-profile", "background": True},
    )
    assert defaulted["profile_id"] == "research"
    runtime.task_manager.wait(defaulted["id"], timeout=3)

    other = ToolRegistry()
    other.register_all(
        subagent_tools(runtime, owner_session_id="s2", workspace=str(tmp_path))
    )
    assert "unknown task" in other.execute(
        "background_task_status", {"task_id": task_id}
    )["error"]
    runtime.task_manager.close()


def test_subagent_tool_links_task_to_parent_trace(tmp_path):
    runtime, _engines, _saved = _runtime(tmp_path)
    reg = ToolRegistry()
    reg.register_all(
        subagent_tools(
            runtime,
            owner_session_id="s1",
            workspace=str(tmp_path),
            parent_trace_id=lambda: "trace-parent",
        )
    )
    started = reg.execute(
        "start_subagent",
        {"task": "linked", "profile": "explore", "background": True},
    )
    assert started["parent_trace_id"] == "trace-parent"
    runtime.task_manager.wait(started["id"], timeout=3)
    runtime.task_manager.close()


class ScriptedProvider(ProviderClient):
    def __init__(self, texts):
        self.texts = list(texts)

    def complete(self, **_kwargs):
        return AssistantTurn(text=self.texts.pop(0), finish_reason="stop")

    def capabilities(self, _model):
        return ModelCapabilities()


def test_session_manager_builds_narrow_child_and_persists_followup(tmp_path):
    from coworker.background_tasks.models import BackgroundTaskRecord
    from coworker.permissions import Mode
    from coworker.server.manager import SessionManager

    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "state",
        provider=ScriptedProvider(["first report", "second report"]),
    )
    now = 1.0
    record = BackgroundTaskRecord(
        id="agent-test",
        kind="agent",
        status="queued",
        owner_session_id="parent",
        description="test",
        workspace=str(tmp_path),
        profile_id="explore",
        child_session_id="__subagent__test",
        created_at=now,
        updated_at=now,
    )
    profile = manager.subagent_runtime.profiles.require("explore")
    child = manager._build_subagent_engine(record, profile)
    assert child.permissions.mode is Mode.PLAN
    assert set(child.registry.names()) == set(profile.tool_allowlist)
    assert "explore" not in child.registry.names() and "run_shell" not in child.registry.names()

    manager.get_engine("parent", workspace=str(tmp_path), agent="code")
    result = manager.subagent_runtime.run_foreground(
        task="inspect",
        profile_id="explore",
        owner_session_id="parent",
        workspace=str(tmp_path),
    )
    assert result.report == "first report"
    manager.background_tasks.send_message(
        result.task_id, "continue", owner_session_id="parent"
    )
    done = manager.background_tasks.wait(result.task_id, timeout=5)
    assert done.run_count == 2 and done.status == "completed"
    output = manager.background_tasks.read_output(result.task_id)
    assert "second report" in "".join(c.text for c in output.chunks)
    task = manager.background_tasks.get(result.task_id)
    persisted = manager.session_store.load(task.child_session_id)
    assert persisted is not None
    assert [m["content"] for m in persisted.messages if m["role"] == "user"] == [
        "inspect",
        "continue",
    ]
    manager.background_tasks.close()


def test_worker_profile_keeps_permission_engine_as_final_authority(tmp_path):
    from coworker.background_tasks.models import BackgroundTaskRecord
    from coworker.server.manager import SessionManager

    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "state",
        provider=ScriptedProvider([]),
    )
    record = BackgroundTaskRecord(
        id="agent-worker",
        kind="agent",
        status="queued",
        owner_session_id="parent",
        description="worker",
        workspace=str(tmp_path),
        profile_id="worker",
        child_session_id="__subagent__worker",
        created_at=1.0,
        updated_at=1.0,
    )
    worker = manager._build_subagent_engine(
        record, manager.subagent_runtime.profiles.require("worker")
    )
    write = worker.registry.get("write_file")
    assert write is not None
    decision = worker.permissions.evaluate(
        "write_file", {"path": "a.txt", "content": "x"}, write.metadata
    )
    assert decision.allowed is False and decision.needs_user is True
    assert "start_subagent" not in worker.registry.names()
    manager.background_tasks.close()


def test_research_profile_inherits_only_declared_live_mcp_servers(tmp_path):
    import aisuite as ai

    from coworker.background_tasks.models import BackgroundTaskRecord
    from coworker.server.manager import SessionManager

    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "state",
        provider=ScriptedProvider([]),
    )
    parent = manager.get_engine("parent", workspace=str(tmp_path), agent="code")

    def mcp__chem_data_hub__price():
        return {"ok": True}

    def mcp__other_server__secret():
        return {"ok": True}

    parent.registry.register(
        mcp__chem_data_hub__price,
        metadata=ai.ToolMetadata(
            category="mcp", risk_level="low", capabilities=["chem-data-hub"]
        ),
    )
    parent.registry.register(
        mcp__other_server__secret,
        metadata=ai.ToolMetadata(
            category="mcp", risk_level="low", capabilities=["other-server"]
        ),
    )
    record = BackgroundTaskRecord(
        id="agent-research",
        kind="agent",
        status="queued",
        owner_session_id="parent",
        description="research",
        workspace=str(tmp_path),
        profile_id="research",
        child_session_id="__subagent__research",
        created_at=1.0,
        updated_at=1.0,
    )
    child = manager._build_subagent_engine(
        record, manager.subagent_runtime.profiles.require("research")
    )
    assert "mcp__chem_data_hub__price" in child.registry.names()
    assert "mcp__other_server__secret" not in child.registry.names()
    assert "lookup_cn_futures_ohlc" in child.registry.names()
    assert "write_file" in child.registry.names()
    assert "start_subagent" not in child.registry.names()
    manager.background_tasks.close()


def test_research_child_inherits_parent_permission_mode(tmp_path):
    from coworker.background_tasks.models import BackgroundTaskRecord
    from coworker.permissions import Mode
    from coworker.server.manager import SessionManager

    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "state",
        provider=ScriptedProvider([]),
    )
    parent = manager.get_engine("parent", workspace=str(tmp_path), agent="cowork")
    parent.permissions.mode = Mode.AUTO
    record = BackgroundTaskRecord(
        id="agent-research-mode",
        kind="agent",
        status="queued",
        owner_session_id="parent",
        description="research",
        workspace=str(tmp_path),
        profile_id="research",
        child_session_id="__subagent__research_mode",
        created_at=1.0,
        updated_at=1.0,
    )
    child = manager._build_subagent_engine(
        record, manager.subagent_runtime.profiles.require("research")
    )
    assert child.permissions.mode is Mode.AUTO
    write = child.registry.get("write_file")
    assert write is not None
    decision = child.permissions.evaluate(
        "write_file", {"path": "report.md", "content": "ok"}, write.metadata
    )
    assert decision.allowed is True and decision.needs_user is False

    parent.permissions.mode = Mode.INTERACTIVE
    child_ask = manager._build_subagent_engine(
        record.model_copy(update={"child_session_id": "__subagent__research_mode2"}),
        manager.subagent_runtime.profiles.require("research"),
    )
    ask = child_ask.permissions.evaluate(
        "write_file",
        {"path": "report.md", "content": "ok"},
        child_ask.registry.get("write_file").metadata,
    )
    assert ask.allowed is False and ask.needs_user is True
    manager.background_tasks.close()


def test_research_child_inherits_parent_dual_market_scope(tmp_path):
    """D-179: parent CN_SPOT_FUTURES must govern child tool guard."""
    import aisuite as ai

    from coworker.background_tasks.models import BackgroundTaskRecord
    from coworker.market_intent import (
        resolve_market_tools,
        snapshot_market_selection_metadata,
    )
    from coworker.server.manager import SessionManager
    from coworker.tools.registry import ToolDescriptor

    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "state",
        provider=ScriptedProvider([]),
    )
    parent = manager.get_engine("parent", workspace=str(tmp_path), agent="cowork")

    def mcp__chem_data_hub__get_price_trend(product: str = "甲醇"):
        return {"ok": True, "product": product}

    parent.registry.register(
        mcp__chem_data_hub__get_price_trend,
        metadata=ai.ToolMetadata(
            category="mcp", risk_level="low", capabilities=["chem-data-hub"]
        ),
    )
    descriptors = [ToolDescriptor(name) for name in parent.registry.names()]
    descriptors.append(
        ToolDescriptor(
            "mcp__chem_data_hub__get_price_trend", "mcp", ("chem-data-hub",)
        )
    )
    dual = resolve_market_tools(
        "研究甲醇期货产业链上下游套利怎么做", descriptors
    )
    meta = snapshot_market_selection_metadata(dual)
    record = BackgroundTaskRecord(
        id="agent-research-market",
        kind="agent",
        status="queued",
        owner_session_id="parent",
        description="research upstream costs",
        workspace=str(tmp_path),
        profile_id="research",
        child_session_id="__subagent__research_market",
        created_at=1.0,
        updated_at=1.0,
        metadata=meta,
    )
    child = manager._build_subagent_engine(
        record, manager.subagent_runtime.profiles.require("research")
    )
    assert child._inherited_market_selection is not None
    assert (
        child._inherited_market_selection.intent.kind.value == "cn_spot_futures"
    )
    # Short child task alone would clarify; inheritance must unlock dual tools.
    child._activate_plan("研究上游成本与期现关系")
    spot = "mcp__chem_data_hub__get_price_trend"
    futures = "lookup_cn_futures_ohlc"
    assert child._market_tool_guard(spot) == (True, "market scope matched")
    assert child._market_tool_guard(futures) == (True, "market scope matched")
    manager.background_tasks.close()


def test_agent_task_followup_rehydrates_child_session_after_manager_restart(tmp_path):
    from coworker.server.manager import SessionManager

    data_dir = tmp_path / "state"
    first = SessionManager(
        workspace=tmp_path,
        data_dir=data_dir,
        provider=ScriptedProvider(["before restart"]),
    )
    first.get_engine("parent", workspace=str(tmp_path), agent="code")
    result = first.subagent_runtime.run_foreground(
        task="first",
        profile_id="explore",
        owner_session_id="parent",
        workspace=str(tmp_path),
    )
    task_id = result.task_id
    child_session_id = first.background_tasks.get(task_id).child_session_id
    first.background_tasks.close()

    second = SessionManager(
        workspace=tmp_path,
        data_dir=data_dir,
        provider=ScriptedProvider(["after restart"]),
    )
    second.background_tasks.send_message(
        task_id, "continue", owner_session_id="parent"
    )
    done = second.background_tasks.wait(task_id, timeout=5)
    assert done.status == "completed" and done.run_count == 2
    persisted = second.session_store.load(child_session_id)
    assert [m["content"] for m in persisted.messages if m["role"] == "user"] == [
        "first",
        "continue",
    ]
    second.background_tasks.close()


def test_background_task_rest_contract_and_owner_guard(tmp_path):
    from fastapi.testclient import TestClient

    from coworker.server.app import create_app
    from coworker.server.manager import SessionManager

    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "state",
        provider=ScriptedProvider(["api report"]),
    )
    manager.get_engine("parent", workspace=str(tmp_path), agent="code")
    client = TestClient(create_app(manager))
    profiles = client.get("/v1/subagent-profiles")
    assert profiles.status_code == 200
    assert {p["id"] for p in profiles.json()["profiles"]} == {
        "explore",
        "research",
        "worker",
    }

    started = client.post(
        "/v1/background-tasks/agent",
        json={"session_id": "parent", "task": "inspect", "profile_id": "explore"},
    )
    assert started.status_code == 200
    started_task = started.json()["task"]
    task_id = started_task["id"]
    assert started_task["profile_title"] == "代码探索"
    gathered = client.post(
        "/v1/background-tasks/gather",
        json={"session_id": "parent", "task_ids": [task_id], "timeout_seconds": 5},
    )
    assert gathered.status_code == 200
    assert gathered.json()["tasks"][0]["status"] == "completed"
    output = client.get(
        f"/v1/background-tasks/{task_id}/output",
        params={"session_id": "parent", "max_chars": 100_000},
    )
    assert "api report" in str(output.json())
    assert client.get(
        f"/v1/background-tasks/{task_id}", params={"session_id": "other"}
    ).status_code == 404
    manager.background_tasks.close()


def test_background_task_change_is_pushed_to_parent_session_websocket(tmp_path):
    from fastapi.testclient import TestClient

    from coworker.server.app import create_app
    from coworker.server.manager import SessionManager

    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "state",
        provider=ScriptedProvider(["ws report"]),
    )
    app = create_app(manager)
    with TestClient(app) as client:
        with client.websocket_connect(
            f"/ws/session/parent?workspace={tmp_path}&agent=code"
        ) as ws:
            assert ws.receive_json()["type"] == "ready"
            started = client.post(
                "/v1/background-tasks/agent",
                json={
                    "session_id": "parent",
                    "task": "inspect",
                    "profile_id": "explore",
                },
            )
            assert started.status_code == 200
            task_id = started.json()["task"]["id"]
            changes = []
            for _ in range(8):
                event = ws.receive_json()
                if event["type"] == "background_task_changed":
                    changes.append(event["data"])
                    if event["data"]["task"]["status"] == "completed":
                        break
            assert changes
            assert all(change["task"]["id"] == task_id for change in changes)
            assert any(change["change"] == "output" for change in changes)
            assert changes[-1]["task"]["status"] == "completed"
