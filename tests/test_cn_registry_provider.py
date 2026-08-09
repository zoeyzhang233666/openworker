"""China registry provider — fixture contract tests (no network)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote_plus

from coworker.entity import (
    CnRegistryProvider,
    RoutingLegalEntityProvider,
    GleifProvider,
    looks_like_uscc,
    make_lookup_legal_entity_tool,
)
from coworker.entity.cn_registry import DEFAULT_CN_BASE_URL
from coworker.entity.providers import BASE_URL as GLEIF_BASE
from coworker.secrets import SecretStore


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cn_registry"
EXAMPLE_USCC = "91110000MA0123456P"
EXAMPLE_LEI = "5493001KJTIIGC8Y1R12"
GLEIF_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gleif"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _cn_http(url: str) -> tuple[int, bytes]:
    decoded = unquote_plus(url)
    if f"uscc={EXAMPLE_USCC}" in decoded:
        return 200, _load("uscc_one_hit.json")
    if "uscc=" in decoded:
        return 404, b'{"data":[]}'
    if "name=" in decoded:
        if "歧义化工" in decoded:
            return 200, _load("name_ambiguous.json")
        if "不存在的公司xyz" in decoded:
            return 200, _load("name_empty.json")
        if "示例化工有限公司" in decoded:
            return 200, _load("uscc_one_hit.json")
        return 200, _load("name_empty.json")
    raise AssertionError(f"unexpected CN URL: {url}")


def _gleif_http(url: str) -> tuple[int, bytes]:
    decoded = unquote_plus(url)
    if f"{GLEIF_BASE}/lei-records/{EXAMPLE_LEI}" == decoded:
        return 200, (GLEIF_FIXTURES / "lei_record_example.json").read_bytes()
    if "filter[entity.legalName]=" in decoded:
        return 200, (GLEIF_FIXTURES / "name_empty.json").read_bytes()
    return 404, b"{}"


def test_looks_like_uscc():
    assert looks_like_uscc(EXAMPLE_USCC)
    assert looks_like_uscc(EXAMPLE_USCC.lower())
    assert not looks_like_uscc("91110000MA0123456X")  # bad check
    assert not looks_like_uscc("SHORT")
    assert not looks_like_uscc(EXAMPLE_LEI)


def test_resolved_by_uscc():
    p = CnRegistryProvider(http_get=_cn_http, configured=True)
    result = p.lookup(EXAMPLE_USCC, query_type="auto")
    assert result.status == "resolved"
    assert result.uscc == EXAMPLE_USCC
    assert result.legal_name == "示例化工有限公司"
    assert result.registration_status == "存续"
    assert result.legal_jurisdiction == "CN"
    assert result.hq_city == "北京"
    assert result.source["provider_id"] == "cn_registry"
    assert result.lei is None
    assert result.error is None


def test_resolved_by_chinese_name():
    p = CnRegistryProvider(http_get=_cn_http, configured=True)
    result = p.lookup("示例化工有限公司", query_type="name")
    assert result.status == "resolved"
    assert result.uscc == EXAMPLE_USCC


def test_not_found_and_ambiguous():
    p = CnRegistryProvider(http_get=_cn_http, configured=True)
    assert p.lookup("不存在的公司xyz", query_type="name").status == "not_found"
    amb = p.lookup("歧义化工", query_type="name")
    assert amb.status == "ambiguous"
    assert amb.uscc is None
    assert len(amb.candidates) == 2


def test_invalid_uscc_chinese_error():
    p = CnRegistryProvider(http_get=_cn_http, configured=True)
    result = p.lookup("91110000MA0123456X", query_type="uscc")
    assert result.status == "error"
    assert "校验位" in (result.error or "") or "无效" in (result.error or "")


def test_unconfigured_chinese_error():
    p = CnRegistryProvider(configured=False)
    result = p.lookup(EXAMPLE_USCC)
    assert result.status == "error"
    assert "未配置" in (result.error or "")
    assert "cn_registry:default" in (result.error or "")


def test_router_uscc_and_lei():
    router = RoutingLegalEntityProvider(
        gleif=GleifProvider(http_get=_gleif_http),
        cn=CnRegistryProvider(http_get=_cn_http, configured=True),
    )
    cn = router.lookup(EXAMPLE_USCC)
    assert cn.status == "resolved" and cn.uscc == EXAMPLE_USCC
    gleif = router.lookup(EXAMPLE_LEI)
    assert gleif.status == "resolved" and gleif.lei == EXAMPLE_LEI


def test_router_chinese_name_goes_cn():
    seen: list[str] = []

    def capture(url: str) -> tuple[int, bytes]:
        seen.append(url)
        return _cn_http(url)

    router = RoutingLegalEntityProvider(
        gleif=GleifProvider(http_get=_gleif_http),
        cn=CnRegistryProvider(http_get=capture, configured=True),
    )
    router.lookup("示例化工有限公司", query_type="auto")
    assert seen
    assert DEFAULT_CN_BASE_URL.split("://")[1].split("/")[0] in seen[0] or "entities" in seen[0]


def test_tool_includes_uscc_key():
    router = RoutingLegalEntityProvider(
        gleif=GleifProvider(http_get=_gleif_http),
        cn=CnRegistryProvider(http_get=_cn_http, configured=True),
    )
    tool = make_lookup_legal_entity_tool(provider=router)
    out = tool(EXAMPLE_USCC)
    assert out["uscc"] == EXAMPLE_USCC
    assert "uscc" in tool.__coworker_schema__["function"]["parameters"]["properties"][
        "query_type"
    ]["enum"] or "uscc" in str(tool.__coworker_schema__)


def test_tool_reads_cn_registry_secret(tmp_path):
    secrets = SecretStore(tmp_path / "secrets.json")
    secrets.put(
        "cn_registry:default",
        {"base_url": "https://cn-registry.test/v1", "api_key": "k"},
    )
    seen: list[str] = []

    def capture(url: str) -> tuple[int, bytes]:
        seen.append(url)
        return 200, _load("uscc_one_hit.json")

    # Inject via provider constructed like production secrets path.
    from coworker.entity.tool import _cn_from_secrets

    cn = _cn_from_secrets(secrets)
    assert cn._configured is True
    assert "cn-registry.test" in cn._base_url
    cn._http_get = capture
    result = cn.lookup(EXAMPLE_USCC)
    assert result.status == "resolved"
    assert seen and "cn-registry.test" in seen[0]
