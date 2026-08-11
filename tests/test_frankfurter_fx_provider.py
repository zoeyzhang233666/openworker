"""Frankfurter FX provider — fixture contract tests (no network)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from coworker.fx import FrankfurterProvider, make_lookup_fx_rate_tool
from coworker.fx.providers import FRANKFURTER_LATEST_URL


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "fx"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fixture_http_get(url: str, headers: dict | None = None) -> tuple[int, bytes]:
    assert url.startswith(FRANKFURTER_LATEST_URL)
    qs = parse_qs(urlparse(url).query)
    assert qs.get("from") == ["USD"]
    assert qs.get("to") == ["CNY"]
    return 200, _load("latest_usd_cny.json")


def test_lookup_rate_and_convert():
    p = FrankfurterProvider(http_get=_fixture_http_get)
    rate_only = p.lookup(base="usd", quote="cny")
    assert rate_only.status == "ok"
    assert rate_only.rate == 7.25
    assert rate_only.converted is None
    assert rate_only.as_of == "2026-08-10"

    with_amt = p.lookup(base="USD", quote="CNY", amount=100)
    assert with_amt.status == "ok"
    assert with_amt.amount == 100
    assert with_amt.converted == 725.0
    assert any("编造单价" in w for w in with_amt.warnings)


def test_same_currency():
    p = FrankfurterProvider(http_get=_fixture_http_get)
    r = p.lookup(base="CNY", quote="CNY", amount=10)
    assert r.status == "ok" and r.rate == 1.0 and r.converted == 10.0


def test_bad_currency():
    p = FrankfurterProvider(http_get=_fixture_http_get)
    r = p.lookup(base="US", quote="CNY")
    assert r.status == "error"


def test_tool_wrapper():
    tool = make_lookup_fx_rate_tool(provider=FrankfurterProvider(http_get=_fixture_http_get))
    out = tool(base="USD", quote="CNY", amount=2)
    assert out["status"] == "ok"
    assert out["converted"] == 14.5
    assert tool.__coworker_schema__["function"]["name"] == "lookup_fx_rate"
