"""China company registry provider — USCC / Chinese name (platform layer).

Uses a configurable HTTP backend (SecretStore `cn_registry:default`). Fixture-contract
tests inject `http_get`. Does not scrape paywalled directories; does not invent USCC.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Optional

from .providers import (
    HttpGet,
    LegalEntityCandidate,
    LegalEntityProvider,
    LegalEntityResult,
    looks_like_lei,
)

CN_PROVIDER_ID = "cn_registry"
CN_PROVIDER_VERSION = "1.0.0"
# Default base used only when secrets supply no base_url — live calls still need a real host.
DEFAULT_CN_BASE_URL = "https://cn-registry.chemclaw.local/v1"
_TIMEOUT = 20.0
_MAX_AMBIGUOUS = 5

# GB 32100 unified social credit code alphabet (no I/O/S/V/Z).
_USCC_CHARS = "0123456789ABCDEFGHJKLMNPQRTUWXY"
_USCC_WEIGHTS = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def looks_like_uscc(value: str) -> bool:
    """True when value is an 18-char USCC with a valid Mod-31 check digit."""
    s = (value or "").strip().upper()
    if len(s) != 18:
        return False
    if any(c not in _USCC_CHARS for c in s):
        return False
    total = sum(_USCC_CHARS.index(s[i]) * _USCC_WEIGHTS[i] for i in range(17))
    check = (31 - total % 31) % 31
    return _USCC_CHARS[check] == s[17]


def looks_like_chinese_name(value: str) -> bool:
    return bool(_CJK_RE.search(value or ""))


def _default_http_get(url: str, *, api_key: str = "") -> tuple[int, bytes]:
    headers = {
        "User-Agent": "ChemClaw/0.1 (+cn-registry; read-only)",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp is not None else b""
        return int(exc.code), body


class CnRegistryProvider(LegalEntityProvider):
    """Domestic registry lookup by USCC or Chinese legal name."""

    name = CN_PROVIDER_ID
    requires_key = False

    def __init__(
        self,
        http_get: Optional[HttpGet] = None,
        *,
        base_url: Optional[str] = None,
        api_key: str = "",
        configured: bool = True,
    ) -> None:
        self._http_get = http_get
        self._base_url = (base_url or DEFAULT_CN_BASE_URL).rstrip("/")
        self._api_key = api_key or ""
        # When False and no injected http_get, return a clear Chinese configuration error.
        self._configured = configured

    def lookup(
        self, query: str, *, query_type: str = "auto"
    ) -> LegalEntityResult:
        q = (query or "").strip()
        if not q:
            return self._error("查询不能为空", endpoint=None)

        kind = query_type if query_type in {"uscc", "name", "auto"} else "auto"
        if kind == "auto":
            kind = "uscc" if looks_like_uscc(q) else "name"

        if kind == "uscc":
            uscc = q.upper()
            if not looks_like_uscc(uscc):
                return self._error(
                    "统一社会信用代码格式或校验位无效（须为 18 位合法代码）",
                    endpoint=None,
                )
            params = urllib.parse.urlencode({"uscc": uscc})
        else:
            params = urllib.parse.urlencode({"name": q})

        if self._http_get is None and not self._configured:
            return LegalEntityResult(
                status="error",
                source={
                    "provider_id": CN_PROVIDER_ID,
                    "provider_version": CN_PROVIDER_VERSION,
                },
                warnings=[],
                error=(
                    "国内登记数据源未配置。请在凭据中设置 cn_registry:default "
                    "（base_url，可选 api_key）后重试。"
                ),
            )

        endpoint = f"{self._base_url}/entities?{params}"
        return self._request(endpoint)

    def _request(self, endpoint: str) -> LegalEntityResult:
        getter = self._http_get
        try:
            if getter is None:
                status_code, body = _default_http_get(
                    endpoint, api_key=self._api_key
                )
            else:
                status_code, body = getter(endpoint)
        except Exception as exc:
            return self._error(f"国内登记请求失败：{exc}", endpoint=endpoint)

        if status_code == 404:
            return LegalEntityResult(
                status="not_found",
                source=self._source(endpoint),
                warnings=["未找到匹配的国内登记主体"],
            )
        if status_code >= 400:
            return self._error(f"国内登记 HTTP {status_code}", endpoint=endpoint)

        try:
            payload = json.loads(body.decode("utf-8"))
            data = payload.get("data") or []
            if not isinstance(data, list):
                data = [data] if data else []
        except Exception as exc:
            return self._error(f"国内登记响应解析失败：{exc}", endpoint=endpoint)

        if not data:
            return LegalEntityResult(
                status="not_found",
                source=self._source(endpoint),
                warnings=["空结果"],
            )

        if len(data) > 1:
            candidates = [
                self._candidate(rec) for rec in data[:_MAX_AMBIGUOUS]
            ]
            return LegalEntityResult(
                status="ambiguous",
                candidates=candidates,
                source=self._source(endpoint),
                warnings=[
                    f"匹配到 {len(data)} 条主体；请改用统一社会信用代码或更精确名称"
                ],
            )

        return self._resolved(data[0], endpoint=endpoint)

    def _resolved(
        self, record: dict[str, Any], *, endpoint: str
    ) -> LegalEntityResult:
        fields = self._fields(record)
        uscc = fields["uscc"]
        record_url = fields.get("url") or endpoint
        return LegalEntityResult(
            status="resolved",
            lei=None,
            uscc=uscc,
            legal_name=fields["legal_name"],
            registration_status=fields["registration_status"],
            legal_jurisdiction=fields["legal_jurisdiction"] or "CN",
            hq_country=fields["hq_country"] or "CN",
            hq_city=fields["hq_city"],
            source=self._source(endpoint, url=record_url, record_id=uscc),
            warnings=[],
        )

    def _candidate(self, record: dict[str, Any]) -> LegalEntityCandidate:
        fields = self._fields(record)
        return LegalEntityCandidate(
            lei="",
            uscc=fields["uscc"],
            legal_name=fields["legal_name"],
            registration_status=fields["registration_status"],
            hq_country=fields["hq_country"] or "CN",
        )

    @staticmethod
    def _fields(record: dict[str, Any]) -> dict[str, Optional[str]]:
        uscc = record.get("uscc") or record.get("credit_code")
        if isinstance(uscc, str):
            uscc = uscc.strip().upper()
        else:
            uscc = None
        url = record.get("url") or record.get("source_url")
        return {
            "uscc": uscc if isinstance(uscc, str) else None,
            "legal_name": record.get("legal_name")
            if isinstance(record.get("legal_name"), str)
            else None,
            "registration_status": record.get("registration_status")
            if isinstance(record.get("registration_status"), str)
            else None,
            "legal_jurisdiction": record.get("legal_jurisdiction")
            if isinstance(record.get("legal_jurisdiction"), str)
            else None,
            "hq_country": record.get("hq_country")
            if isinstance(record.get("hq_country"), str)
            else None,
            "hq_city": record.get("hq_city")
            if isinstance(record.get("hq_city"), str)
            else None,
            "url": url if isinstance(url, str) else None,
        }

    def _error(
        self, message: str, *, endpoint: Optional[str]
    ) -> LegalEntityResult:
        return LegalEntityResult(
            status="error",
            source=self._source(endpoint)
            if endpoint
            else {
                "provider_id": CN_PROVIDER_ID,
                "provider_version": CN_PROVIDER_VERSION,
            },
            warnings=[],
            error=message,
        )

    @staticmethod
    def _source(
        endpoint: Optional[str],
        url: Optional[str] = None,
        record_id: Optional[str] = None,
    ) -> dict[str, Any]:
        return {
            "provider_id": CN_PROVIDER_ID,
            "provider_version": CN_PROVIDER_VERSION,
            "endpoint": endpoint,
            "url": url or endpoint,
            "record_id": record_id,
        }


class RoutingLegalEntityProvider(LegalEntityProvider):
    """Route LEI/Latin names to GLEIF; USCC / Chinese names to cn_registry."""

    name = "legal_entity_router"
    requires_key = False

    def __init__(
        self,
        *,
        gleif: LegalEntityProvider,
        cn: LegalEntityProvider,
    ) -> None:
        self._gleif = gleif
        self._cn = cn

    def lookup(
        self, query: str, *, query_type: str = "auto"
    ) -> LegalEntityResult:
        q = (query or "").strip()
        kind = (query_type or "auto").strip().lower()
        if kind not in {"auto", "lei", "name", "uscc"}:
            kind = "auto"

        if kind == "lei":
            return self._gleif.lookup(q, query_type="lei")
        if kind == "uscc":
            return self._cn.lookup(q, query_type="uscc")
        if kind == "name":
            if looks_like_chinese_name(q):
                return self._cn.lookup(q, query_type="name")
            return self._gleif.lookup(q, query_type="name")

        # auto
        if looks_like_lei(q):
            return self._gleif.lookup(q, query_type="lei")
        if looks_like_uscc(q):
            return self._cn.lookup(q, query_type="uscc")
        if looks_like_chinese_name(q):
            return self._cn.lookup(q, query_type="name")
        return self._gleif.lookup(q, query_type="name")
