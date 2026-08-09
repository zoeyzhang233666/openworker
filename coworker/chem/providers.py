"""Chemical identity providers — PubChem PUG-REST first (keyless, read-only).

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

PROVIDER_ID = "pubchem"
PROVIDER_VERSION = "1.0.0"
BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_TIMEOUT = 20.0
_MAX_SYNONYMS = 20
_MAX_AMBIGUOUS = 5
_CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
_CAS_IN_TEXT = re.compile(r"\b(\d{2,7}-\d{2}-\d)\b")

HttpGet = Callable[[str], tuple[int, bytes]]


@dataclass
class IdentityCandidate:
    cid: int
    preferred_name: Optional[str] = None
    cas: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChemicalIdentityResult:
    status: str  # resolved | not_found | ambiguous | error
    cid: Optional[int] = None
    preferred_name: Optional[str] = None
    cas: Optional[str] = None
    synonyms: list[str] = field(default_factory=list)
    candidates: list[IdentityCandidate] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "cid": self.cid,
            "preferred_name": self.preferred_name,
            "cas": self.cas,
            "synonyms": list(self.synonyms),
            "candidates": [c.to_dict() for c in self.candidates],
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


class ChemicalIdentityProvider(ABC):
    name: str = "base"
    requires_key: bool = False

    @abstractmethod
    def lookup(
        self, query: str, *, query_type: str = "auto"
    ) -> ChemicalIdentityResult: ...


def looks_like_cas(value: str) -> bool:
    return bool(_CAS_RE.fullmatch(value.strip()))


def _default_http_get(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ChemClaw/0.1 (+chemical-identity; read-only)"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp is not None else b""
        return int(exc.code), body


class PubChemProvider(ChemicalIdentityProvider):
    """Keyless PubChem PUG-REST chemical identity lookup."""

    name = PROVIDER_ID
    requires_key = False

    def __init__(self, http_get: Optional[HttpGet] = None) -> None:
        self._http_get = http_get or _default_http_get

    def lookup(
        self, query: str, *, query_type: str = "auto"
    ) -> ChemicalIdentityResult:
        q = (query or "").strip()
        if not q:
            return self._error("query must be a non-empty string", endpoint=None)
        kind = query_type if query_type in {"cas", "name", "auto"} else "auto"
        if kind == "auto":
            kind = "cas" if looks_like_cas(q) else "name"

        if kind == "cas":
            endpoint = f"{BASE_URL}/compound/xref/RN/{urllib.parse.quote(q)}/cids/JSON"
        else:
            endpoint = f"{BASE_URL}/compound/name/{urllib.parse.quote(q)}/cids/JSON"

        try:
            status_code, body = self._http_get(endpoint)
        except Exception as exc:  # network / timeout
            return self._error(f"pubchem request failed: {exc}", endpoint=endpoint)

        if status_code == 404 or self._is_not_found(body):
            return ChemicalIdentityResult(
                status="not_found",
                source=self._source(endpoint),
                warnings=["no PubChem CID matched the query"],
            )
        if status_code >= 400:
            return self._error(
                f"pubchem HTTP {status_code}",
                endpoint=endpoint,
            )

        try:
            payload = json.loads(body.decode("utf-8"))
            cids = list(payload.get("IdentifierList", {}).get("CID") or [])
        except Exception as exc:
            return self._error(f"pubchem response parse failed: {exc}", endpoint=endpoint)

        if not cids:
            return ChemicalIdentityResult(
                status="not_found",
                source=self._source(endpoint),
                warnings=["empty CID list"],
            )

        if len(cids) > 1:
            candidates = self._candidate_summaries(cids[:_MAX_AMBIGUOUS])
            return ChemicalIdentityResult(
                status="ambiguous",
                candidates=candidates,
                source=self._source(endpoint),
                warnings=[
                    f"matched {len(cids)} CIDs; refine the query or pick a CID"
                ],
            )

        cid = int(cids[0])
        return self._resolve_cid(cid, cids_endpoint=endpoint)

    def _resolve_cid(self, cid: int, *, cids_endpoint: str) -> ChemicalIdentityResult:
        prop_url = (
            f"{BASE_URL}/compound/cid/{cid}/property/Title,IUPACName/JSON"
        )
        syn_url = f"{BASE_URL}/compound/cid/{cid}/synonyms/JSON"
        warnings: list[str] = []
        preferred: Optional[str] = None
        synonyms: list[str] = []
        cas: Optional[str] = None

        try:
            code, body = self._http_get(prop_url)
            if code == 200:
                props = json.loads(body.decode("utf-8")).get("PropertyTable", {}).get(
                    "Properties"
                ) or []
                if props:
                    preferred = props[0].get("Title") or props[0].get("IUPACName")
            else:
                warnings.append(f"property lookup HTTP {code}")
        except Exception as exc:
            warnings.append(f"property lookup failed: {exc}")

        try:
            code, body = self._http_get(syn_url)
            if code == 200:
                info = (
                    json.loads(body.decode("utf-8"))
                    .get("InformationList", {})
                    .get("Information")
                    or []
                )
                if info:
                    raw = info[0].get("Synonym") or []
                    synonyms = [s for s in raw if isinstance(s, str)][:_MAX_SYNONYMS]
                    cas = _extract_cas(synonyms)
            else:
                warnings.append(f"synonym lookup HTTP {code}")
        except Exception as exc:
            warnings.append(f"synonym lookup failed: {exc}")

        compound_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
        return ChemicalIdentityResult(
            status="resolved",
            cid=cid,
            preferred_name=preferred,
            cas=cas,
            synonyms=synonyms,
            source=self._source(cids_endpoint, compound_url=compound_url),
            warnings=warnings,
        )

    def _candidate_summaries(self, cids: list[Any]) -> list[IdentityCandidate]:
        out: list[IdentityCandidate] = []
        for raw in cids:
            cid = int(raw)
            name: Optional[str] = None
            try:
                url = f"{BASE_URL}/compound/cid/{cid}/property/Title/JSON"
                code, body = self._http_get(url)
                if code == 200:
                    props = json.loads(body.decode("utf-8")).get(
                        "PropertyTable", {}
                    ).get("Properties") or []
                    if props:
                        name = props[0].get("Title")
            except Exception:
                name = None
            out.append(IdentityCandidate(cid=cid, preferred_name=name))
        return out

    def _error(self, message: str, *, endpoint: Optional[str]) -> ChemicalIdentityResult:
        return ChemicalIdentityResult(
            status="error",
            source=self._source(endpoint) if endpoint else {
                "provider_id": PROVIDER_ID,
                "provider_version": PROVIDER_VERSION,
            },
            warnings=[],
            error=message,
        )

    @staticmethod
    def _source(endpoint: Optional[str], compound_url: Optional[str] = None) -> dict[str, Any]:
        return {
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
            "endpoint": endpoint,
            "url": compound_url or endpoint,
        }

    @staticmethod
    def _is_not_found(body: bytes) -> bool:
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return False
        fault = payload.get("Fault") or {}
        code = str(fault.get("Code") or "")
        return "NotFound" in code


def _extract_cas(synonyms: list[str]) -> Optional[str]:
    for syn in synonyms:
        if looks_like_cas(syn):
            return syn.strip()
        match = _CAS_IN_TEXT.search(syn)
        if match:
            return match.group(1)
    return None
