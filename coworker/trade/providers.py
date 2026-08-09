"""UN Comtrade trade-flow provider — subscription key via SecretStore.

API clients live here (platform Tool/Provider layer), not inside bundled Skills.
Returns country/HS aggregates for market attractiveness — never buyer company lists.
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

PROVIDER_ID = "comtrade"
PROVIDER_VERSION = "1.0.0"
COMTRADE_DATA_URL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
COMTRADE_UI_URL = "https://comtradeplus.un.org/TradeFlow"
_TIMEOUT = 30.0
_MAX_LIMIT = 100
_HS_RE = re.compile(r"^\d{2,10}$")
_BUYER_WARNING = (
    "贸易流为国家/HS 汇总指标，不是企业买家名单；不得据此编造进口商或成交客户。"
)

# Common ISO 3166-1 alpha-3 → UN M49 / Comtrade reporter codes (subset for first pack).
_ISO3_TO_CODE: dict[str, int] = {
    "AUS": 36,
    "BEL": 56,
    "BRA": 76,
    "CAN": 124,
    "CHE": 756,
    "CHN": 156,
    "DEU": 276,
    "ESP": 724,
    "FRA": 251,
    "GBR": 826,
    "IDN": 360,
    "IND": 356,
    "ITA": 380,
    "JPN": 392,
    "KOR": 410,
    "MEX": 484,
    "MYS": 458,
    "NLD": 528,
    "POL": 616,
    "RUS": 643,
    "SGP": 702,
    "THA": 764,
    "TUR": 792,
    "USA": 842,
    "VNM": 704,
    "WLD": 0,
}

# (url, headers) -> (status_code, response_body)
HttpGet = Callable[..., tuple[int, bytes]]


@dataclass
class TradeFlowResult:
    status: str  # ok | empty | error
    flows: list[dict[str, Any]] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "flows": list(self.flows),
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


class TradeFlowProvider(ABC):
    name: str = "base"

    @abstractmethod
    def lookup(
        self,
        *,
        hs_code: str,
        reporter: str,
        period: str = "",
        flow: str = "M",
        partner: str = "0",
        limit: int = 20,
    ) -> TradeFlowResult: ...


def _default_http_get(
    url: str, headers: Optional[dict[str, str]] = None
) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers=headers
        or {
            "User-Agent": "ChemClaw/0.1 (+comtrade-trade; read-only)",
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


def resolve_area_code(value: str) -> tuple[Optional[int], Optional[str]]:
    """Return (numeric_code, error_zh). Accepts digits or known ISO3."""
    raw = (value or "").strip()
    if not raw:
        return None, "报告国/伙伴不能为空；请提供 ISO3（如 USA）或 Comtrade 数字代码"
    if raw.isdigit():
        return int(raw), None
    iso = raw.upper()
    if iso in _ISO3_TO_CODE:
        return _ISO3_TO_CODE[iso], None
    return None, (
        f"无法识别地区代码「{raw}」；请使用 ISO3（如 USA、CHN、DEU）"
        "或 Comtrade 数字代码（如 842）"
    )


class ComtradeProvider(TradeFlowProvider):
    """UN Comtrade final-data API (subscription key required)."""

    name = PROVIDER_ID

    def __init__(
        self,
        *,
        api_key: str = "",
        http_get: Optional[HttpGet] = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._http_get = http_get or _default_http_get

    def lookup(
        self,
        *,
        hs_code: str,
        reporter: str,
        period: str = "",
        flow: str = "M",
        partner: str = "0",
        limit: int = 20,
    ) -> TradeFlowResult:
        if not self._api_key:
            return TradeFlowResult(
                status="error",
                source=self._source(),
                warnings=[_BUYER_WARNING],
                error=(
                    "UN Comtrade 数据源未配置。请在凭据中设置 comtrade:default "
                    "（api_key 为订阅密钥），详见 comtradeplus.un.org / 开发者门户。"
                ),
            )

        cmd = (hs_code or "").strip()
        if not _HS_RE.fullmatch(cmd):
            return TradeFlowResult(
                status="error",
                source=self._source(),
                warnings=[_BUYER_WARNING],
                error="HS 编码无效；请提供 2–10 位数字（如 291631）",
            )

        reporter_code, rep_err = resolve_area_code(reporter)
        if rep_err is not None:
            return TradeFlowResult(
                status="error",
                source=self._source(),
                warnings=[_BUYER_WARNING],
                error=rep_err,
            )

        partner_raw = (partner or "0").strip() or "0"
        partner_code, part_err = resolve_area_code(partner_raw)
        if part_err is not None:
            return TradeFlowResult(
                status="error",
                source=self._source(),
                warnings=[_BUYER_WARNING],
                error=part_err,
            )

        flow_code = (flow or "M").strip().upper() or "M"
        if flow_code not in {"M", "X", "RX", "RM", "MIP", "XIP"}:
            # Still allow other official codes; only reject obvious junk.
            if not re.fullmatch(r"[A-Z]{1,5}", flow_code):
                return TradeFlowResult(
                    status="error",
                    source=self._source(),
                    warnings=[_BUYER_WARNING],
                    error="贸易流向无效；常用 M=进口、X=出口",
                )

        per = (period or "").strip()
        if not per:
            from datetime import datetime, timezone

            per = str(datetime.now(timezone.utc).year - 1)
        if not re.fullmatch(r"\d{4}", per):
            return TradeFlowResult(
                status="error",
                source=self._source(),
                warnings=[_BUYER_WARNING],
                error="统计期无效；请提供四位年份（如 2022）",
            )

        lim = max(1, min(int(limit or 20), _MAX_LIMIT))
        params = {
            "reporterCode": str(reporter_code),
            "period": per,
            "cmdCode": cmd,
            "flowCode": flow_code,
            "partnerCode": str(partner_code),
            "maxRecords": str(lim),
            "format": "JSON",
            "includeDesc": "true",
        }
        url = f"{COMTRADE_DATA_URL}?{urllib.parse.urlencode(params)}"
        headers = {
            "User-Agent": "ChemClaw/0.1 (+comtrade-trade; read-only)",
            "Accept": "application/json",
            "Ocp-Apim-Subscription-Key": self._api_key,
        }

        try:
            status_code, raw = self._http_get(url, headers)
        except Exception as exc:
            return TradeFlowResult(
                status="error",
                source=self._source(url),
                warnings=[_BUYER_WARNING],
                error=f"Comtrade 请求失败：{exc}",
            )

        if status_code >= 400:
            return TradeFlowResult(
                status="error",
                source=self._source(url),
                warnings=[_BUYER_WARNING],
                error=f"Comtrade HTTP {status_code}",
            )

        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            return TradeFlowResult(
                status="error",
                source=self._source(url),
                warnings=[_BUYER_WARNING],
                error=f"Comtrade 响应解析失败：{exc}",
            )

        if not isinstance(data, dict):
            return TradeFlowResult(
                status="error",
                source=self._source(url),
                warnings=[_BUYER_WARNING],
                error="Comtrade 响应格式无效",
            )

        api_err = data.get("error")
        if isinstance(api_err, str) and api_err.strip():
            return TradeFlowResult(
                status="error",
                source=self._source(url),
                warnings=[_BUYER_WARNING],
                error=f"Comtrade：{api_err.strip()}",
            )

        rows = data.get("data")
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            return TradeFlowResult(
                status="error",
                source=self._source(url),
                warnings=[_BUYER_WARNING],
                error="Comtrade 响应缺少 data 数组",
            )

        flows: list[dict[str, Any]] = []
        for row in rows[:lim]:
            if isinstance(row, dict):
                flows.append(self._normalize_row(row))

        if not flows:
            return TradeFlowResult(
                status="empty",
                flows=[],
                source=self._source(url),
                warnings=[_BUYER_WARNING, "未找到匹配的贸易流记录"],
            )

        return TradeFlowResult(
            status="ok",
            flows=flows,
            source=self._source(url),
            warnings=[_BUYER_WARNING],
        )

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        primary = row.get("primaryValue")
        if primary is None:
            primary = row.get("cifvalue") if row.get("cifvalue") is not None else row.get(
                "fobvalue"
            )
        net = row.get("netWgt")
        if net is None:
            alt = row.get("altQty")
            if row.get("altQtyUnitAbbr") == "kg":
                net = alt
        return {
            "hs_code": str(row.get("cmdCode") or "").strip(),
            "hs_description": (row.get("cmdDesc") or None),
            "reporter_iso": (row.get("reporterISO") or None),
            "reporter_code": row.get("reporterCode"),
            "partner_iso": (row.get("partnerISO") or None),
            "partner_code": row.get("partnerCode"),
            "flow_code": (row.get("flowCode") or None),
            "period": str(row.get("period") or "").strip() or None,
            "primary_value_usd": primary,
            "cif_value_usd": row.get("cifvalue"),
            "fob_value_usd": row.get("fobvalue"),
            "net_weight_kg": net,
            "qty": row.get("qty"),
            "qty_unit": row.get("qtyUnitAbbr"),
        }

    @staticmethod
    def _source(endpoint: Optional[str] = None) -> dict[str, Any]:
        return {
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
            "endpoint": endpoint or COMTRADE_DATA_URL,
            "url": COMTRADE_UI_URL,
        }
