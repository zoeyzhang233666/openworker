"""Legal entity providers — GLEIF API first (keyless, read-only).

API clients live here (platform Tool/Provider layer), not inside bundled Skills.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional

PROVIDER_ID = "gleif"
PROVIDER_VERSION = "1.0.0"
BASE_URL = "https://api.gleif.org/api/v1"
_TIMEOUT = 20.0
_MAX_AMBIGUOUS = 5
# ISO 17442 LEI: 20 alphanumeric characters (no separators).
_LEI_RE = re.compile(r"^[A-Z0-9]{20}$")

HttpGet = Callable[[str], tuple[int, bytes]]


@dataclass
class LegalEntityCandidate:
    lei: str
    legal_name: Optional[str] = None
    registration_status: Optional[str] = None
    hq_country: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LegalEntityResult:
    status: str  # resolved | not_found | ambiguous | error
    lei: Optional[str] = None
    legal_name: Optional[str] = None
    registration_status: Optional[str] = None
    legal_jurisdiction: Optional[str] = None
    hq_country: Optional[str] = None
    hq_city: Optional[str] = None
    candidates: list[LegalEntityCandidate] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "lei": self.lei,
            "legal_name": self.legal_name,
            "registration_status": self.registration_status,
            "legal_jurisdiction": self.legal_jurisdiction,
            "hq_country": self.hq_country,
            "hq_city": self.hq_city,
            "candidates": [c.to_dict() for c in self.candidates],
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


class LegalEntityProvider(ABC):
    name: str = "base"
    requires_key: bool = False

    @abstractmethod
    def lookup(
        self, query: str, *, query_type: str = "auto"
    ) -> LegalEntityResult: ...


def looks_like_lei(value: str) -> bool:
    return bool(_LEI_RE.fullmatch(value.strip().upper()))


def _default_http_get(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ChemClaw/0.1 (+legal-entity; read-only)",
            "Accept": "application/vnd.api+json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp is not None else b""
        return int(exc.code), body


class GleifProvider(LegalEntityProvider):
    """Keyless GLEIF LEI record lookup."""

    name = PROVIDER_ID
    requires_key = False

    def __init__(self, http_get: Optional[HttpGet] = None) -> None:
        self._http_get = http_get or _default_http_get

    def lookup(
        self, query: str, *, query_type: str = "auto"
    ) -> LegalEntityResult:
        q = (query or "").strip()
        if not q:
            return self._error("query must be a non-empty string", endpoint=None)
        kind = query_type if query_type in {"lei", "name", "auto"} else "auto"
        if kind == "auto":
            kind = "lei" if looks_like_lei(q) else "name"

        if kind == "lei":
            lei = q.upper()
            if not looks_like_lei(lei):
                return self._error("query is not a valid 20-character LEI", endpoint=None)
            endpoint = f"{BASE_URL}/lei-records/{urllib.parse.quote(lei)}"
            return self._lookup_by_lei(endpoint)

        params = urllib.parse.urlencode(
            {
                "filter[entity.legalName]": q,
                "page[size]": str(_MAX_AMBIGUOUS),
            }
        )
        endpoint = f"{BASE_URL}/lei-records?{params}"
        return self._lookup_by_name(endpoint)

    def _lookup_by_lei(self, endpoint: str) -> LegalEntityResult:
        try:
            status_code, body = self._http_get(endpoint)
        except Exception as exc:
            return self._error(f"gleif request failed: {exc}", endpoint=endpoint)

        if status_code == 404:
            return LegalEntityResult(
                status="not_found",
                source=self._source(endpoint),
                warnings=["no GLEIF LEI record matched the query"],
            )
        if status_code >= 400:
            return self._error(f"gleif HTTP {status_code}", endpoint=endpoint)

        try:
            payload = json.loads(body.decode("utf-8"))
            data = payload.get("data")
            if not data:
                return LegalEntityResult(
                    status="not_found",
                    source=self._source(endpoint),
                    warnings=["empty LEI record"],
                )
            # Single-record endpoint returns one object; list returns an array.
            record = data[0] if isinstance(data, list) else data
            return self._resolved_from_record(record, endpoint=endpoint)
        except Exception as exc:
            return self._error(f"gleif response parse failed: {exc}", endpoint=endpoint)

    def _lookup_by_name(self, endpoint: str) -> LegalEntityResult:
        try:
            status_code, body = self._http_get(endpoint)
        except Exception as exc:
            return self._error(f"gleif request failed: {exc}", endpoint=endpoint)

        if status_code == 404:
            return LegalEntityResult(
                status="not_found",
                source=self._source(endpoint),
                warnings=["no GLEIF LEI record matched the query"],
            )
        if status_code >= 400:
            return self._error(f"gleif HTTP {status_code}", endpoint=endpoint)

        try:
            payload = json.loads(body.decode("utf-8"))
            data = payload.get("data") or []
            if not isinstance(data, list):
                data = [data]
        except Exception as exc:
            return self._error(f"gleif response parse failed: {exc}", endpoint=endpoint)

        if not data:
            return LegalEntityResult(
                status="not_found",
                source=self._source(endpoint),
                warnings=["empty search result"],
            )

        if len(data) > 1:
            candidates = [
                self._candidate_from_record(rec) for rec in data[:_MAX_AMBIGUOUS]
            ]
            return LegalEntityResult(
                status="ambiguous",
                candidates=candidates,
                source=self._source(endpoint),
                warnings=[
                    f"matched {len(data)} LEI records; refine the query or pick an LEI"
                ],
            )

        return self._resolved_from_record(data[0], endpoint=endpoint)

    def _resolved_from_record(
        self, record: dict[str, Any], *, endpoint: str
    ) -> LegalEntityResult:
        fields = self._extract_fields(record)
        lei = fields["lei"]
        record_url = (
            f"https://search.gleif.org/#/record/{lei}" if lei else endpoint
        )
        return LegalEntityResult(
            status="resolved",
            lei=lei,
            legal_name=fields["legal_name"],
            registration_status=fields["registration_status"],
            legal_jurisdiction=fields["legal_jurisdiction"],
            hq_country=fields["hq_country"],
            hq_city=fields["hq_city"],
            source=self._source(endpoint, url=record_url, record_id=lei),
            warnings=[],
        )

    def _candidate_from_record(self, record: dict[str, Any]) -> LegalEntityCandidate:
        fields = self._extract_fields(record)
        return LegalEntityCandidate(
            lei=fields["lei"] or "",
            legal_name=fields["legal_name"],
            registration_status=fields["registration_status"],
            hq_country=fields["hq_country"],
        )

    @staticmethod
    def _extract_fields(record: dict[str, Any]) -> dict[str, Optional[str]]:
        attrs = record.get("attributes") or {}
        entity = attrs.get("entity") or {}
        registration = attrs.get("registration") or {}
        legal_name_obj = entity.get("legalName") or {}
        hq = entity.get("headquartersAddress") or entity.get("legalAddress") or {}
        lei = attrs.get("lei") or record.get("id")
        if isinstance(lei, str):
            lei = lei.upper()
        else:
            lei = None
        legal_name = legal_name_obj.get("name") if isinstance(legal_name_obj, dict) else None
        return {
            "lei": lei,
            "legal_name": legal_name if isinstance(legal_name, str) else None,
            "registration_status": registration.get("status")
            if isinstance(registration.get("status"), str)
            else None,
            "legal_jurisdiction": entity.get("jurisdiction")
            if isinstance(entity.get("jurisdiction"), str)
            else None,
            "hq_country": hq.get("country") if isinstance(hq.get("country"), str) else None,
            "hq_city": hq.get("city") if isinstance(hq.get("city"), str) else None,
        }

    def _error(
        self, message: str, *, endpoint: Optional[str]
    ) -> LegalEntityResult:
        return LegalEntityResult(
            status="error",
            source=self._source(endpoint)
            if endpoint
            else {
                "provider_id": PROVIDER_ID,
                "provider_version": PROVIDER_VERSION,
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
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
            "endpoint": endpoint,
            "url": url or endpoint,
            "record_id": record_id,
        }
