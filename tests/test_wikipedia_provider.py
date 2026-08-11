"""Wikipedia MediaWiki provider — fixture contract tests (no network)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from coworker.wiki import MediaWikiWikipediaProvider, make_lookup_wikipedia_tool


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wiki"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fixture_http_get(url: str, headers: dict | None = None) -> tuple[int, bytes]:
    assert "wikipedia.org/w/api.php" in url
    qs = parse_qs(urlparse(url).query)
    title = (qs.get("titles") or [""])[0]
    if "NO_SUCH" in title:
        return 200, _load("missing.json")
    return 200, _load("zh_benzoate.json")


def test_lookup_extract():
    p = MediaWikiWikipediaProvider(http_get=_fixture_http_get)
    result = p.lookup("苯甲酸钠", lang="zh")
    assert result.status == "ok"
    assert result.title == "苯甲酸钠"
    assert "防腐剂" in (result.extract or "")
    assert result.page_url and "wikipedia.org" in result.page_url
    assert any("百科" in w for w in result.warnings)


def test_not_found():
    p = MediaWikiWikipediaProvider(http_get=_fixture_http_get)
    result = p.lookup("NO_SUCH_CHEM_PAGE_XYZ", lang="zh")
    assert result.status == "not_found"


def test_bad_lang_and_empty():
    p = MediaWikiWikipediaProvider(http_get=_fixture_http_get)
    assert p.lookup("x", lang="fr").status == "error"
    assert p.lookup("  ").status == "error"


def test_tool_wrapper():
    tool = make_lookup_wikipedia_tool(
        provider=MediaWikiWikipediaProvider(http_get=_fixture_http_get)
    )
    out = tool(title="苯甲酸钠", lang="zh")
    assert out["status"] == "ok"
    assert tool.__coworker_schema__["function"]["name"] == "lookup_wikipedia"
