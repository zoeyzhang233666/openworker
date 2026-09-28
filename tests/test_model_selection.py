"""Session choices survive subsequent turns and an empty-session restart."""

from fastapi.testclient import TestClient

from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient
from coworker.server import SessionManager, create_app


class RecordingProvider(ProviderClient):
    def __init__(self):
        self.models = []

    def capabilities(self, model):
        return ModelCapabilities()

    def complete(self, *, model, **kwargs):
        self.models.append(model)
        return AssistantTurn(text="回答", finish_reason="stop")


def drain(ws):
    events = []
    while True:
        event = ws.receive_json()
        events.append(event)
        if event["type"] == "turn_done":
            return events


def test_empty_session_model_choice_is_saved_before_first_question(tmp_path):
    data = tmp_path / "data"
    provider = RecordingProvider()
    manager = SessionManager(data_dir=data, workspace=tmp_path, provider=provider, model="default")
    client = TestClient(create_app(manager))
    with client.websocket_connect("/ws/session/choice?agent=cowork") as ws:
        assert ws.receive_json()["data"]["model"] == "default"
        ws.send_json({"type": "set_model", "model": "chosen"})
        event = ws.receive_json()
        assert event["type"] == "model_selected"
        assert event["data"]["model"] == "chosen" and not event["data"]["text"]
        assert manager.session_store.load("choice").model == "chosen"
    restored = SessionManager(data_dir=data, workspace=tmp_path, provider=provider, model="new-default")
    assert restored.get_engine("choice").model == "chosen"
    assert restored.get_engine("other", agent="cowork").model == "new-default"
    assert not provider.models


def test_selected_model_persists_across_turns_settings_and_reconnect(tmp_path):
    provider = RecordingProvider()
    manager = SessionManager(data_dir=tmp_path / "data", workspace=tmp_path, provider=provider, model="default")
    client = TestClient(create_app(manager))
    with client.websocket_connect("/ws/session/choice?agent=cowork") as ws:
        ws.receive_json()
        ws.send_json({"type": "user_message", "text": "first", "model": "first-model"})
        drain(ws)
        ws.send_json({"type": "set_model", "model": "chosen"})
        event = ws.receive_json()
        # Ignore a possible title broadcast from the preceding turn.
        while event["type"] == "session_title":
            event = ws.receive_json()
        assert event["type"] == "model_changed"
        assert event["data"]["model"] == "chosen"
        before = len(provider.models)
        client.get("/v1/settings")
        for text in ("next", "one more"):
            ws.send_json({"type": "user_message", "text": text})
            drain(ws)
        assert provider.models[before:] and set(provider.models[before:]) == {"chosen"}
    with client.websocket_connect("/ws/session/choice?agent=cowork") as ws:
        assert ws.receive_json()["data"]["model"] == "chosen"
    assert manager.session_store.load("choice").model == "chosen"
