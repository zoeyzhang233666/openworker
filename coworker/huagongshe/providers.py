"""Huagongshe (化工社) chemistry search + optional reaction write.

API clients live here (platform Tool/Provider layer), not inside bundled Skills.
Reaction data must never feed Lead Fit scoring.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

PROVIDER_ID = "huagongshe"
PROVIDER_VERSION = "1.2.0"
API_BASE = "https://huagongshe.com/api"
DOCS_URL = "https://huagongshe.com/api/agent-guide"
GUIDE_URL = "https://huagongshe.com/guide"
_TIMEOUT = 30.0
_MAX_PAGE_SIZE = 50
_LEAD_WARNING = (
    "化工社结果仅为化学证据补充，不参与客户搜索与 Lead 评分；不得据此编造买家或商机。"
)
_WRITE_WARNING = (
    "校验不会保存；只有 create 会写入反应库。未获成功响应不得声称已保存。"
)
_TOKEN_REQUIRED = (
    "化工社写操作未配置 Token。请在「连接 → API 公开查询」配置 huagongshe:default（API Token）。"
)

HttpGet = Callable[..., tuple[int, bytes]]
# (url, body, headers) -> (status_code, response_body)
HttpPost = Callable[..., tuple[int, bytes]]


@dataclass
class HuagongsheSearchResult:
    status: str  # ok | empty | error
    query: str = ""
    mode: str = "exact"
    total: int = 0
    chemicals: list[dict[str, Any]] = field(default_factory=list)
    reactions: list[dict[str, Any]] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "query": self.query,
            "mode": self.mode,
            "total": self.total,
            "chemicals": list(self.chemicals),
            "reactions": list(self.reactions),
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


@dataclass
class HuagongsheChemicalResult:
    status: str  # ok | not_found | error
    chemical: Optional[dict[str, Any]] = None
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "chemical": dict(self.chemical) if self.chemical else None,
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


@dataclass
class HuagongsheValidateResult:
    status: str  # ok | invalid | error
    normalized: Optional[dict[str, Any]] = None
    detail: Optional[Any] = None
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "normalized": (
                dict(self.normalized) if isinstance(self.normalized, dict) else self.normalized
            ),
            "detail": self.detail,
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


@dataclass
class HuagongsheCreateResult:
    status: str  # ok | error
    hrid: Optional[Any] = None
    page_url: Optional[str] = None
    visibility: Optional[str] = None
    created_chemical_ids: list[Any] = field(default_factory=list)
    idempotency_key: Optional[str] = None
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "hrid": self.hrid,
            "page_url": self.page_url,
            "visibility": self.visibility,
            "created_chemical_ids": list(self.created_chemical_ids),
            "idempotency_key": self.idempotency_key,
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


@dataclass
class HuagongsheSvgResult:
    """SVG fetch — `content` is for callers that write files; never in to_dict()."""

    status: str  # ok | not_found | error
    kind: Optional[str] = None
    entity_id: Optional[str] = None
    public_url: Optional[str] = None
    bytes_len: int = 0
    content: Optional[bytes] = field(default=None, repr=False)
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "kind": self.kind,
            "entity_id": self.entity_id,
            "public_url": self.public_url,
            "bytes": self.bytes_len,
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


class HuagongsheProvider(ABC):
    name: str = "base"

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        mode: str = "exact",
        page: int = 1,
        page_size: int = 10,
    ) -> HuagongsheSearchResult: ...

    @abstractmethod
    def get_chemical(self, chemical_id: str) -> HuagongsheChemicalResult: ...


_SVG_DIR = "huagongshe_assets"
_SVG_MIN_DIM = 50
_SVG_MAX_DIM = 2000
_SVG_DEFAULT_W = 400
_SVG_DEFAULT_H = 300


def _clamp_svg_dim(value: Any, default: int) -> tuple[Optional[int], Optional[str]]:
    if value is None or value == "":
        return default, None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None, "width / height 必须是正整数"
    if n < _SVG_MIN_DIM or n > _SVG_MAX_DIM:
        return None, f"width / height 须在 {_SVG_MIN_DIM}–{_SVG_MAX_DIM} 之间"
    return n, None


def svg_artifact_relpath(kind: str, entity_id: str, width: int, height: int) -> str:
    prefix = "mol" if kind == "chemical" else "rxn"
    return f"{_SVG_DIR}/{prefix}-{entity_id}-{width}x{height}.svg"


def svg_public_url(kind: str, entity_id: str, width: int, height: int) -> str:
    if kind == "chemical":
        return f"{API_BASE}/mol/{urllib.parse.quote(entity_id)}/svg/{width}x{height}.svg"
    return (
        f"{API_BASE}/reactions/{urllib.parse.quote(entity_id)}/svg/{width}x{height}.svg"
    )


def _default_http_get(
    url: str, headers: Optional[dict[str, str]] = None
) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers=headers
        or {
            "User-Agent": "ChemClaw/0.1 (+huagongshe; read-only)",
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


def _default_http_post(
    url: str, body: bytes, headers: Optional[dict[str, str]] = None
) -> tuple[int, bytes]:
    hdrs = {
        "User-Agent": "ChemClaw/0.1 (+huagongshe; write)",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp is not None else b""
        return int(exc.code), raw


def _slim_chemical(row: dict[str, Any]) -> dict[str, Any]:
    cas = row.get("cas_numbers")
    if not isinstance(cas, list):
        cas = []
    return {
        "hcid": row.get("id"),
        "pubchem_cid": row.get("pubchem_cid"),
        "preferred_name": row.get("preferred_name"),
        "iupac_name": row.get("iupac_name"),
        "molecular_formula": row.get("molecular_formula"),
        "smiles": row.get("smiles") or row.get("pubchem_smiles"),
        "inchikey": row.get("inchikey"),
        "cas_numbers": [str(c) for c in cas if c],
        "page_url": (
            f"https://huagongshe.com/chemical/{row.get('id')}"
            if row.get("id") is not None
            else None
        ),
    }


def _slim_reaction(row: dict[str, Any]) -> dict[str, Any]:
    rid = row.get("id")
    return {
        "hrid": rid,
        "summary": row.get("summary") or row.get("title") or row.get("reaction_smiles"),
        "page_url": f"https://huagongshe.com/reaction/{rid}" if rid is not None else None,
    }


def _parse_reaction_payload(raw: Any) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    if isinstance(raw, dict):
        return raw, None
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None, "请提供反应草稿 JSON（reaction_json）"
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            return None, f"reaction_json 不是合法 JSON：{exc}"
        if not isinstance(parsed, dict):
            return None, "reaction_json 必须是 JSON 对象"
        return parsed, None
    return None, "reaction_json 必须是对象或 JSON 字符串"


class HuagongsheHttpProvider(HuagongsheProvider):
    """Client for huagongshe.com (optional Bearer; required for write)."""

    name = PROVIDER_ID

    def __init__(
        self,
        *,
        api_key: str = "",
        http_get: Optional[HttpGet] = None,
        http_post: Optional[HttpPost] = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._http_get = http_get or _default_http_get
        self._http_post = http_post or _default_http_post

    def _headers(self, *, write: bool = False, accept: str = "application/json") -> dict[str, str]:
        headers = {
            "User-Agent": "ChemClaw/0.1 (+huagongshe; "
            + ("write)" if write else "read-only)"),
            "Accept": accept,
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _source(self, *, record_id: str = "", url: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
            "url": url or DOCS_URL,
            "has_api_key": bool(self._api_key),
        }
        if record_id:
            out["record_id"] = record_id
        return out

    def _http_error(self, code: int, raw: bytes, *, write: bool = False) -> str:
        if code == 401:
            return (
                "化工社 Token 无效或已撤销；请在「连接 → API 公开查询」更新密钥"
                + ("。" if write else "，或清空后使用公开检索。")
            )
        if code == 403:
            return (
                "化工社拒绝访问（权限不足）；"
                + (
                    "写反应请确认 Token 含 reaction:write 范围。"
                    if write
                    else "只读检索请确认 Token 含 read 范围。"
                )
            )
        if code == 409:
            return "化工社冲突（409）；请检查重复参与物或 Idempotency-Key 是否被其他草稿占用。"
        if code in (400, 422):
            snippet = raw[:400].decode("utf-8", errors="replace") if raw else ""
            return "化工社校验失败，请按 detail 修正字段或结构后重试" + (
                f"：{snippet}" if snippet else "。"
            )
        if code == 429:
            return "化工社请求过于频繁（429）；请稍后重试。"
        snippet = raw[:200].decode("utf-8", errors="replace") if raw else ""
        return f"化工社 HTTP {code}" + (f"：{snippet}" if snippet else "")

    def search(
        self,
        query: str,
        *,
        mode: str = "exact",
        page: int = 1,
        page_size: int = 10,
    ) -> HuagongsheSearchResult:
        q = (query or "").strip()
        if not q:
            return HuagongsheSearchResult(
                status="error",
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error="请提供检索词（名称、CAS、SMILES、DOI 等）",
            )
        mode_norm = (mode or "exact").strip().lower() or "exact"
        if mode_norm not in ("exact", "substructure", "similarity"):
            return HuagongsheSearchResult(
                status="error",
                query=q,
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error="mode 仅支持 exact / substructure / similarity",
            )
        try:
            page_i = max(1, int(page))
            size_i = max(1, min(int(page_size), _MAX_PAGE_SIZE))
        except (TypeError, ValueError):
            return HuagongsheSearchResult(
                status="error",
                query=q,
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error="page / page_size 必须是正整数",
            )

        qs = urllib.parse.urlencode(
            {
                "q": q,
                "mode": mode_norm,
                "page": str(page_i),
                "page_size": str(size_i),
            }
        )
        url = f"{API_BASE}/search?{qs}"
        try:
            code, raw = self._http_get(url, self._headers())
        except Exception as exc:
            return HuagongsheSearchResult(
                status="error",
                query=q,
                mode=mode_norm,
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error=f"化工社请求失败：{exc}",
            )

        if code != 200:
            return HuagongsheSearchResult(
                status="error",
                query=q,
                mode=mode_norm,
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error=self._http_error(code, raw),
            )

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return HuagongsheSearchResult(
                status="error",
                query=q,
                mode=mode_norm,
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error=f"化工社响应不是合法 JSON：{exc}",
            )

        if not isinstance(payload, dict):
            return HuagongsheSearchResult(
                status="error",
                query=q,
                mode=mode_norm,
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error="化工社响应格式无效",
            )

        chemicals_raw = payload.get("chemicals")
        reactions_raw = payload.get("reactions")
        chemicals = (
            [_slim_chemical(c) for c in chemicals_raw if isinstance(c, dict)]
            if isinstance(chemicals_raw, list)
            else []
        )
        reactions = (
            [_slim_reaction(r) for r in reactions_raw if isinstance(r, dict)]
            if isinstance(reactions_raw, list)
            else []
        )
        try:
            total = int(payload.get("total") or (len(chemicals) + len(reactions)))
        except (TypeError, ValueError):
            total = len(chemicals) + len(reactions)

        if not chemicals and not reactions:
            return HuagongsheSearchResult(
                status="empty",
                query=q,
                mode=str(payload.get("mode") or mode_norm),
                total=total,
                source=self._source(url=f"{GUIDE_URL}"),
                warnings=[_LEAD_WARNING],
            )

        return HuagongsheSearchResult(
            status="ok",
            query=q,
            mode=str(payload.get("mode") or mode_norm),
            total=total,
            chemicals=chemicals,
            reactions=reactions,
            source=self._source(url=DOCS_URL),
            warnings=[_LEAD_WARNING],
        )

    def get_chemical(self, chemical_id: str) -> HuagongsheChemicalResult:
        cid = str(chemical_id or "").strip()
        if not cid:
            return HuagongsheChemicalResult(
                status="error",
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error="请提供化工社化合物 HCID",
            )
        if not cid.isdigit():
            return HuagongsheChemicalResult(
                status="error",
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error="HCID 须为数字",
            )

        url = f"{API_BASE}/chemicals/{urllib.parse.quote(cid)}"
        try:
            code, raw = self._http_get(url, self._headers())
        except Exception as exc:
            return HuagongsheChemicalResult(
                status="error",
                source=self._source(record_id=cid),
                warnings=[_LEAD_WARNING],
                error=f"化工社请求失败：{exc}",
            )

        if code == 404:
            return HuagongsheChemicalResult(
                status="not_found",
                source=self._source(record_id=cid),
                warnings=[_LEAD_WARNING],
            )
        if code != 200:
            return HuagongsheChemicalResult(
                status="error",
                source=self._source(record_id=cid),
                warnings=[_LEAD_WARNING],
                error=self._http_error(code, raw),
            )

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return HuagongsheChemicalResult(
                status="error",
                source=self._source(record_id=cid),
                warnings=[_LEAD_WARNING],
                error=f"化工社响应不是合法 JSON：{exc}",
            )

        if not isinstance(payload, dict) or payload.get("id") is None:
            return HuagongsheChemicalResult(
                status="error",
                source=self._source(record_id=cid),
                warnings=[_LEAD_WARNING],
                error="化工社化合物响应缺少 id",
            )

        slim = _slim_chemical(payload)
        syn = payload.get("synonyms")
        if isinstance(syn, list):
            slim["synonyms"] = [str(s) for s in syn[:20] if s]
        reaction_count = payload.get("reaction_count")
        if reaction_count is not None:
            slim["reaction_count"] = reaction_count

        return HuagongsheChemicalResult(
            status="ok",
            chemical=slim,
            source=self._source(
                record_id=str(payload.get("id")),
                url=slim.get("page_url") or DOCS_URL,
            ),
            warnings=[_LEAD_WARNING],
        )

    def fetch_svg(
        self,
        *,
        kind: str,
        entity_id: str,
        width: int = _SVG_DEFAULT_W,
        height: int = _SVG_DEFAULT_H,
    ) -> HuagongsheSvgResult:
        kind_norm = (kind or "").strip().lower()
        if kind_norm not in ("chemical", "reaction"):
            return HuagongsheSvgResult(
                status="error",
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error="kind 须为 chemical 或 reaction",
            )
        eid = str(entity_id or "").strip()
        if not eid:
            return HuagongsheSvgResult(
                status="error",
                kind=kind_norm,
                source=self._source(),
                warnings=[_LEAD_WARNING],
                error="请提供化合物 HCID 或反应 HRID",
            )
        if not eid.isdigit():
            return HuagongsheSvgResult(
                status="error",
                kind=kind_norm,
                entity_id=eid,
                source=self._source(record_id=eid),
                warnings=[_LEAD_WARNING],
                error="id 须为数字",
            )
        w, w_err = _clamp_svg_dim(width, _SVG_DEFAULT_W)
        if w_err or w is None:
            return HuagongsheSvgResult(
                status="error",
                kind=kind_norm,
                entity_id=eid,
                source=self._source(record_id=eid),
                warnings=[_LEAD_WARNING],
                error=w_err or "width 无效",
            )
        h, h_err = _clamp_svg_dim(height, _SVG_DEFAULT_H)
        if h_err or h is None:
            return HuagongsheSvgResult(
                status="error",
                kind=kind_norm,
                entity_id=eid,
                source=self._source(record_id=eid),
                warnings=[_LEAD_WARNING],
                error=h_err or "height 无效",
            )

        url = svg_public_url(kind_norm, eid, w, h)
        try:
            code, raw = self._http_get(
                url, self._headers(accept="image/svg+xml,application/json;q=0.9,*/*;q=0.8")
            )
        except Exception as exc:
            return HuagongsheSvgResult(
                status="error",
                kind=kind_norm,
                entity_id=eid,
                public_url=url,
                source=self._source(record_id=eid, url=url),
                warnings=[_LEAD_WARNING],
                error=f"化工社 SVG 请求失败：{exc}",
            )

        if code == 404:
            return HuagongsheSvgResult(
                status="not_found",
                kind=kind_norm,
                entity_id=eid,
                public_url=url,
                source=self._source(record_id=eid, url=url),
                warnings=[_LEAD_WARNING],
            )
        if code != 200:
            return HuagongsheSvgResult(
                status="error",
                kind=kind_norm,
                entity_id=eid,
                public_url=url,
                source=self._source(record_id=eid, url=url),
                warnings=[_LEAD_WARNING],
                error=self._http_error(code, raw),
            )
        if not raw or b"<svg" not in raw[:500].lower():
            return HuagongsheSvgResult(
                status="error",
                kind=kind_norm,
                entity_id=eid,
                public_url=url,
                source=self._source(record_id=eid, url=url),
                warnings=[_LEAD_WARNING],
                error="化工社响应不是有效 SVG",
            )

        return HuagongsheSvgResult(
            status="ok",
            kind=kind_norm,
            entity_id=eid,
            public_url=url,
            bytes_len=len(raw),
            content=raw,
            source=self._source(record_id=eid, url=url),
            warnings=[_LEAD_WARNING],
        )

    def validate_reaction(self, reaction: Any) -> HuagongsheValidateResult:
        if not self._api_key:
            return HuagongsheValidateResult(
                status="error",
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=_TOKEN_REQUIRED,
            )
        payload, err = _parse_reaction_payload(reaction)
        if err or payload is None:
            return HuagongsheValidateResult(
                status="error",
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=err or "反应草稿无效",
            )

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        url = f"{API_BASE}/reactions/validate"
        headers = self._headers(write=True)
        headers["Content-Type"] = "application/json"
        try:
            code, raw = self._http_post(url, body, headers)
        except Exception as exc:
            return HuagongsheValidateResult(
                status="error",
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=f"化工社校验请求失败：{exc}",
            )

        if code in (400, 422):
            detail: Any = None
            try:
                detail = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                detail = raw.decode("utf-8", errors="replace") if raw else None
            return HuagongsheValidateResult(
                status="invalid",
                detail=detail,
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=self._http_error(code, raw, write=True),
            )
        if code not in (200, 201):
            return HuagongsheValidateResult(
                status="error",
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=self._http_error(code, raw, write=True),
            )

        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return HuagongsheValidateResult(
                status="error",
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=f"化工社校验响应不是合法 JSON：{exc}",
            )

        normalized = parsed if isinstance(parsed, dict) else {"result": parsed}
        return HuagongsheValidateResult(
            status="ok",
            normalized=normalized,
            source=self._source(),
            warnings=[_LEAD_WARNING, _WRITE_WARNING],
        )

    def create_reaction(
        self,
        reaction: Any,
        *,
        idempotency_key: str,
    ) -> HuagongsheCreateResult:
        key = (idempotency_key or "").strip()
        if not key:
            return HuagongsheCreateResult(
                status="error",
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error="缺少 Idempotency-Key；同一次保存重试须复用同一密钥",
            )
        if not self._api_key:
            return HuagongsheCreateResult(
                status="error",
                idempotency_key=key,
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=_TOKEN_REQUIRED,
            )
        payload, err = _parse_reaction_payload(reaction)
        if err or payload is None:
            return HuagongsheCreateResult(
                status="error",
                idempotency_key=key,
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=err or "反应草稿无效",
            )

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        url = f"{API_BASE}/reactions"
        headers = self._headers(write=True)
        headers["Content-Type"] = "application/json"
        headers["Idempotency-Key"] = key
        try:
            code, raw = self._http_post(url, body, headers)
        except Exception as exc:
            return HuagongsheCreateResult(
                status="error",
                idempotency_key=key,
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=f"化工社保存请求失败：{exc}",
            )

        if code not in (200, 201):
            return HuagongsheCreateResult(
                status="error",
                idempotency_key=key,
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=self._http_error(code, raw, write=True),
            )

        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return HuagongsheCreateResult(
                status="error",
                idempotency_key=key,
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error=f"化工社保存响应不是合法 JSON：{exc}",
            )

        if not isinstance(parsed, dict):
            return HuagongsheCreateResult(
                status="error",
                idempotency_key=key,
                source=self._source(),
                warnings=[_LEAD_WARNING, _WRITE_WARNING],
                error="化工社保存响应格式无效",
            )

        hrid = parsed.get("id") or parsed.get("hrid") or parsed.get("reaction_id")
        visibility = parsed.get("visibility")
        created = parsed.get("created_chemical_ids") or parsed.get("created_hcids") or []
        if not isinstance(created, list):
            created = []
        page_url = None
        if hrid is not None:
            page_url = f"https://huagongshe.com/reaction/{hrid}"
        if isinstance(parsed.get("url"), str) and parsed.get("url"):
            page_url = str(parsed.get("url"))

        return HuagongsheCreateResult(
            status="ok",
            hrid=hrid,
            page_url=page_url,
            visibility=str(visibility) if visibility is not None else None,
            created_chemical_ids=created,
            idempotency_key=key,
            source=self._source(record_id=str(hrid) if hrid is not None else ""),
            warnings=[_LEAD_WARNING, _WRITE_WARNING],
        )
