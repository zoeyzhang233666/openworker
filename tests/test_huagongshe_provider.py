"""Huagongshe provider — fixture contract tests (no network)."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from coworker.huagongshe import (
    HuagongsheHttpProvider,
    make_create_huagongshe_reaction_tool,
    make_fetch_huagongshe_svg_tool,
    make_lookup_huagongshe_chemical_tool,
    make_search_huagongshe_tool,
    make_validate_huagongshe_reaction_tool,
)
from coworker.huagongshe.providers import API_BASE
from coworker.secrets import SecretStore


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "huagongshe"

_DRAFT = {
    "visibility": "private",
    "source_type": "self",
    "participants": [
        {"role": "REACTANT", "smiles": "CCO"},
        {"role": "PRODUCT", "smiles": "CCOC(=O)C"},
    ],
}


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fixture_http_get(url: str, headers: dict | None = None) -> tuple[int, bytes]:
    assert url.startswith(API_BASE)
    if "/svg/" in url and url.endswith(".svg"):
        if "/mol/517055/svg/" in url:
            return 200, _load("mol_517055.svg")
        if "/reactions/90001/svg/" in url:
            return 200, _load("mol_517055.svg")  # reuse small fixture
        return 404, b'{"detail":"not found"}'
    if "/chemicals/" in url:
        if url.rstrip("/").endswith("/517055"):
            return 200, _load("chemical_517055.json")
        return 404, b'{"detail":"not found"}'
    qs = parse_qs(urlparse(url).query)
    q = (qs.get("q") or [""])[0]
    if "NOMATCH" in q.upper():
        return 200, _load("search_empty.json")
    if headers and headers.get("Authorization") == "Bearer bad-token":
        return 401, b'{"detail":"unauthorized"}'
    return 200, _load("search_benzoate.json")


def _fixture_http_post(
    url: str, body: bytes, headers: dict | None = None
) -> tuple[int, bytes]:
    assert url.startswith(API_BASE)
    assert headers and headers.get("Authorization", "").startswith("Bearer ")
    if url.endswith("/reactions/validate"):
        payload = json.loads(body.decode("utf-8"))
        if not payload.get("participants"):
            return 422, _load("validate_422.json")
        return 200, _load("validate_ok.json")
    if url.rstrip("/").endswith("/reactions"):
        assert headers.get("Idempotency-Key"), "create must send Idempotency-Key"
        if headers.get("Authorization") == "Bearer bad-token":
            return 401, b'{"detail":"unauthorized"}'
        return 201, _load("create_ok.json")
    raise AssertionError(f"unexpected POST {url}")


def test_search_maps_chemicals():
    p = HuagongsheHttpProvider(http_get=_fixture_http_get)
    result = p.search("sodium benzoate", page_size=2)
    assert result.status == "ok"
    assert result.total == 2
    assert result.chemicals[0]["hcid"] == 517055
    assert "532-32-1" in result.chemicals[0]["cas_numbers"]
    assert any("Lead" in w or "评分" in w for w in result.warnings)


def test_search_empty_and_errors():
    p = HuagongsheHttpProvider(http_get=_fixture_http_get)
    assert p.search("NOMATCHXYZ").status == "empty"
    assert p.search("").status == "error"
    bad = HuagongsheHttpProvider(api_key="bad-token", http_get=_fixture_http_get)
    err = bad.search("x")
    assert err.status == "error"
    assert "Token" in (err.error or "") or "密钥" in (err.error or "")


def test_get_chemical():
    p = HuagongsheHttpProvider(http_get=_fixture_http_get)
    ok = p.get_chemical("517055")
    assert ok.status == "ok"
    assert ok.chemical and ok.chemical["preferred_name"] == "Sodium benzoate"
    assert ok.chemical.get("reaction_count") == 12
    assert p.get_chemical("999").status == "not_found"
    assert p.get_chemical("abc").status == "error"


def test_validate_requires_token_and_maps_ok_invalid():
    no_tok = HuagongsheHttpProvider(http_post=_fixture_http_post)
    missing = no_tok.validate_reaction(_DRAFT)
    assert missing.status == "error"
    assert "Token" in (missing.error or "")

    p = HuagongsheHttpProvider(api_key="tok-1", http_post=_fixture_http_post)
    ok = p.validate_reaction(_DRAFT)
    assert ok.status == "ok"
    assert isinstance(ok.normalized, dict)
    assert ok.normalized.get("visibility") == "private"

    bad = p.validate_reaction({"visibility": "private", "source_type": "self"})
    assert bad.status == "invalid"
    assert bad.detail is not None


def test_create_requires_token_and_idempotency_key():
    p = HuagongsheHttpProvider(api_key="tok-1", http_post=_fixture_http_post)
    no_key = p.create_reaction(_DRAFT, idempotency_key="")
    assert no_key.status == "error"
    assert "Idempotency" in (no_key.error or "")

    no_tok = HuagongsheHttpProvider(http_post=_fixture_http_post)
    missing = no_tok.create_reaction(_DRAFT, idempotency_key="idem-1")
    assert missing.status == "error"
    assert "Token" in (missing.error or "")

    ok = p.create_reaction(_DRAFT, idempotency_key="idem-1")
    assert ok.status == "ok"
    assert ok.hrid == 90001
    assert ok.idempotency_key == "idem-1"
    assert "90001" in (ok.page_url or "")


def test_tools_with_secret(tmp_path):
    secrets = SecretStore(tmp_path / "s.json")
    secrets.put("huagongshe:default", {"api_key": "tok-1"})
    search = make_search_huagongshe_tool(secrets=secrets, http_get=_fixture_http_get)
    out = search(query="sodium benzoate")
    assert out["status"] == "ok"
    assert out["source"].get("has_api_key") is True

    chem = make_lookup_huagongshe_chemical_tool(
        secrets=secrets, http_get=_fixture_http_get
    )
    detail = chem(chemical_id="517055")
    assert detail["status"] == "ok"
    assert search.__coworker_schema__["function"]["name"] == "search_huagongshe"
    assert chem.__coworker_schema__["function"]["name"] == "lookup_huagongshe_chemical"

    validate = make_validate_huagongshe_reaction_tool(
        secrets=secrets, http_post=_fixture_http_post
    )
    v = validate(reaction_json=_DRAFT)
    assert v["status"] == "ok"
    assert validate.__aisuite_tool_metadata__.requires_approval is False

    create = make_create_huagongshe_reaction_tool(
        secrets=secrets, http_post=_fixture_http_post
    )
    c = create(reaction_json=_DRAFT)
    assert c["status"] == "ok"
    assert c.get("idempotency_key")
    assert create.__aisuite_tool_metadata__.requires_approval is True
    assert create.__aisuite_tool_metadata__.risk_level == "medium"

    bare = make_validate_huagongshe_reaction_tool(
        secrets=SecretStore(tmp_path / "empty.json"),
        http_post=_fixture_http_post,
    )
    err = bare(reaction_json=_DRAFT)
    assert err["status"] == "error"
    assert "Token" in (err["error"] or "")


def test_fetch_svg_provider_ok_and_not_found():
    p = HuagongsheHttpProvider(http_get=_fixture_http_get)
    ok = p.fetch_svg(kind="chemical", entity_id="517055", width=400, height=300)
    assert ok.status == "ok"
    assert ok.kind == "chemical"
    assert ok.entity_id == "517055"
    assert ok.content and b"<svg" in ok.content
    assert ok.bytes_len == len(ok.content)
    assert ok.public_url and "/mol/517055/svg/400x300.svg" in ok.public_url
    assert "svg" not in (ok.to_dict().get("content") or "")  # never expose body in dict
    assert "content" not in ok.to_dict()

    missing = p.fetch_svg(kind="chemical", entity_id="999", width=400, height=300)
    assert missing.status == "not_found"

    rxn = p.fetch_svg(kind="reaction", entity_id="90001", width=760, height=200)
    assert rxn.status == "ok"
    assert "/reactions/90001/svg/760x200.svg" in (rxn.public_url or "")

    bad = p.fetch_svg(kind="chemical", entity_id="abc", width=400, height=300)
    assert bad.status == "error"


def test_fetch_svg_tool_writes_artifact_without_body(tmp_path):
    tool = make_fetch_huagongshe_svg_tool(
        http_get=_fixture_http_get,
        workspace_root=tmp_path,
    )
    out = tool(kind="chemical", entity_id="517055", width=400, height=300)
    assert out["status"] == "ok"
    assert out["artifact_path"] == "huagongshe_assets/mol-517055-400x300.svg"
    assert "content" not in out
    assert "<svg" not in str(out)
    assert "path" not in str(out).lower() or "d=" not in str(out)
    saved = tmp_path / out["artifact_path"]
    assert saved.is_file()
    assert b"<svg" in saved.read_bytes()
    assert out["bytes"] == saved.stat().st_size
    assert tool.__coworker_schema__["function"]["name"] == "fetch_huagongshe_svg"
    assert tool.__aisuite_tool_metadata__.requires_approval is False

    no_ws = make_fetch_huagongshe_svg_tool(http_get=_fixture_http_get, workspace_root=None)
    err = no_ws(kind="chemical", entity_id="517055")
    assert err["status"] == "error"
    assert "工作区" in (err["error"] or "") or "workspace" in (err["error"] or "").lower()
