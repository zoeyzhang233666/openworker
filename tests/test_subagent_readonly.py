from __future__ import annotations

import asyncio
import pytest
import aisuite as ai

from coworker.background_tasks.models import BackgroundTaskRecord
from coworker.permissions import Mode
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient, ToolCall
from coworker.risk import RiskClass
from coworker.server.manager import SessionManager
from coworker.tool_policy import TurnToolPolicy


class Provider(ProviderClient):
    def __init__(self, turns=()):
        self.turns = iter(turns)

    def complete(self, **kwargs):
        return next(self.turns)

    def capabilities(self, model):
        return ModelCapabilities()


def child_pair(tmp_path, provider=None):
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "state", provider=provider or Provider())
    parent = manager.get_engine("parent", workspace=str(tmp_path), agent="cowork")
    parent.permissions.mode = Mode.AUTO
    record = BackgroundTaskRecord(id="child", kind="agent", status="queued", owner_session_id="parent",
        description="research", workspace=str(tmp_path), profile_id="research", child_session_id="__child",
        created_at=1, updated_at=1)
    return manager, parent, record


def test_readonly_is_enforced_before_special_tools_and_parent_auto(tmp_path):
    provider = Provider([AssistantTurn(tool_calls=[
        ToolCall(id="write", name="write_file", arguments={"path": "bad.txt", "content": "bad"}),
        ToolCall(id="plan", name="propose_plan", arguments={}),
    ], finish_reason="tool_calls"), AssistantTurn(text="Need parent assistance", finish_reason="stop")])
    manager, parent, record = child_pair(tmp_path, provider)
    child = manager._build_subagent_engine(record, manager.subagent_runtime.profiles.require("research"))
    try:
        assert child.permissions.mode is Mode.PLAN
        assert not {"write_file", "run_shell", "send_message", "start_subagent"} & set(child.registry.names())
        events = asyncio.run(_consume(child.run("research")))
        assert not (tmp_path / "bad.txt").exists()
        assert child.permissions.mode is Mode.PLAN
        assert sum(e.data.get("status") == "denied" for e in events) == 2
        assert child.checkpoint_sink is not None and child.compaction_settings == manager.compaction_settings
        child.checkpoint_sink()
        assert manager.session_store.load("__child") is not None
    finally:
        manager.background_tasks.close()


async def _consume(stream):
    return [event async for event in stream]


def test_mcp_low_risk_and_name_are_not_readonly_evidence(tmp_path):
    manager, parent, record = child_pair(tmp_path)
    def mcp__uncommon__get_data():
        return "data"
    parent.registry.register(mcp__uncommon__get_data, metadata=ai.ToolMetadata(
        category="mcp", requires_approval=False, risk_level="low"))
    profile = manager.subagent_runtime.profiles.require("research")
    try:
        child = manager._build_subagent_engine(record, profile)
        assert "mcp__uncommon__get_data" not in child.registry.names()
        parent.permissions.risk_overrides = lambda name: RiskClass.READ if name == "mcp__uncommon__get_data" else None
        child = manager._build_subagent_engine(record, profile)
        assert "mcp__uncommon__get_data" in child.registry.names()
        parent.turn_tool_policy = TurnToolPolicy(no_external_network=True)
        child = manager._build_subagent_engine(record, profile)
        child._activate_plan("find data")
        assert child._turn_plan_tool_guard("mcp__uncommon__get_data")[0] is False
    finally:
        manager.background_tasks.close()


@pytest.mark.parametrize("profile", ["worker", "market_report"])
def test_retired_write_profiles_cannot_start_or_rehydrate(tmp_path, profile):
    manager, parent, record = child_pair(tmp_path)
    try:
        with pytest.raises(ValueError, match="主助手"):
            manager.subagent_runtime.start(task="write", profile_id=profile, owner_session_id="parent", workspace=str(tmp_path))
        with pytest.raises(ValueError, match="主助手"):
            manager.subagent_runtime.adapter_for_record(record.model_copy(update={"profile_id": profile}))
        assert {p["id"] for p in manager.list_subagent_profiles()} == {"explore", "research"}
    finally:
        manager.background_tasks.close()
