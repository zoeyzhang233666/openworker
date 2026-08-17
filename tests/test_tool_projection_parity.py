"""HARD STOP E — legacy provider-visible schema parity vs HARD STOP D snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from coworker.agent import build_engine
from coworker.agents import chat_agent, get_agent
from coworker.config import Config
from coworker.execution_profile import RequestRoute, make_execution_profile
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient
from coworker.request_router import route_request
from coworker.tool_policy import TurnToolPolicy
from coworker.tool_projection import project_provider_visible_schemas


class _Stub(ProviderClient):
    def complete(self, *, model, messages, tools=None, **settings):
        return AssistantTurn(text="ok")

    def capabilities(self, model):
        return ModelCapabilities()

    def stream(self, *, model, messages, tools=None, **settings):
        yield from ()


def _fingerprint(schema: dict) -> str:
    blob = json.dumps(schema, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _names_and_fps(schemas: list[dict] | None) -> tuple[set[str], dict[str, str]]:
    names: set[str] = set()
    fps: dict[str, str] = {}
    for sch in schemas or []:
        fn = (sch.get("function") or {}) if isinstance(sch, dict) else {}
        name = fn.get("name") or sch.get("name")
        if not name:
            continue
        names.add(name)
        fps[name] = _fingerprint(sch)
    return names, fps


SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "superpowers"
    / "plans"
    / "fixtures"
    / "hard-stop-d-legacy-tool-schema-snapshot.json"
)


def test_hard_stop_d_legacy_snapshot_exists_and_loads():
    assert SNAPSHOT_PATH.is_file()
    payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert payload["phase"] == "HARD_STOP_D"
    assert len(payload["snapshots"]) >= 2


def test_projection_off_matches_legacy_snapshot_tool_names(tmp_path):
    """tool_projection_enabled=false must restore HARD STOP D legacy exposure."""
    payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    by_label = {s["label"]: s for s in payload["snapshots"]}

    cowork = build_engine(
        agent=get_agent("cowork"),
        workspace=tmp_path,
        provider=_Stub(),
        question_asker=lambda *a, **k: {"answers": []},
        tool_projection_enabled=False,
        execution_profile=make_execution_profile(
            RequestRoute.FAST_CHAT, Config(tool_projection_enabled=False)
        ),
    )
    # Kill switch OFF → even FAST_CHAT profile must not narrow schemas.
    projected = project_provider_visible_schemas(
        cowork.registry,
        tool_projection_enabled=False,
        profile=cowork.execution_profile,
        tool_policy=TurnToolPolicy(),
    )
    names, fps = _names_and_fps(projected)
    snap = by_label["cowork_default_session"]
    assert names == set(snap["tool_names"])
    for tool_name, meta in snap["schemas"].items():
        assert fps[tool_name] == meta["fingerprint"]

    chat = build_engine(
        agent=chat_agent(),
        provider=_Stub(),
        tool_projection_enabled=False,
    )
    chat_proj = project_provider_visible_schemas(
        chat.registry,
        tool_projection_enabled=False,
        profile=None,
        tool_policy=None,
    )
    chat_names, _ = _names_and_fps(chat_proj)
    assert chat_names == set(by_label["chat_agent_session"]["tool_names"])


def test_projection_on_fast_chat_tools_none_while_registry_intact(tmp_path):
    engine = build_engine(
        agent=get_agent("cowork"),
        workspace=tmp_path,
        provider=_Stub(),
        question_asker=lambda *a, **k: {"answers": []},
        tool_projection_enabled=True,
        execution_profile=make_execution_profile(
            RequestRoute.FAST_CHAT, Config(tool_projection_enabled=True)
        ),
    )
    before = sorted(engine.registry.names())
    out = project_provider_visible_schemas(
        engine.registry,
        tool_projection_enabled=True,
        profile=engine.execution_profile,
        tool_policy=TurnToolPolicy(),
    )
    assert out is None
    assert sorted(engine.registry.names()) == before
    assert engine.registry.get("load_skill") is not None
    assert engine.registry.get("ask_user") is not None


def test_projection_on_agent_unknown_extra_tool_kept(tmp_path):
    def totally_custom_extra_tool_xyz(*, note: str = "") -> str:
        """Unknown custom dynamic tool."""
        return note

    engine = build_engine(
        agent=get_agent("cowork"),
        workspace=tmp_path,
        provider=_Stub(),
        question_asker=lambda *a, **k: {"answers": []},
        extra_tools=[totally_custom_extra_tool_xyz],
        tool_projection_enabled=True,
        execution_profile=make_execution_profile(
            RequestRoute.AGENT, Config(tool_projection_enabled=True)
        ),
        turn_tool_policy=TurnToolPolicy(),
    )
    out = project_provider_visible_schemas(
        engine.registry,
        tool_projection_enabled=True,
        profile=engine.execution_profile,
        tool_policy=TurnToolPolicy(),
    )
    names, _ = _names_and_fps(out)
    assert "totally_custom_extra_tool_xyz" in names
    assert "load_skill" in names
    assert "ask_user" in names


def test_no_external_network_agent_keeps_local_drops_unknown(tmp_path):
    def totally_custom_extra_tool_xyz(*, note: str = "") -> str:
        """Unknown custom dynamic tool."""
        return note

    cfg = Config(request_routing_enabled=True, tool_projection_enabled=True)
    decision = route_request("不要联网，读取本地 fixture 并总结", config=cfg)
    assert decision is not None
    assert decision.route is RequestRoute.AGENT
    assert decision.tool_policy.no_external_network is True

    engine = build_engine(
        agent=get_agent("cowork"),
        workspace=tmp_path,
        provider=_Stub(),
        question_asker=lambda *a, **k: {"answers": []},
        extra_tools=[totally_custom_extra_tool_xyz],
        tool_projection_enabled=True,
        execution_profile=make_execution_profile(
            decision.route, cfg, allowed_tool_names=decision.allowed_tool_names
        ),
        turn_tool_policy=decision.tool_policy,
    )
    out = project_provider_visible_schemas(
        engine.registry,
        tool_projection_enabled=True,
        profile=engine.execution_profile,
        tool_policy=decision.tool_policy,
    )
    names, _ = _names_and_fps(out)
    assert "read_file" in names
    assert "list_files" in names
    assert "ask_user" in names
    assert "web_search" not in names
    assert "web_fetch" not in names
    assert "lookup_chemical_identity" not in names
    assert "totally_custom_extra_tool_xyz" not in names
