"""TED tender provider — fixture contract tests (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coworker.tender import TedProvider, make_search_tenders_tool
from coworker.tender.providers import TED_SEARCH_URL


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ted"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fixture_http_post(url: str, body: bytes, headers: dict | None = None):
    assert url == TED_SEARCH_URL
    payload = json.loads(body.decode("utf-8"))
    assert "query" in payload
    q = payload["query"]
    if "NOMATCHXYZ" in q:
        return 200, _load("search_empty.json")
    if "sodium" in q.lower() or "benzoate" in q.lower():
        return 200, _load("search_one_hit.json")
    return 200, _load("search_empty.json")


def test_search_maps_notice_to_opportunity_signal():
    p = TedProvider(http_post=_fixture_http_post)
    result = p.search(query='FT~"sodium benzoate"', limit=5)
    assert result.status == "ok"
    assert len(result.signals) == 1
    sig = result.signals[0]
    assert sig["signal_type"] == "tender"
    assert sig["signal_id"].startswith("ted:")
    assert "123456-2026" in sig["signal_id"]
    assert "sodium benzoate" in sig["summary"].lower()
    assert sig["event_date"] == "2026-01-15"
    assert sig["source"]["provider_id"] == "ted"
    assert "ted.europa.eu" in (sig["source"].get("url") or "")
    assert sig["source"].get("record_id") == "123456-2026"
    assert sig["buyer_hint"] == "Example City Hospital"
    assert sig["buyer_country"] == "DEU"
    assert result.error is None


def test_empty_search():
    p = TedProvider(http_post=_fixture_http_post)
    result = p.search(query='FT~"NOMATCHXYZ"')
    assert result.status == "empty"
    assert result.signals == []


def test_empty_query_error():
    p = TedProvider(http_post=_fixture_http_post)
    result = p.search(query="  ")
    assert result.status == "error"
    assert result.signals == []
    assert result.error


def test_http_error():
    def boom(url, body, headers=None):
        return 503, b"unavailable"

    p = TedProvider(http_post=boom)
    result = p.search(query='FT~"x"')
    assert result.status == "error"
    assert "503" in (result.error or "")


def test_does_not_invent_publication_number_on_parse_fail():
    def bad(url, body, headers=None):
        return 200, b"not-json"

    p = TedProvider(http_post=bad)
    result = p.search(query='FT~"x"')
    assert result.status == "error"
    assert not any(
        "ted:" in (s.get("signal_id") or "") for s in result.signals
    )


def test_tool_returns_signals_and_is_readonly():
    tool = make_search_tenders_tool(
        provider=TedProvider(http_post=_fixture_http_post)
    )
    out = tool(query='FT~"sodium benzoate"', limit=3)
    assert out["status"] == "ok"
    assert len(out["signals"]) == 1
    assert tool.__aisuite_tool_metadata__.requires_approval is False
    assert tool.__coworker_schema__["function"]["name"] == "search_tenders"


def test_build_engine_registers_search_tenders():
    from coworker.agent import build_engine
    from coworker.agents import chat_agent

    class _Stub:
        def complete(self, **_kw):
            from coworker.providers import AssistantTurn

            return AssistantTurn()

        def capabilities(self, _model):
            from coworker.providers.base import ModelCapabilities

            return ModelCapabilities()

    eng = build_engine(agent=chat_agent(), provider=_Stub())
    assert "search_tenders" in eng.registry.names()
