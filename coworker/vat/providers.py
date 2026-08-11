"""EU VAT validation via VATComply — keyless, read-only.

API clients live here (platform Tool/Provider layer), not inside bundled Skills.
Does not issue legal conclusions or replace company registry lookups.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

PROVIDER_ID = "vatcomply"
PROVIDER_VERSION = "1.0.0"
VATCOMPLY_VAT_URL = "https://api.vatcomply.com/vat"
VATCOMPLY_DOCS_URL = "https://www.vatcomply.com/documentation"
_TIMEOUT = 30.0
# Country code (2 letters) + national number (2–12 alnum). Spaces/punctuation stripped.
_VAT_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{2,12}$")
_LEGAL_WARNING = (
    "VAT 核验仅为公开登记辅助，不是法律结论；不得据此单独判定 Qualified。"
)

# (url, headers) -> (status_code, response_body)
HttpGet = Callable[..., tuple[int, bytes]]


@dataclass
class VatValidationResult:
    status: str  # valid | invalid | error
    valid: Optional[bool] = None
    vat_number: Optional[str] = None
    country_code: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "valid": self.valid,
            "vat_number": self.vat_number,
            "country_code": self.country_code,
            "name": self.name,
            "address": self.address,
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


class VatValidationProvider(ABC):
    name: str = "base"

    @abstractmethod
    def validate(self, vat_number: str) -> VatValidationResult: ...


def _default_http_get(
    url: str, headers: Optional[dict[str, str]] = None
) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers=headers
        or {
            "User-Agent": "ChemClaw/0.1 (+vatcomply-vat; read-only)",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp is not None else b""
        return int(exc.code), raw


def normalize_vat_number(raw: str) -> str:
    """Strip spaces/punctuation and uppercase (e.g. 'de 811 111 125' → 'DE811111125')."""
    s = (raw or "").strip().upper()
    return re.sub(r"[^A-Z0-9]", "", s)


class VatComplyProvider(VatValidationProvider):
    """VATComply public VAT endpoint (no API key)."""

    name = PROVIDER_ID

    def __init__(self, *, http_get: Optional[HttpGet] = None) -> None:
        self._http_get = http_get or _default_http_get

    def _source(self, *, record_id: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
            "url": VATCOMPLY_DOCS_URL,
        }
        if record_id:
            out["record_id"] = record_id
        return out

    def validate(self, vat_number: str) -> VatValidationResult:
        normalized = normalize_vat_number(vat_number)
        if not normalized:
            return VatValidationResult(
                status="error",
                source=self._source(),
                warnings=[_LEGAL_WARNING],
                error="请提供欧盟 VAT 号（含国家代码，如 DE123456789）",
            )
        if not _VAT_RE.fullmatch(normalized):
            return VatValidationResult(
                status="error",
                vat_number=normalized,
                source=self._source(),
                warnings=[_LEGAL_WARNING],
                error="VAT 号格式无效；需为 2 位国家代码 + 2–12 位字母数字（如 DE811111125）",
            )

        qs = urllib.parse.urlencode({"vat_number": normalized})
        url = f"{VATCOMPLY_VAT_URL}?{qs}"
        try:
            code, raw = self._http_get(url, None)
        except Exception as exc:
            return VatValidationResult(
                status="error",
                vat_number=normalized,
                country_code=normalized[:2],
                source=self._source(record_id=normalized),
                warnings=[_LEGAL_WARNING],
                error=f"VATComply 请求失败：{exc}",
            )

        if code != 200:
            snippet = raw[:200].decode("utf-8", errors="replace") if raw else ""
            return VatValidationResult(
                status="error",
                vat_number=normalized,
                country_code=normalized[:2],
                source=self._source(record_id=normalized),
                warnings=[_LEGAL_WARNING],
                error=f"VATComply HTTP {code}" + (f"：{snippet}" if snippet else ""),
            )

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return VatValidationResult(
                status="error",
                vat_number=normalized,
                country_code=normalized[:2],
                source=self._source(record_id=normalized),
                warnings=[_LEGAL_WARNING],
                error=f"VATComply 响应不是合法 JSON：{exc}",
            )

        if not isinstance(payload, dict):
            return VatValidationResult(
                status="error",
                vat_number=normalized,
                country_code=normalized[:2],
                source=self._source(record_id=normalized),
                warnings=[_LEGAL_WARNING],
                error="VATComply 响应缺少对象主体",
            )

        is_valid = bool(payload.get("valid"))
        country = str(payload.get("country_code") or normalized[:2]).strip().upper() or None
        national = str(payload.get("vat_number") or "").strip()
        display_vat = f"{country}{national}" if country and national else normalized
        name = str(payload.get("name") or "").strip() or None
        address = str(payload.get("address") or "").strip() or None
        if name in ("---", "-"):
            name = None
        if address in ("---", "-"):
            address = None

        return VatValidationResult(
            status="valid" if is_valid else "invalid",
            valid=is_valid,
            vat_number=display_vat,
            country_code=country,
            name=name,
            address=address,
            source=self._source(record_id=display_vat),
            warnings=[_LEGAL_WARNING],
            error=None,
        )
