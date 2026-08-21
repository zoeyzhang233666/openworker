from __future__ import annotations

from fastapi.testclient import TestClient

from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient
from coworker.server import SessionManager, create_app


class NoCallProvider(ProviderClient):
    def complete(self, **kwargs):  # pragma: no cover - validation must stop first
        raise AssertionError("provider must not be called")

    def capabilities(self, model):
        return ModelCapabilities()


class SingleTurnProvider(ProviderClient):
    def complete(self, **kwargs):
        return AssistantTurn(text="ok", finish_reason="stop")

    def capabilities(self, model):
        return ModelCapabilities()


def _client(tmp_path):
    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "data",
        provider=NoCallProvider(),
    )
    return TestClient(create_app(manager)), manager


def test_scenario_list_and_preview_use_live_planner_without_side_effects(tmp_path) -> None:
    client, manager = _client(tmp_path)
    scenarios = client.get("/v1/scenarios").json()["scenarios"]
    assert {item["id"] for item in scenarios} == {
        "chemical_spot_price",
        "cn_futures_market",
        "chemical_identity",
        "chemical_company_research",
        "chemical_market_research",
    }
    # The GUI previews an initialized live session; system prompt initialization is
    # outside Preview, and the Preview itself must not append anything.
    assert manager.get_engine("preview-session") is not None
    before_messages = manager.session_messages("preview-session")
    before_traces = manager.list_turn_traces(session_id="preview-session")
    response = client.post(
        "/v1/sessions/preview-session/plan-preview",
        json={"text": "查询 CAS 67-56-1"},
    )
    assert response.status_code == 200
    preview = response.json()["preview"]
    assert preview["scenario"]["scenario_id"] == "chemical_identity"
    assert preview["selected_tool_names"] == ["lookup_chemical_identity"]
    assert manager.session_messages("preview-session") == before_messages
    assert manager.list_turn_traces(session_id="preview-session") == before_traces


def test_invalid_explicit_scenario_is_422_for_rest_and_input_rejected_for_ws(tmp_path) -> None:
    client, _manager = _client(tmp_path)
    response = client.post(
        "/v1/sessions/s1/plan-preview",
        json={"text": "hello", "scenario_id": "missing"},
    )
    assert response.status_code == 422

    with client.websocket_connect("/ws/session/s2?agent=cowork") as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_json(
            {"type": "user_message", "text": "hello", "scenario_id": "missing"}
        )
        rejected = ws.receive_json()
        assert rejected["type"] == "input_rejected"
        assert "Unknown scenario_id" in rejected["data"]["error"]


def test_trace_list_and_detail_contract(tmp_path) -> None:
    client, manager = _client(tmp_path)
    from coworker.tracing import TurnTraceRecorder

    trace = TurnTraceRecorder(session_id="s", model="m", plan=None).finish()
    manager.trace_store.append(trace)
    listed = client.get("/v1/turn-traces", params={"session_id": "s", "limit": 999}).json()
    assert listed["traces"][0]["trace_id"] == trace.trace_id
    detail = client.get(f"/v1/turn-traces/{trace.trace_id}")
    assert detail.status_code == 200
    assert detail.json()["trace"]["session_id"] == "s"
    assert client.get("/v1/turn-traces/not-found").status_code == 404


def test_ws_accepts_scenario_id_and_emits_trace_summary(tmp_path) -> None:
    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "data-ws",
        provider=SingleTurnProvider(),
    )
    client = TestClient(create_app(manager))
    with client.websocket_connect("/ws/session/trace-ws?agent=cowork") as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_json(
            {
                "type": "user_message",
                "text": "查询 CAS 67-56-1",
                "scenario_id": "chemical_identity",
            }
        )
        events = []
        while True:
            event = ws.receive_json()
            events.append(event)
            if event["type"] == "turn_done":
                break
    turn_start = next(item for item in events if item["type"] == "turn_start")
    turn_end = next(item for item in events if item["type"] == "turn_end")
    assert turn_start["data"]["trace_id"] == turn_end["data"]["trace_id"]
    assert turn_start["data"]["plan_summary"]["scenario"]["scenario_id"] == "chemical_identity"
    stored = client.get(
        "/v1/turn-traces", params={"session_id": "trace-ws"}
    ).json()["traces"]
    assert stored[0]["trace_id"] == turn_start["data"]["trace_id"]
    assert stored[0]["model_calls"] == 1
