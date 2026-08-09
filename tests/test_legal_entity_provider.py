"""GLEIF legal entity provider — fixture contract tests (no network)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote_plus

from coworker.entity import (
    GleifProvider,
    looks_like_lei,
    make_lookup_legal_entity_tool,
)
from coworker.entity.providers import BASE_URL


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gleif"
EXAMPLE_LEI = "5493001KJTIIGC8Y1R12"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fixture_http_get(url: str) -> tuple[int, bytes]:
    decoded = unquote_plus(url)
    if f"{BASE_URL}/lei-records/{EXAMPLE_LEI}" == decoded:
        return 200, _load("lei_record_example.json")
    if decoded.startswith(f"{BASE_URL}/lei-records/") and "filter[" not in decoded:
        return 404, b'{"errors":[{"status":"404"}]}'
    if "filter[entity.legalName]=" in decoded:
        if "ambiguous-mix" in decoded:
            return 200, _load("name_ambiguous.json")
        if "not-a-real-entity-xyz" in decoded:
            return 200, _load("name_empty.json")
        if "Example Chemie" in decoded:
            return 200, _load("name_one_hit.json")
        return 200, _load("name_empty.json")
    raise AssertionError(f"unexpected URL in fixture http_get: {url}")


def test_looks_like_lei():
    assert looks_like_lei(EXAMPLE_LEI)
    assert looks_like_lei(EXAMPLE_LEI.lower())
    assert not looks_like_lei("Example Chemie GmbH")
    assert not looks_like_lei("SHORT")


def test_resolved_by_lei():
    p = GleifProvider(http_get=_fixture_http_get)
    result = p.lookup(EXAMPLE_LEI, query_type="auto")
    assert result.status == "resolved"
    assert result.lei == EXAMPLE_LEI
    assert result.legal_name == "Example Chemie GmbH"
    assert result.registration_status == "ISSUED"
    assert result.legal_jurisdiction == "DE"
    assert result.hq_country == "DE"
    assert result.hq_city == "Frankfurt am Main"
    assert result.source["provider_id"] == "gleif"
    assert result.source["provider_version"] == "1.0.0"
    assert result.source["record_id"] == EXAMPLE_LEI
    assert "gleif.org" in (result.source.get("url") or "")
    assert result.error is None


def test_resolved_by_name():
    p = GleifProvider(http_get=_fixture_http_get)
    result = p.lookup("Example Chemie GmbH", query_type="name")
    assert result.status == "resolved"
    assert result.lei == EXAMPLE_LEI


def test_not_found_by_name():
    p = GleifProvider(http_get=_fixture_http_get)
    result = p.lookup("not-a-real-entity-xyz", query_type="name")
    assert result.status == "not_found"
    assert result.lei is None


def test_not_found_by_lei():
    p = GleifProvider(http_get=_fixture_http_get)
    result = p.lookup("00000000000000000000", query_type="lei")
    assert result.status == "not_found"
    assert result.lei is None


def test_ambiguous_does_not_pick_silently():
    p = GleifProvider(http_get=_fixture_http_get)
    result = p.lookup("ambiguous-mix", query_type="name")
    assert result.status == "ambiguous"
    assert result.lei is None
    assert len(result.candidates) == 2
    assert {c.lei for c in result.candidates} == {
        EXAMPLE_LEI,
        "549300ABCDEFGHIJKLMN",
    }


def test_http_error_status():
    def boom(url: str) -> tuple[int, bytes]:
        return 503, b"unavailable"

    p = GleifProvider(http_get=boom)
    result = p.lookup(EXAMPLE_LEI)
    assert result.status == "error"
    assert result.lei is None
    assert "503" in (result.error or "")


def test_network_exception_status():
    def boom(url: str) -> tuple[int, bytes]:
        raise TimeoutError("timed out")

    p = GleifProvider(http_get=boom)
    result = p.lookup(EXAMPLE_LEI)
    assert result.status == "error"
    assert result.lei is None
    assert "timed out" in (result.error or "")


def test_empty_query_error():
    p = GleifProvider(http_get=_fixture_http_get)
    result = p.lookup("  ")
    assert result.status == "error"


def test_invalid_lei_format_error():
    p = GleifProvider(http_get=_fixture_http_get)
    result = p.lookup("not-an-lei", query_type="lei")
    assert result.status == "error"
    assert result.lei is None


def test_lei_query_builds_record_endpoint():
    seen: list[str] = []

    def capture(url: str) -> tuple[int, bytes]:
        seen.append(url)
        return _fixture_http_get(url)

    GleifProvider(http_get=capture).lookup(EXAMPLE_LEI, query_type="lei")
    assert seen
    assert seen[0] == f"{BASE_URL}/lei-records/{EXAMPLE_LEI}"


def test_tool_returns_fixed_keys():
    tool = make_lookup_legal_entity_tool(
        provider=GleifProvider(http_get=_fixture_http_get)
    )
    out = tool(EXAMPLE_LEI)
    for key in (
        "status",
        "lei",
        "legal_name",
        "registration_status",
        "legal_jurisdiction",
        "hq_country",
        "hq_city",
        "candidates",
        "source",
        "warnings",
        "error",
    ):
        assert key in out
    assert out["status"] == "resolved"
    assert tool.__coworker_schema__["function"]["name"] == "lookup_legal_entity"
    assert tool.__aisuite_tool_metadata__.requires_approval is False


def test_build_engine_registers_lookup_tool():
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
    assert "lookup_legal_entity" in eng.registry.names()
