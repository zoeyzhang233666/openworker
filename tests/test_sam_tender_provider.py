"""SAM.gov tender provider — fixture contract tests (no network)."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from coworker.secrets import SecretStore
from coworker.tender import SamProvider, make_search_sam_opportunities_tool
from coworker.tender.sam import SAM_SEARCH_URL


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sam"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fixture_http_get(url: str, headers: dict | None = None) -> tuple[int, bytes]:
    assert url.startswith(SAM_SEARCH_URL)
    qs = parse_qs(urlparse(url).query)
    assert qs.get("api_key") == ["test-key"]
    title = (qs.get("title") or [""])[0]
    if "NOMATCHXYZ" in title:
        return 200, _load("search_empty.json")
    if "sodium" in title.lower() or "benzoate" in title.lower():
        return 200, _load("search_one_hit.json")
    return 200, _load("search_empty.json")


def test_search_maps_notice_to_opportunity_signal():
    p = SamProvider(api_key="test-key", http_get=_fixture_http_get)
    result = p.search(
        query="sodium benzoate",
        limit=5,
        posted_from="01/01/2026",
        posted_to="01/31/2026",
    )
    assert result.status == "ok"
    assert len(result.signals) == 1
    sig = result.signals[0]
    assert sig["signal_type"] == "tender"
    assert sig["signal_id"] == "sam:abc123notice"
    assert "sodium benzoate" in sig["summary"].lower()
    assert sig["event_date"] == "2026-01-15"
    assert sig["source"]["provider_id"] == "sam"
    assert "sam.gov" in (sig["source"].get("url") or "")
    assert sig["source"].get("record_id") == "abc123notice"
    assert sig["buyer_country"] == "USA"
    assert result.error is None


def test_empty_search():
    p = SamProvider(api_key="test-key", http_get=_fixture_http_get)
    result = p.search(
        query="NOMATCHXYZ",
        posted_from="01/01/2026",
        posted_to="01/31/2026",
    )
    assert result.status == "empty"
    assert result.signals == []


def test_missing_api_key_chinese_error():
    p = SamProvider(api_key="", http_get=_fixture_http_get)
    result = p.search(query="x", posted_from="01/01/2026", posted_to="01/31/2026")
    assert result.status == "error"
    assert "未配置" in (result.error or "")
    assert "sam:default" in (result.error or "")
    assert "TED" in (result.error or "") or "search_tenders" in (result.error or "")
    assert "境外可选" in (result.error or "")


def test_empty_query_error():
    p = SamProvider(api_key="test-key", http_get=_fixture_http_get)
    result = p.search(query="  ", posted_from="01/01/2026", posted_to="01/31/2026")
    assert result.status == "error"
    assert result.signals == []


def test_skips_rows_without_notice_id():
    def no_id(url, headers=None):
        body = {
            "opportunitiesData": [
                {"title": "No id row", "postedDate": "2026-01-01"},
                json.loads(_load("search_one_hit.json"))["opportunitiesData"][0],
            ]
        }
        return 200, json.dumps(body).encode("utf-8")

    p = SamProvider(api_key="test-key", http_get=no_id)
    result = p.search(
        query="sodium",
        posted_from="01/01/2026",
        posted_to="01/31/2026",
    )
    assert result.status == "ok"
    assert len(result.signals) == 1
    assert result.signals[0]["signal_id"] == "sam:abc123notice"


def test_does_not_invent_ids_on_parse_fail():
    def bad(url, headers=None):
        return 200, b"not-json"

    p = SamProvider(api_key="test-key", http_get=bad)
    result = p.search(query="x", posted_from="01/01/2026", posted_to="01/31/2026")
    assert result.status == "error"
    assert result.signals == []


def test_tool_reads_secret_and_is_readonly(tmp_path):
    secrets = SecretStore(tmp_path / "secrets.json")
    secrets.put("sam:default", {"api_key": "test-key"})
    tool = make_search_sam_opportunities_tool(
        secrets=secrets,
        http_get=_fixture_http_get,
    )
    out = tool(
        query="sodium benzoate",
        limit=3,
        posted_from="01/01/2026",
        posted_to="01/31/2026",
    )
    assert out["status"] == "ok"
    assert len(out["signals"]) == 1
    assert tool.__aisuite_tool_metadata__.requires_approval is False
    assert tool.__coworker_schema__["function"]["name"] == "search_sam_opportunities"


def test_tool_missing_secret_chinese(tmp_path):
    secrets = SecretStore(tmp_path / "secrets.json")
    tool = make_search_sam_opportunities_tool(
        secrets=secrets, http_get=_fixture_http_get
    )
    out = tool(query="x", posted_from="01/01/2026", posted_to="01/31/2026")
    assert out["status"] == "error"
    assert "sam:default" in (out.get("error") or "")


def test_build_engine_registers_search_sam_opportunities():
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
    assert "search_sam_opportunities" in eng.registry.names()
