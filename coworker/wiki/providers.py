"""Wikipedia / MediaWiki extracts — keyless, read-only encyclopedia assist.

Background only; never sole evidence for Qualified / Actionable / purchase intent.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

PROVIDER_ID = "wikipedia"
PROVIDER_VERSION = "1.0.0"
_TIMEOUT = 30.0
_ALLOWED_LANG = frozenset({"zh", "en"})
_EVIDENCE_WARNING = (
    "百科摘要仅为背景知识，不得单独支撑 Qualified / Actionable 或采购意图。"
)

HttpGet = Callable[..., tuple[int, bytes]]


@dataclass
class WikipediaResult:
    status: str  # ok | not_found | error
    title: Optional[str] = None
    lang: Optional[str] = None
    extract: Optional[str] = None
    page_url: Optional[str] = None
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "title": self.title,
            "lang": self.lang,
            "extract": self.extract,
            "page_url": self.page_url,
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


class WikipediaProvider(ABC):
    name: str = "base"

    @abstractmethod
    def lookup(self, title: str, *, lang: str = "zh") -> WikipediaResult: ...


def _default_http_get(
    url: str, headers: Optional[dict[str, str]] = None
) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers=headers
        or {
            "User-Agent": "ChemClaw/0.1 (+wikipedia-wiki; read-only)",
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


class MediaWikiWikipediaProvider(WikipediaProvider):
    name = PROVIDER_ID

    def __init__(self, *, http_get: Optional[HttpGet] = None) -> None:
        self._http_get = http_get or _default_http_get

    def _api_base(self, lang: str) -> str:
        return f"https://{lang}.wikipedia.org/w/api.php"

    def _source(self, *, page_url: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
            "url": page_url or "https://www.mediawiki.org/wiki/API:Main_page",
        }
        return out

    def lookup(self, title: str, *, lang: str = "zh") -> WikipediaResult:
        t = (title or "").strip()
        lang_norm = (lang or "zh").strip().lower() or "zh"
        if not t:
            return WikipediaResult(
                status="error",
                source=self._source(),
                warnings=[_EVIDENCE_WARNING],
                error="请提供百科条目标题（品名或常见别名）",
            )
        if lang_norm not in _ALLOWED_LANG:
            return WikipediaResult(
                status="error",
                title=t,
                lang=lang_norm,
                source=self._source(),
                warnings=[_EVIDENCE_WARNING],
                error="lang 仅支持 zh 或 en",
            )

        qs = urllib.parse.urlencode(
            {
                "action": "query",
                "format": "json",
                "prop": "extracts|info",
                "exintro": "1",
                "explaintext": "1",
                "redirects": "1",
                "inprop": "url",
                "titles": t,
            }
        )
        url = f"{self._api_base(lang_norm)}?{qs}"
        try:
            code, raw = self._http_get(url, None)
        except Exception as exc:
            return WikipediaResult(
                status="error",
                title=t,
                lang=lang_norm,
                source=self._source(),
                warnings=[_EVIDENCE_WARNING],
                error=f"Wikipedia 请求失败：{exc}",
            )

        if code != 200:
            snippet = raw[:200].decode("utf-8", errors="replace") if raw else ""
            return WikipediaResult(
                status="error",
                title=t,
                lang=lang_norm,
                source=self._source(),
                warnings=[_EVIDENCE_WARNING],
                error=f"Wikipedia HTTP {code}" + (f"：{snippet}" if snippet else ""),
            )

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return WikipediaResult(
                status="error",
                title=t,
                lang=lang_norm,
                source=self._source(),
                warnings=[_EVIDENCE_WARNING],
                error=f"Wikipedia 响应不是合法 JSON：{exc}",
            )

        pages = (
            (payload.get("query") or {}).get("pages")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(pages, dict) or not pages:
            return WikipediaResult(
                status="error",
                title=t,
                lang=lang_norm,
                source=self._source(),
                warnings=[_EVIDENCE_WARNING],
                error="Wikipedia 响应缺少 pages",
            )

        page = next(iter(pages.values()))
        if not isinstance(page, dict):
            return WikipediaResult(
                status="error",
                title=t,
                lang=lang_norm,
                source=self._source(),
                warnings=[_EVIDENCE_WARNING],
                error="Wikipedia 页面对象无效",
            )

        if page.get("missing") is not None or int(page.get("pageid") or 0) < 0:
            return WikipediaResult(
                status="not_found",
                title=t,
                lang=lang_norm,
                source=self._source(),
                warnings=[_EVIDENCE_WARNING],
            )

        resolved_title = str(page.get("title") or t).strip()
        extract = str(page.get("extract") or "").strip() or None
        page_url = str(page.get("fullurl") or "").strip()
        if not page_url:
            page_url = (
                f"https://{lang_norm}.wikipedia.org/wiki/"
                + urllib.parse.quote(resolved_title.replace(" ", "_"))
            )

        if not extract:
            return WikipediaResult(
                status="not_found",
                title=resolved_title,
                lang=lang_norm,
                page_url=page_url,
                source=self._source(page_url=page_url),
                warnings=[_EVIDENCE_WARNING],
                error="条目无可用摘要",
            )

        # Cap extract for tool payload size
        if len(extract) > 4000:
            extract = extract[:4000] + "…"

        return WikipediaResult(
            status="ok",
            title=resolved_title,
            lang=lang_norm,
            extract=extract,
            page_url=page_url,
            source=self._source(page_url=page_url),
            warnings=[_EVIDENCE_WARNING],
        )
