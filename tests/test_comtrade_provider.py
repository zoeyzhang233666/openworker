"""UN Comtrade TradeFlowProvider — fixture contract tests (no network)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from coworker.secrets import SecretStore
from coworker.trade import ComtradeProvider, make_lookup_trade_flow_tool
from coworker.trade.providers import COMTRADE_DATA_URL


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "comtrade"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fixture_http_get(url: str, headers: dict | None = None) -> tuple[int, bytes]:
    assert url.startswith(COMTRADE_DATA_URL)
    assert headers and headers.get("Ocp-Apim-Subscription-Key") == "test-key"
    qs = parse_qs(urlparse(url).query)
    cmd = (qs.get("cmdCode") or [""])[0]
    if cmd == "291631":
        return 200, _load("flow_one_hit.json")
    if cmd == "000000":
        return 200, _load("flow_empty.json")
    return 200, _load("flow_empty.json")


def test_lookup_normalizes_trade_flow():
    p = ComtradeProvider(api_key="test-key", http_get=_fixture_http_get)
    result = p.lookup(
        hs_code="291631",
        reporter="USA",
        period="2022",
        flow="M",
        partner="0",
    )
    assert result.status == "ok"
    assert len(result.flows) == 1
    row = result.flows[0]
    assert row["hs_code"] == "291631"
    assert "benzoic" in (row.get("hs_description") or "").lower()
    assert row["reporter_iso"] == "USA"
    assert row["reporter_code"] == 842
    assert row["partner_code"] == 0
    assert row["flow_code"] == "M"
    assert row["period"] == "2022"
    assert row["primary_value_usd"] == 110163575.0
    assert result.source["provider_id"] == "comtrade"
    assert "comtrade" in (result.source.get("url") or "").lower() or result.source.get(
        "endpoint"
    )
    assert any("买家" in w or "企业" in w for w in result.warnings)
    assert result.error is None


def test_empty_result():
    p = ComtradeProvider(api_key="test-key", http_get=_fixture_http_get)
    result = p.lookup(hs_code="000000", reporter="USA", period="2022")
    assert result.status == "empty"
    assert result.flows == []


def test_missing_api_key_chinese_error():
    p = ComtradeProvider(api_key="", http_get=_fixture_http_get)
    result = p.lookup(hs_code="291631", reporter="USA", period="2022")
    assert result.status == "error"
    assert "未配置" in (result.error or "")
    assert "comtrade:default" in (result.error or "")
    assert "海关" in (result.error or "") or "filter_customs" in (result.error or "")
    assert "境外可选" in (result.error or "")


def test_invalid_hs_and_reporter():
    p = ComtradeProvider(api_key="test-key", http_get=_fixture_http_get)
    bad_hs = p.lookup(hs_code="ABC", reporter="USA", period="2022")
    assert bad_hs.status == "error"
    assert bad_hs.flows == []
    bad_rep = p.lookup(hs_code="291631", reporter="ZZZ", period="2022")
    assert bad_rep.status == "error"


def test_http_error():
    def boom(url, headers=None):
        return 401, b"unauthorized"

    p = ComtradeProvider(api_key="test-key", http_get=boom)
    result = p.lookup(hs_code="291631", reporter="USA", period="2022")
    assert result.status == "error"
    assert "401" in (result.error or "")


def test_does_not_invent_flows_on_parse_fail():
    def bad(url, headers=None):
        return 200, b"not-json"

    p = ComtradeProvider(api_key="test-key", http_get=bad)
    result = p.lookup(hs_code="291631", reporter="USA", period="2022")
    assert result.status == "error"
    assert result.flows == []


def test_tool_reads_secret_and_is_readonly(tmp_path):
    secrets = SecretStore(tmp_path / "secrets.json")
    secrets.put("comtrade:default", {"api_key": "test-key"})
    tool = make_lookup_trade_flow_tool(
        secrets=secrets,
        http_get=_fixture_http_get,
    )
    out = tool(hs_code="291631", reporter="USA", period="2022")
    assert out["status"] == "ok"
    assert len(out["flows"]) == 1
    assert tool.__aisuite_tool_metadata__.requires_approval is False
    assert tool.__coworker_schema__["function"]["name"] == "lookup_trade_flow"


def test_tool_missing_secret_chinese(tmp_path):
    secrets = SecretStore(tmp_path / "secrets.json")
    tool = make_lookup_trade_flow_tool(secrets=secrets, http_get=_fixture_http_get)
    out = tool(hs_code="291631", reporter="USA", period="2022")
    assert out["status"] == "error"
    assert "comtrade:default" in (out.get("error") or "")


def test_build_engine_registers_lookup_trade_flow():
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
    assert "lookup_trade_flow" in eng.registry.names()
