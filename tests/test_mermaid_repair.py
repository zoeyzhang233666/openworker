"""Unit tests for Mermaid in-place repair helpers (D-074)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from coworker.mermaid_repair import (
    extract_mermaid_sources,
    find_message_index_for_source,
    parse_repaired_mermaid,
    repair_prompt_messages,
    replace_mermaid_source,
)
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient
from coworker.server import SessionManager, create_app
from coworker.sessions import SessionRecord


def test_extract_and_replace_first_fence():
    content = (
        "Intro\n\n```mermaid\ngraph TD\nA-->B\n```\n\n"
        "More\n\n```mermaid\ngraph LR\nX-->Y\n```\n"
    )
    bodies = extract_mermaid_sources(content)
    assert bodies[0].rstrip("\n") == "graph TD\nA-->B"
    out = replace_mermaid_source(content, "graph TD\nA-->B", "flowchart TD\nA -->|edge| B")
    assert out is not None
    assert "A -->|edge| B" in out
    assert "graph LR\nX-->Y" in out


def test_replace_missing_returns_none():
    assert replace_mermaid_source("no diagram", "graph TD\nA-->B", "x") is None


def test_find_message_prefers_ts():
    msgs = [
        {"role": "user", "content": "hi", "ts": 1.0},
        {
            "role": "assistant",
            "content": "```mermaid\nbad\n```",
            "ts": 2.0,
        },
        {
            "role": "assistant",
            "content": "```mermaid\nbad\n```",
            "ts": 3.0,
        },
    ]
    assert find_message_index_for_source(msgs, "bad", message_ts=2.0) == 1
    assert find_message_index_for_source(msgs, "bad") == 2


def test_parse_repaired_mermaid_fence_and_bare():
    assert (
        parse_repaired_mermaid("Sure:\n```mermaid\nflowchart TD\nA-->B\n```\n")
        == "flowchart TD\nA-->B"
    )
    assert parse_repaired_mermaid("flowchart TD\nA-->B") == "flowchart TD\nA-->B"
    assert parse_repaired_mermaid("I cannot fix this.") is None


def test_repair_prompt_messages_shape():
    msgs = repair_prompt_messages("graph TD\nA-->B", "Parse error")
    assert msgs[0]["role"] == "system"
    assert "fix" in msgs[0]["content"].lower() or "ONLY" in msgs[0]["content"]
    assert "Parse error" in msgs[1]["content"]
    assert "```mermaid" in msgs[1]["content"]


class _Scripted(ProviderClient):
    def __init__(self, turns):
        self._turns = list(turns)
        self.last_tools = object()

    def complete(self, *, model, messages, tools=None, **settings):
        self.last_tools = tools
        return self._turns.pop(0)

    def capabilities(self, model):
        return ModelCapabilities()


def test_repair_mermaid_rewrites_persisted_message(tmp_path):
    broken = "not valid mermaid at all"
    fixed = "flowchart TD\nA -->|ok| B"
    provider = _Scripted(
        [AssistantTurn(text=f"```mermaid\n{fixed}\n```", finish_reason="stop")]
    )
    manager = SessionManager(workspace=tmp_path, provider=provider)
    content = f"See:\n\n```mermaid\n{broken}\n```\n"
    manager.session_store.save(
        SessionRecord(
            session_id="s1",
            workspace=str(tmp_path),
            model="m",
            mode="interactive",
            messages=[
                {"role": "user", "content": "draw", "ts": 1.0},
                {"role": "assistant", "content": content, "ts": 2.0},
            ],
        )
    )
    result = manager.repair_mermaid("s1", source=broken, error="Parse error", message_ts=2.0)
    assert result["ok"] is True
    assert result["source"] == fixed
    assert provider.last_tools is None
    loaded = manager.session_store.load("s1")
    assert fixed in loaded.messages[1]["content"]
    assert broken not in loaded.messages[1]["content"]


def test_mermaid_repair_rest_endpoint(tmp_path):
    broken = "totally-broken"
    fixed = "flowchart TD\nA --> B"
    provider = _Scripted(
        [AssistantTurn(text=f"```mermaid\n{fixed}\n```", finish_reason="stop")]
    )
    manager = SessionManager(workspace=tmp_path, provider=provider)
    manager.session_store.save(
        SessionRecord(
            session_id="s2",
            workspace=str(tmp_path),
            model="m",
            mode="interactive",
            messages=[
                {
                    "role": "assistant",
                    "content": f"```mermaid\n{broken}\n```",
                    "ts": 9.0,
                }
            ],
        )
    )
    client = TestClient(create_app(manager))
    resp = client.post(
        "/v1/sessions/s2/mermaid-repair",
        json={"source": broken, "error": "boom", "message_ts": 9.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["source"] == fixed
