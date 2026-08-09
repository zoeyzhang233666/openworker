"""TED (Tenders Electronic Daily) search provider — keyless, read-only.

API clients live here (platform Tool/Provider layer), not inside bundled Skills.
Maps notices to OpportunitySignal-shaped dicts for chem-opportunity-radar.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

PROVIDER_ID = "ted"
PROVIDER_VERSION = "1.0.0"
TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
_TIMEOUT = 30.0
_MAX_LIMIT = 50
_DEFAULT_FIELDS = [
    "publication-number",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "publication-date",
    "classification-cpv",
    "links",
]

# (url, body, headers) -> (status_code, response_body)
HttpPost = Callable[..., tuple[int, bytes]]


@dataclass
class TenderSearchResult:
    status: str  # ok | empty | error
    signals: list[dict[str, Any]] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": list(self.signals),
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


class TenderProvider(ABC):
    name: str = "base"

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        buyer_country: str = "",
        cpv: str = "",
    ) -> TenderSearchResult: ...


def _default_http_post(
    url: str, body: bytes, headers: Optional[dict[str, str]] = None
) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        data=body,
        headers=headers
        or {
            "User-Agent": "ChemClaw/0.1 (+ted-tender; read-only)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp is not None else b""
        return int(exc.code), raw


def _pick_lang(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("eng", "en", "EN", "deu", "de", "fra", "fr"):
            v = value.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for v in value.values():
            if isinstance(v, str) and v.strip():
                return v.strip()
            if isinstance(v, list) and v and isinstance(v[0], str):
                return v[0].strip()
    if isinstance(value, list) and value:
        return _pick_lang(value[0])
    return None


def _normalize_date(raw: Any) -> Optional[str]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    # TED often returns YYYY-MM-DDZ or YYYYMMDD
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) >= 8:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return None


def _notice_url(notice: dict[str, Any], publication_number: str) -> str:
    links = notice.get("links")
    if isinstance(links, dict):
        for key in ("html", "HTML", "canonical", "self"):
            u = links.get(key)
            if isinstance(u, str) and u.startswith("http"):
                return u
    if publication_number:
        return f"https://ted.europa.eu/en/notice/-/detail/{publication_number}"
    return TED_SEARCH_URL


class TedProvider(TenderProvider):
    """Keyless TED Search API (POST /v3/notices/search)."""

    name = PROVIDER_ID

    def __init__(self, http_post: Optional[HttpPost] = None) -> None:
        self._http_post = http_post or _default_http_post

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        buyer_country: str = "",
        cpv: str = "",
    ) -> TenderSearchResult:
        q = (query or "").strip()
        if not q:
            return TenderSearchResult(
                status="error",
                source=self._source(),
                error="查询不能为空；请提供 TED expert 检索式或关键词",
            )

        parts = [q]
        country = (buyer_country or "").strip().upper()
        if country and f"buyer-country=" not in q:
            parts.append(f"buyer-country={country}")
        cpv_code = (cpv or "").strip()
        if cpv_code and "classification-cpv=" not in q:
            parts.append(f"classification-cpv={cpv_code}")
        expert = " AND ".join(parts)
        if "SORT BY" not in expert.upper():
            expert = f"{expert} SORT BY publication-date DESC"

        lim = max(1, min(int(limit or 10), _MAX_LIMIT))
        payload = {
            "query": expert,
            "fields": list(_DEFAULT_FIELDS),
            "limit": lim,
            "scope": "ACTIVE",
            "paginationMode": "ITERATION",
        }
        body = json.dumps(payload).encode("utf-8")

        try:
            status_code, raw = self._http_post(
                TED_SEARCH_URL,
                body,
                {
                    "User-Agent": "ChemClaw/0.1 (+ted-tender; read-only)",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        except Exception as exc:
            return TenderSearchResult(
                status="error",
                source=self._source(),
                error=f"TED 请求失败：{exc}",
            )

        if status_code >= 400:
            return TenderSearchResult(
                status="error",
                source=self._source(),
                error=f"TED HTTP {status_code}",
            )

        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            return TenderSearchResult(
                status="error",
                source=self._source(),
                error=f"TED 响应解析失败：{exc}",
            )

        notices = data.get("notices")
        if notices is None:
            notices = data.get("results") or data.get("data") or []
        if not isinstance(notices, list):
            return TenderSearchResult(
                status="error",
                source=self._source(),
                error="TED 响应缺少 notices 数组",
            )

        collected = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        signals: list[dict[str, Any]] = []
        for notice in notices[:lim]:
            if not isinstance(notice, dict):
                continue
            sig = self._to_signal(notice, collected_at=collected)
            if sig is not None:
                signals.append(sig)

        if not signals:
            return TenderSearchResult(
                status="empty",
                signals=[],
                source=self._source(),
                warnings=["未找到匹配的 TED 公告"],
            )

        return TenderSearchResult(
            status="ok",
            signals=signals,
            source=self._source(),
            warnings=[],
        )

    def _to_signal(
        self, notice: dict[str, Any], *, collected_at: str
    ) -> Optional[dict[str, Any]]:
        pub = notice.get("publication-number") or notice.get("publicationNumber")
        if not isinstance(pub, str) or not pub.strip():
            # Refuse to invent TED numbers
            return None
        pub = pub.strip()
        title = _pick_lang(notice.get("notice-title") or notice.get("title")) or pub
        buyer = _pick_lang(notice.get("buyer-name") or notice.get("buyerName"))
        country = notice.get("buyer-country") or notice.get("buyerCountry")
        if isinstance(country, str):
            country = country.strip().upper() or None
        else:
            country = None
        event_date = _normalize_date(
            notice.get("publication-date") or notice.get("publicationDate")
        )
        url = _notice_url(notice, pub)
        summary_parts = [title]
        if buyer:
            summary_parts.append(f"buyer={buyer}")
        if country:
            summary_parts.append(f"country={country}")
        return {
            "signal_id": f"ted:{pub}",
            "signal_type": "tender",
            "summary": "; ".join(summary_parts),
            "event_date": event_date,
            "collected_at": collected_at,
            "buyer_hint": buyer,
            "buyer_country": country,
            "source": {
                "provider_id": PROVIDER_ID,
                "provider_version": PROVIDER_VERSION,
                "type": "government_registry",
                "locator": f"ted:{pub}",
                "url": url,
                "record_id": pub,
            },
        }

    @staticmethod
    def _source() -> dict[str, Any]:
        return {
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
            "endpoint": TED_SEARCH_URL,
            "url": "https://ted.europa.eu/",
        }
