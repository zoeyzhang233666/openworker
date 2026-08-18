"""Public API lookups catalog — 连接 → API 公开查询."""

from __future__ import annotations

from coworker.public_lookups import (
    CATALOG,
    WRITABLE_IDS,
    apply_lookup_update,
    get_lookup,
    list_lookups,
)
from coworker.secrets import SecretStore


def test_catalog_covers_platform_providers():
    ids = {e["id"] for e in CATALOG}
    assert {
        "pubchem",
        "huagongshe",
        "huagongshe_chemical",
        "huagongshe_svg",
        "huagongshe_validate",
        "huagongshe_create",
        "gleif",
        "vatcomply",
        "frankfurter",
        "wikipedia",
        "ted",
        "cn_stock_public",
        "cn_futures_public",
        "cn_option_public",
        "web_fetch",
        "customs_file",
        "web_search",
        "sam",
        "comtrade",
        "cn_registry",
    } <= ids
    assert WRITABLE_IDS == frozenset(
        {"web_search", "sam", "comtrade", "cn_registry", "huagongshe"}
    )
    for e in CATALOG:
        assert e.get("purpose_zh") and e.get("setup_zh"), e["id"]
    by_id = {e["id"]: e for e in CATALOG}
    assert by_id["sam"]["signup_url"].startswith("https://sam.gov")
    assert "境外可选" in by_id["sam"]["label_zh"]
    assert "TED" in by_id["sam"]["setup_zh"] or "ted" in by_id["sam"]["setup_zh"].lower()
    assert "境外可选" in by_id["comtrade"]["label_zh"]
    assert "海关" in by_id["comtrade"]["setup_zh"]
    assert "comtrade" in by_id["comtrade"]["signup_url"]
    assert by_id["vatcomply"]["tool"] == "validate_eu_vat"
    assert by_id["frankfurter"]["tool"] == "lookup_fx_rate"
    assert by_id["wikipedia"]["tool"] == "lookup_wikipedia"
    assert by_id["huagongshe"]["tool"] == "search_huagongshe"
    assert by_id["huagongshe"]["signup_url"].startswith("https://huagongshe.com")
    assert by_id["huagongshe"]["docs_url"] == "https://huagongshe.com/guide"
    assert "Token" in by_id["huagongshe"]["setup_zh"] and "审批" in by_id["huagongshe"]["setup_zh"]
    assert by_id["huagongshe_chemical"]["tool"] == "lookup_huagongshe_chemical"
    assert by_id["huagongshe_svg"]["tool"] == "fetch_huagongshe_svg"
    assert by_id["huagongshe_validate"]["tool"] == "validate_huagongshe_reaction"
    assert by_id["huagongshe_create"]["tool"] == "create_huagongshe_reaction"
    assert by_id["pubchem"]["signup_url"] == ""


REQUIRED_CATALOG_TOOLS = frozenset(
    {
        "lookup_chemical_identity",
        "lookup_legal_entity",
        "validate_eu_vat",
        "lookup_fx_rate",
        "lookup_wikipedia",
        "search_huagongshe",
        "lookup_huagongshe_chemical",
        "fetch_huagongshe_svg",
        "validate_huagongshe_reaction",
        "create_huagongshe_reaction",
        "search_tenders",
        "search_sam_opportunities",
        "lookup_trade_flow",
        "filter_customs_importers",
        "web_fetch",
        "web_search",
    }
)


def test_catalog_covers_registered_sales_provider_tools():
    """Every sales Provider tool on the engine must appear in API 公开查询."""
    from coworker.agent import build_engine
    from coworker.agents import chat_agent
    from coworker.providers import AssistantTurn
    from coworker.providers.base import ModelCapabilities

    class _Stub:
        def complete(self, **_kw):
            return AssistantTurn()

        def capabilities(self, _model):
            return ModelCapabilities()

    eng = build_engine(agent=chat_agent(), provider=_Stub())
    names = set(eng.registry.names())
    catalog_tools = {e["tool"] for e in CATALOG}
    missing = sorted(t for t in REQUIRED_CATALOG_TOOLS if t in names and t not in catalog_tools)
    assert missing == [], f"registered but missing from CATALOG: {missing}"
    for tid in (
        "validate_eu_vat",
        "lookup_fx_rate",
        "lookup_wikipedia",
        "search_huagongshe",
        "lookup_huagongshe_chemical",
        "fetch_huagongshe_svg",
        "validate_huagongshe_reaction",
        "create_huagongshe_reaction",
    ):
        assert tid in names and tid in catalog_tools


def test_huagongshe_optional_token_save_never_echoes(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    rows = list_lookups(secrets)
    hgs = next(r for r in rows if r["id"] == "huagongshe")
    assert hgs["ready"] is True and hgs["has_api_key"] is False
    validate_row = next(r for r in rows if r["id"] == "huagongshe_validate")
    create_row = next(r for r in rows if r["id"] == "huagongshe_create")
    assert validate_row["ready"] is False and create_row["ready"] is False

    out = apply_lookup_update("huagongshe", {"api_key": "hgs-secret-xyz"}, secrets)
    assert out["ok"] is True
    row = get_lookup("huagongshe", secrets)
    assert row["has_api_key"] is True and row["ready"] is True
    assert "hgs-secret-xyz" not in str(row)
    assert get_lookup("huagongshe_validate", secrets)["ready"] is True
    assert get_lookup("huagongshe_create", secrets)["has_api_key"] is True
    assert "hgs-secret-xyz" not in str(get_lookup("huagongshe_create", secrets))

    cleared = apply_lookup_update("huagongshe", {"clear_api_key": True}, secrets)
    assert cleared["ok"] is True
    assert get_lookup("huagongshe", secrets)["has_api_key"] is False
    assert get_lookup("huagongshe_validate", secrets)["ready"] is False


def test_list_lookups_includes_help_fields(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    rows = list_lookups(
        secrets,
        web_search_status={
            "provider": "duckduckgo",
            "has_key": False,
            "providers": ["duckduckgo"],
        },
    )
    sam = next(r for r in rows if r["id"] == "sam")
    assert "商机雷达" in sam["used_by_zh"]
    assert sam["signup_url"].startswith("https://")
    assert "api_key" not in sam or sam.get("api_key") is None


def test_free_entries_ready_without_secrets(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    rows = list_lookups(secrets, web_search_status={"provider": "duckduckgo", "has_key": False, "providers": ["duckduckgo"]})
    by_id = {r["id"]: r for r in rows}
    assert by_id["pubchem"]["ready"] is True
    assert by_id["gleif"]["configured"] is True
    assert by_id["ted"]["has_api_key"] is False
    assert by_id["customs_file"]["kind"] == "workspace_file"
    assert by_id["sam"]["configured"] is False
    assert by_id["web_search"]["ready"] is True


def test_sam_save_and_clear_never_echoes_key(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    bad = apply_lookup_update("pubchem", {"api_key": "x"}, secrets)
    assert bad["ok"] is False

    out = apply_lookup_update("sam", {"api_key": "sam-secret-xyz"}, secrets)
    assert out["ok"] is True
    row = get_lookup("sam", secrets)
    assert row["configured"] is True and row["has_api_key"] is True
    assert "sam-secret-xyz" not in str(row)

    cleared = apply_lookup_update("sam", {"clear_api_key": True}, secrets)
    assert cleared["ok"] is True
    assert get_lookup("sam", secrets)["configured"] is False


def test_cn_registry_requires_base_url(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    fail = apply_lookup_update("cn_registry", {"api_key": "k"}, secrets)
    assert fail["ok"] is False and "base_url" in fail["error"]

    ok = apply_lookup_update(
        "cn_registry",
        {"base_url": "https://registry.example.com", "api_key": "k"},
        secrets,
    )
    assert ok["ok"] is True
    row = get_lookup("cn_registry", secrets)
    assert row["base_url"] == "https://registry.example.com"
    assert row["has_api_key"] is True
    assert "k" not in str(row) or row.get("api_key") is None


def test_public_api_lookups_rest(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from coworker.server.app import create_app
    from coworker.server.manager import SessionManager

    monkeypatch.setenv("COWORKER_STATE_DIR", str(tmp_path / "state"))
    client = TestClient(create_app(SessionManager(data_dir=tmp_path / "data")))

    listed = client.get("/v1/public-api-lookups").json()
    assert isinstance(listed, list) and len(listed) >= 11
    ids = {x["id"] for x in listed}
    assert {"vatcomply", "frankfurter", "wikipedia", "huagongshe"} <= ids
    assert any(x["id"] == "pubchem" and x["ready"] for x in listed)
    assert any(x["id"] == "vatcomply" and x["ready"] and x.get("purpose_zh") for x in listed)
    assert any(x["id"] == "huagongshe" and x["ready"] for x in listed)
    blob = client.get("/v1/public-api-lookups").text
    assert '"api_key":' not in blob  # never echo secret field

    assert (
        client.post(
            "/v1/public-api-lookups/sam", json={"api_key": "live-secret-abc"}
        ).json()["ok"]
        is True
    )
    detail = client.get("/v1/public-api-lookups/sam").json()
    assert detail["configured"] is True and detail["has_api_key"] is True
    assert "live-secret-abc" not in client.get("/v1/public-api-lookups/sam").text

    assert (
        client.post(
            "/v1/public-api-lookups/pubchem", json={"api_key": "nope"}
        ).json()["ok"]
        is False
    )
    assert client.get("/v1/public-api-lookups/nope").status_code == 404
