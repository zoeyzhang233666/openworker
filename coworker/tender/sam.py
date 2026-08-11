"""SAM.gov Opportunities API provider — subscription key via SecretStore.

API clients live here (platform Tool/Provider layer), not inside bundled Skills.
Maps notices to OpportunitySignal-shaped dicts for chem-opportunity-radar.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from .providers import TenderSearchResult

SAM_PROVIDER_ID = "sam"
SAM_PROVIDER_VERSION = "1.0.0"
SAM_SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"
SAM_UI_URL = "https://sam.gov/"
_TIMEOUT = 30.0
_MAX_LIMIT = 50

# (url, headers) -> (status_code, response_body)
HttpGet = Callable[..., tuple[int, bytes]]


def _default_http_get(
    url: str, headers: Optional[dict[str, str]] = None
) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers=headers
        or {
            "User-Agent": "ChemClaw/0.1 (+sam-tender; read-only)",
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


def _mmddyyyy(d: datetime) -> str:
    return d.strftime("%m/%d/%Y")


def _default_posted_range() -> tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=30)
    return (
        _mmddyyyy(datetime(start.year, start.month, start.day, tzinfo=timezone.utc)),
        _mmddyyyy(datetime(end.year, end.month, end.day, tzinfo=timezone.utc)),
    )


def _normalize_posted_date(raw: Any) -> Optional[str]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    # ISO-ish: YYYY-MM-DD…
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    # MM/dd/yyyy
    if len(s) >= 10 and s[2] == "/" and s[5] == "/":
        try:
            m, d, y = int(s[0:2]), int(s[3:5]), int(s[6:10])
            return f"{y:04d}-{m:02d}-{d:02d}"
        except ValueError:
            return None
    return None


class SamProvider:
    """SAM.gov Opportunities v2 search (api_key required)."""

    name = SAM_PROVIDER_ID

    def __init__(
        self,
        *,
        api_key: str = "",
        http_get: Optional[HttpGet] = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._http_get = http_get or _default_http_get

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        posted_from: str = "",
        posted_to: str = "",
        naics: str = "",
    ) -> TenderSearchResult:
        if not self._api_key:
            return TenderSearchResult(
                status="error",
                source=self._source(),
                error=(
                    "SAM.gov 数据源未配置（境外可选，非大陆刚需）。"
                    "可改用 EU TED（免密钥 search_tenders）或网页搜索。"
                    "若确需美国联邦标且能访问 sam.gov：在「连接 → API 公开查询」配置 "
                    "sam:default（api_key）。"
                ),
            )

        q = (query or "").strip()
        if not q:
            return TenderSearchResult(
                status="error",
                source=self._source(),
                error="查询不能为空；请提供关键词、品名或招标主题",
            )

        pf = (posted_from or "").strip()
        pt = (posted_to or "").strip()
        if not pf or not pt:
            pf, pt = _default_posted_range()

        lim = max(1, min(int(limit or 10), _MAX_LIMIT))
        params: dict[str, str] = {
            "api_key": self._api_key,
            "limit": str(lim),
            "offset": "0",
            "postedFrom": pf,
            "postedTo": pt,
            "title": q,
        }
        ncode = (naics or "").strip()
        if ncode:
            params["ncode"] = ncode

        url = f"{SAM_SEARCH_URL}?{urllib.parse.urlencode(params)}"
        headers = {
            "User-Agent": "ChemClaw/0.1 (+sam-tender; read-only)",
            "Accept": "application/json",
        }

        try:
            status_code, raw = self._http_get(url, headers)
        except Exception as exc:
            return TenderSearchResult(
                status="error",
                source=self._source(url),
                error=f"SAM 请求失败：{exc}",
            )

        if status_code >= 400:
            return TenderSearchResult(
                status="error",
                source=self._source(url),
                error=f"SAM HTTP {status_code}",
            )

        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            return TenderSearchResult(
                status="error",
                source=self._source(url),
                error=f"SAM 响应解析失败：{exc}",
            )

        if not isinstance(data, dict):
            return TenderSearchResult(
                status="error",
                source=self._source(url),
                error="SAM 响应格式无效",
            )

        rows = data.get("opportunitiesData")
        if rows is None:
            rows = data.get("opportunities") or data.get("data") or []
        if not isinstance(rows, list):
            return TenderSearchResult(
                status="error",
                source=self._source(url),
                error="SAM 响应缺少 opportunitiesData 数组",
            )

        collected = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        signals: list[dict[str, Any]] = []
        for row in rows[:lim]:
            if not isinstance(row, dict):
                continue
            sig = self._to_signal(row, collected_at=collected)
            if sig is not None:
                signals.append(sig)

        if not signals:
            return TenderSearchResult(
                status="empty",
                signals=[],
                source=self._source(url),
                warnings=["未找到匹配的 SAM.gov 公告"],
            )

        return TenderSearchResult(
            status="ok",
            signals=signals,
            source=self._source(url),
            warnings=[],
        )

    def _to_signal(
        self, row: dict[str, Any], *, collected_at: str
    ) -> Optional[dict[str, Any]]:
        notice = row.get("noticeId") or row.get("notice_id")
        if not isinstance(notice, str) or not notice.strip():
            # Refuse to invent SAM notice IDs
            return None
        notice = notice.strip()
        title = row.get("title")
        if not isinstance(title, str) or not title.strip():
            title = notice
        else:
            title = title.strip()
        agency = row.get("fullParentPathName") or row.get("organizationName")
        if isinstance(agency, str):
            agency = agency.strip() or None
        else:
            agency = None
        event_date = _normalize_posted_date(row.get("postedDate") or row.get("posted_date"))
        ui = row.get("uiLink") or row.get("ui_link")
        if isinstance(ui, str) and ui.startswith("http"):
            url = ui.strip()
        else:
            url = f"https://sam.gov/opp/{urllib.parse.quote(notice)}/view"
        summary_parts = [title]
        if agency:
            summary_parts.append(f"agency={agency}")
        sol = row.get("solicitationNumber")
        if isinstance(sol, str) and sol.strip():
            summary_parts.append(f"sol={sol.strip()}")
        return {
            "signal_id": f"sam:{notice}",
            "signal_type": "tender",
            "summary": "; ".join(summary_parts),
            "event_date": event_date,
            "collected_at": collected_at,
            "buyer_hint": agency,
            "buyer_country": "USA",
            "source": {
                "provider_id": SAM_PROVIDER_ID,
                "provider_version": SAM_PROVIDER_VERSION,
                "type": "government_registry",
                "locator": f"sam:{notice}",
                "url": url,
                "record_id": notice,
            },
        }

    @staticmethod
    def _source(endpoint: Optional[str] = None) -> dict[str, Any]:
        return {
            "provider_id": SAM_PROVIDER_ID,
            "provider_version": SAM_PROVIDER_VERSION,
            "endpoint": endpoint or SAM_SEARCH_URL,
            "url": SAM_UI_URL,
        }
