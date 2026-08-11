"""FX rates via Frankfurter — keyless, read-only.

Does not invent unit prices; only converts amounts the user already provided.
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

PROVIDER_ID = "frankfurter"
PROVIDER_VERSION = "1.0.0"
FRANKFURTER_LATEST_URL = "https://api.frankfurter.app/latest"
FRANKFURTER_DOCS_URL = "https://www.frankfurter.app/docs"
_TIMEOUT = 30.0
_CCY_RE = re.compile(r"^[A-Z]{3}$")
_PRICE_WARNING = (
    "汇率换算不得编造单价或数量；仅转换用户已给出的金额。"
)

HttpGet = Callable[..., tuple[int, bytes]]


@dataclass
class FxRateResult:
    status: str  # ok | error
    base: Optional[str] = None
    quote: Optional[str] = None
    rate: Optional[float] = None
    amount: Optional[float] = None
    converted: Optional[float] = None
    as_of: Optional[str] = None
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "base": self.base,
            "quote": self.quote,
            "rate": self.rate,
            "amount": self.amount,
            "converted": self.converted,
            "as_of": self.as_of,
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


class FxRateProvider(ABC):
    name: str = "base"

    @abstractmethod
    def lookup(
        self,
        *,
        base: str,
        quote: str,
        amount: Optional[float] = None,
    ) -> FxRateResult: ...


def _default_http_get(
    url: str, headers: Optional[dict[str, str]] = None
) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers=headers
        or {
            "User-Agent": "ChemClaw/0.1 (+frankfurter-fx; read-only)",
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


class FrankfurterProvider(FxRateProvider):
    name = PROVIDER_ID

    def __init__(self, *, http_get: Optional[HttpGet] = None) -> None:
        self._http_get = http_get or _default_http_get

    def _source(self) -> dict[str, Any]:
        return {
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
            "url": FRANKFURTER_DOCS_URL,
        }

    def lookup(
        self,
        *,
        base: str,
        quote: str,
        amount: Optional[float] = None,
    ) -> FxRateResult:
        b = (base or "").strip().upper()
        q = (quote or "").strip().upper()
        if not _CCY_RE.fullmatch(b) or not _CCY_RE.fullmatch(q):
            return FxRateResult(
                status="error",
                source=self._source(),
                warnings=[_PRICE_WARNING],
                error="币种须为 3 位 ISO 代码（如 USD、CNY、EUR）",
            )
        if b == q:
            amt = float(amount) if amount is not None else 1.0
            return FxRateResult(
                status="ok",
                base=b,
                quote=q,
                rate=1.0,
                amount=amt,
                converted=amt,
                as_of=None,
                source=self._source(),
                warnings=[_PRICE_WARNING],
            )

        amt_f: Optional[float] = None
        if amount is not None:
            try:
                amt_f = float(amount)
            except (TypeError, ValueError):
                return FxRateResult(
                    status="error",
                    base=b,
                    quote=q,
                    source=self._source(),
                    warnings=[_PRICE_WARNING],
                    error="amount 必须是数字",
                )
            if amt_f < 0:
                return FxRateResult(
                    status="error",
                    base=b,
                    quote=q,
                    source=self._source(),
                    warnings=[_PRICE_WARNING],
                    error="amount 不能为负数",
                )

        # Always fetch unit rate (amount=1); convert locally so `rate` stays 1-base units.
        params = {"from": b, "to": q}
        url = f"{FRANKFURTER_LATEST_URL}?{urllib.parse.urlencode(params)}"
        try:
            code, raw = self._http_get(url, None)
        except Exception as exc:
            return FxRateResult(
                status="error",
                base=b,
                quote=q,
                source=self._source(),
                warnings=[_PRICE_WARNING],
                error=f"Frankfurter 请求失败：{exc}",
            )

        if code != 200:
            snippet = raw[:200].decode("utf-8", errors="replace") if raw else ""
            return FxRateResult(
                status="error",
                base=b,
                quote=q,
                source=self._source(),
                warnings=[_PRICE_WARNING],
                error=f"Frankfurter HTTP {code}" + (f"：{snippet}" if snippet else ""),
            )

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return FxRateResult(
                status="error",
                base=b,
                quote=q,
                source=self._source(),
                warnings=[_PRICE_WARNING],
                error=f"Frankfurter 响应不是合法 JSON：{exc}",
            )

        if not isinstance(payload, dict):
            return FxRateResult(
                status="error",
                base=b,
                quote=q,
                source=self._source(),
                warnings=[_PRICE_WARNING],
                error="Frankfurter 响应格式无效",
            )

        rates = payload.get("rates")
        if not isinstance(rates, dict) or q not in rates:
            return FxRateResult(
                status="error",
                base=b,
                quote=q,
                source=self._source(),
                warnings=[_PRICE_WARNING],
                error=f"Frankfurter 未返回 {q} 汇率",
            )

        try:
            rate = float(rates[q])
        except (TypeError, ValueError):
            return FxRateResult(
                status="error",
                base=b,
                quote=q,
                source=self._source(),
                warnings=[_PRICE_WARNING],
                error="Frankfurter 汇率字段无法解析为数字",
            )

        as_of = str(payload.get("date") or "").strip() or None
        converted = (amt_f * rate) if amt_f is not None else None
        return FxRateResult(
            status="ok",
            base=str(payload.get("base") or b).upper(),
            quote=q,
            rate=rate,
            amount=amt_f,
            converted=converted,
            as_of=as_of,
            source=self._source(),
            warnings=[_PRICE_WARNING],
        )
