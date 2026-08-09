"""PubChem chemical identity provider — fixture contract tests (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coworker.chem import (
    PubChemProvider,
    looks_like_cas,
    make_lookup_chemical_identity_tool,
)
from coworker.chem.providers import BASE_URL


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pubchem"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fixture_http_get(url: str) -> tuple[int, bytes]:
    if "/xref/RN/" in url and "/cids/JSON" in url:
        if "532-32-1" in url:
            return 200, _load("cids_sodium_benzoate.json")
        return 404, _load("not_found.json")
    if "/compound/name/" in url and "/cids/JSON" in url:
        if "sodium%20benzoate" in url.lower() or "Sodium%20benzoate" in url:
            return 200, _load("cids_sodium_benzoate.json")
        if "ambiguous-mix" in url:
            return 200, _load("cids_ambiguous.json")
        if "not-a-real-chem-xyz" in url:
            return 404, _load("not_found.json")
        return 404, _load("not_found.json")
    if "/compound/cid/53232/property/" in url:
        return 200, _load("props_53232.json")
    if "/compound/cid/53232/synonyms/" in url:
        return 200, _load("synonyms_53232.json")
    if "/compound/cid/2244/property/" in url:
        return 200, json.dumps(
            {"PropertyTable": {"Properties": [{"CID": 2244, "Title": "Aspirin"}]}}
        ).encode()
    if "/compound/cid/3672/property/" in url:
        return 200, json.dumps(
            {"PropertyTable": {"Properties": [{"CID": 3672, "Title": "Other"}]}}
        ).encode()
    if url.endswith("/malformed"):
        return 200, b"{not-json"
    raise AssertionError(f"unexpected URL in fixture http_get: {url}")


def test_looks_like_cas():
    assert looks_like_cas("532-32-1")
    assert not looks_like_cas("sodium benzoate")


def test_resolved_by_cas():
    p = PubChemProvider(http_get=_fixture_http_get)
    result = p.lookup("532-32-1", query_type="auto")
    assert result.status == "resolved"
    assert result.cid == 53232
    assert result.preferred_name == "Sodium benzoate"
    assert result.cas == "532-32-1"
    assert "Sodium benzoate" in result.synonyms
    assert result.source["provider_id"] == "pubchem"
    assert result.source["provider_version"] == "1.0.0"
    assert "pubchem.ncbi.nlm.nih.gov" in (result.source.get("url") or "")
    assert result.error is None


def test_resolved_by_name():
    p = PubChemProvider(http_get=_fixture_http_get)
    result = p.lookup("sodium benzoate", query_type="name")
    assert result.status == "resolved"
    assert result.cid == 53232


def test_not_found():
    p = PubChemProvider(http_get=_fixture_http_get)
    result = p.lookup("not-a-real-chem-xyz", query_type="name")
    assert result.status == "not_found"
    assert result.cid is None
    assert result.cas is None


def test_ambiguous_does_not_pick_silently():
    p = PubChemProvider(http_get=_fixture_http_get)
    result = p.lookup("ambiguous-mix", query_type="name")
    assert result.status == "ambiguous"
    assert result.cid is None
    assert len(result.candidates) == 2
    assert {c.cid for c in result.candidates} == {2244, 3672}


def test_http_error_status():
    def boom(url: str) -> tuple[int, bytes]:
        return 503, b"unavailable"

    p = PubChemProvider(http_get=boom)
    result = p.lookup("532-32-1")
    assert result.status == "error"
    assert result.cid is None
    assert result.cas is None
    assert "503" in (result.error or "")


def test_network_exception_status():
    def boom(url: str) -> tuple[int, bytes]:
        raise TimeoutError("timed out")

    p = PubChemProvider(http_get=boom)
    result = p.lookup("532-32-1")
    assert result.status == "error"
    assert result.cid is None
    assert "timed out" in (result.error or "")


def test_empty_query_error():
    p = PubChemProvider(http_get=_fixture_http_get)
    result = p.lookup("  ")
    assert result.status == "error"


def test_cas_query_builds_xref_endpoint():
    seen: list[str] = []

    def capture(url: str) -> tuple[int, bytes]:
        seen.append(url)
        return _fixture_http_get(url)

    PubChemProvider(http_get=capture).lookup("532-32-1", query_type="cas")
    assert seen
    assert seen[0].startswith(f"{BASE_URL}/compound/xref/RN/")


def test_tool_returns_fixed_keys():
    tool = make_lookup_chemical_identity_tool(
        provider=PubChemProvider(http_get=_fixture_http_get)
    )
    out = tool("532-32-1")
    for key in (
        "status",
        "cid",
        "preferred_name",
        "cas",
        "synonyms",
        "candidates",
        "source",
        "warnings",
        "error",
    ):
        assert key in out
    assert out["status"] == "resolved"
    assert tool.__coworker_schema__["function"]["name"] == "lookup_chemical_identity"
    assert tool.__aisuite_tool_metadata__.requires_approval is False


def test_build_engine_registers_lookup_tool():
    from coworker.agent import build_engine
    from coworker.agents import chat_agent

    class _Stub:
        def complete(self, *a, **k):
            raise NotImplementedError

    eng = build_engine(agent=chat_agent(), provider=_Stub())
    assert "lookup_chemical_identity" in eng.registry.names()
