"""VATComply EU VAT provider — fixture contract tests (no network)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from coworker.vat import VatComplyProvider, make_validate_eu_vat_tool, normalize_vat_number
from coworker.vat.providers import VATCOMPLY_VAT_URL


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vat"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fixture_http_get(url: str, headers: dict | None = None) -> tuple[int, bytes]:
    assert url.startswith(VATCOMPLY_VAT_URL)
    qs = parse_qs(urlparse(url).query)
    vat = (qs.get("vat_number") or [""])[0]
    if vat == "DE123456789":
        return 200, _load("valid.json")
    if vat == "DE811111125":
        return 200, _load("invalid.json")
    return 200, _load("invalid.json")


def test_normalize_vat_strips_spaces():
    assert normalize_vat_number("de 123 456 789") == "DE123456789"


def test_valid_vat_maps_fields():
    p = VatComplyProvider(http_get=_fixture_http_get)
    result = p.validate("DE 123 456 789")
    assert result.status == "valid"
    assert result.valid is True
    assert result.vat_number == "DE123456789"
    assert result.country_code == "DE"
    assert result.name == "Example Chemie GmbH"
    assert "Berlin" in (result.address or "")
    assert result.source["provider_id"] == "vatcomply"
    assert result.source["record_id"] == "DE123456789"
    assert any("法律结论" in w for w in result.warnings)
    assert result.error is None


def test_invalid_vat():
    p = VatComplyProvider(http_get=_fixture_http_get)
    result = p.validate("DE811111125")
    assert result.status == "invalid"
    assert result.valid is False
    assert result.name is None
    assert result.address is None


def test_empty_and_bad_format():
    p = VatComplyProvider(http_get=_fixture_http_get)
    empty = p.validate("   ")
    assert empty.status == "error"
    assert "请提供" in (empty.error or "")

    bad = p.validate("12345")
    assert bad.status == "error"
    assert "格式无效" in (bad.error or "")


def test_http_error():
    def boom(url, headers=None):
        return 503, b"unavailable"

    p = VatComplyProvider(http_get=boom)
    result = p.validate("DE123456789")
    assert result.status == "error"
    assert "503" in (result.error or "")


def test_tool_wrapper():
    tool = make_validate_eu_vat_tool(provider=VatComplyProvider(http_get=_fixture_http_get))
    out = tool(vat_number="DE123456789")
    assert out["status"] == "valid"
    assert out["vat_number"] == "DE123456789"
    assert tool.__coworker_schema__["function"]["name"] == "validate_eu_vat"
