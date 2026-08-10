"""Customs / bill-of-lading file provider — enterprise importer screening.

Reads CSV from the user workspace. Filters freight-forwarder noise and scores
likely importers. Consignee rows are trade clues, not proven end buyers.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

PROVIDER_ID = "customs_file"
PROVIDER_VERSION = "1.0.0"

_BUYER_WARNING = (
    "收货方/进口商不等于终端买家；货代与物流方应优先排除或人工复核。"
    "结果仅为交易线索旁证，须与官网/主体信息交叉核验后再写入 Lead。"
)

_COMPANY_ALIASES = (
    "consignee_name",
    "consignee",
    "importer_name",
    "importer",
    "buyer_name",
    "buyer",
    "company_name",
    "company",
)
_ROLE_ALIASES = ("party_role", "role", "party_type")
_ADDRESS_ALIASES = (
    "consignee_address",
    "address",
    "importer_address",
    "buyer_address",
)
_PRODUCT_ALIASES = (
    "product_description",
    "description",
    "product",
    "commodity",
    "goods_description",
)
_HS_ALIASES = ("hs_code", "hs", "hscode", "harmonized_code", "htscode")
_DATE_ALIASES = ("arrival_date", "date", "shipment_date", "import_date")
_VALUE_ALIASES = ("customs_value", "value", "shipment_value", "cif_value")
_SHIPPER_ALIASES = (
    "shipper_name",
    "shipper",
    "supplier",
    "exporter",
    "exporter_name",
)

_FORWARDER_KEYWORDS = (
    "freight",
    "forwarder",
    "forwarding",
    "logistics",
    "customs broker",
    "brokerage",
    "warehouse",
    "warehousing",
    "shipping",
    "carrier",
    "consolidat",
    "nvocc",
    "po box",
    "p.o. box",
    "care of",
    "c/o ",
    "货代",
    "货运代理",
    "物流",
    "报关",
    "仓储",
    "船运",
    "海运代理",
)

_ROLE_IMPORTER = frozenset(
    {"consignee", "importer", "buyer", "收货人", "进口商", "买方"}
)
_ROLE_NOTIFY = frozenset({"notify", "notify party", "通知方"})
_ROLE_BROKER = frozenset(
    {"customs broker", "broker", "freight forwarder", "forwarder", "货代", "报关行"}
)


@dataclass
class CustomsFilterResult:
    status: str  # ok | empty | error
    candidates: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "candidates": list(self.candidates),
            "summary": dict(self.summary),
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "error": self.error,
        }


def _norm_header(name: str) -> str:
    return re.sub(r"[\s\-]+", "_", (name or "").strip().lower())


def _pick_column(headers: list[str], aliases: tuple[str, ...]) -> Optional[str]:
    normalized = {_norm_header(h): h for h in headers}
    for alias in aliases:
        key = _norm_header(alias)
        if key in normalized:
            return normalized[key]
    return None


def _keyword_hits(text: str) -> list[str]:
    lower = (text or "").lower()
    hits: list[str] = []
    for kw in _FORWARDER_KEYWORDS:
        if kw in lower:
            hits.append(kw)
    return hits


def _parse_float(raw: str) -> Optional[float]:
    s = (raw or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


class CustomsFileProvider:
    """Screen importers from a workspace customs/BOL CSV."""

    name = PROVIDER_ID

    def filter_importers(
        self,
        *,
        path: str,
        limit: int = 20,
        company_col: str = "",
        role_col: str = "",
        address_col: str = "",
        product_col: str = "",
        hs_col: str = "",
        date_col: str = "",
        value_col: str = "",
        shipper_col: str = "",
    ) -> CustomsFilterResult:
        source = {
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
            "path": path or "",
        }
        warnings = [_BUYER_WARNING]
        file_path = Path(path or "")
        if not path or not str(path).strip():
            return CustomsFilterResult(
                status="error",
                source=source,
                warnings=warnings,
                error="未提供海关/提单 CSV 路径。请将文件放入工作区后传入 path。",
            )
        if not file_path.is_file():
            return CustomsFilterResult(
                status="error",
                source=source,
                warnings=warnings,
                error=f"找不到海关数据文件：{file_path}。请确认路径在已挂载工作区内且为 CSV。",
            )
        if file_path.suffix.lower() not in {".csv", ".txt"}:
            return CustomsFilterResult(
                status="error",
                source=source,
                warnings=warnings,
                error="首包仅支持 CSV（.csv）。XLSX 与外部海关 API 尚未接入。",
            )

        try:
            with file_path.open(encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                if not reader.fieldnames:
                    return CustomsFilterResult(
                        status="error",
                        source=source,
                        warnings=warnings,
                        error="CSV 无表头。至少需要公司列（如 consignee_name / importer / buyer）。",
                    )
                headers = list(reader.fieldnames)
                rows = list(reader)
        except UnicodeDecodeError:
            return CustomsFilterResult(
                status="error",
                source=source,
                warnings=warnings,
                error="无法以 UTF-8 读取 CSV。请另存为 UTF-8 后再试。",
            )
        except OSError as exc:
            return CustomsFilterResult(
                status="error",
                source=source,
                warnings=warnings,
                error=f"读取海关文件失败：{exc}",
            )

        cols = {
            "company": company_col or _pick_column(headers, _COMPANY_ALIASES),
            "role": role_col or _pick_column(headers, _ROLE_ALIASES),
            "address": address_col or _pick_column(headers, _ADDRESS_ALIASES),
            "product": product_col or _pick_column(headers, _PRODUCT_ALIASES),
            "hs": hs_col or _pick_column(headers, _HS_ALIASES),
            "date": date_col or _pick_column(headers, _DATE_ALIASES),
            "value": value_col or _pick_column(headers, _VALUE_ALIASES),
            "shipper": shipper_col or _pick_column(headers, _SHIPPER_ALIASES),
        }
        if not cols["company"]:
            return CustomsFilterResult(
                status="error",
                source=source,
                warnings=warnings,
                error=(
                    "缺少公司列。请提供 consignee_name / importer / buyer / company "
                    "之一，或通过 company_col 指定列名。"
                ),
            )

        source["columns"] = {k: v for k, v in cols.items() if v}
        aggregates: dict[str, dict[str, Any]] = {}

        for raw in rows:
            company = (raw.get(cols["company"]) or "").strip()
            if not company:
                continue
            key = re.sub(r"\s+", " ", company).casefold()
            bucket = aggregates.get(key)
            if bucket is None:
                bucket = {
                    "company_name": company,
                    "roles": set(),
                    "addresses": set(),
                    "products": set(),
                    "hs_codes": set(),
                    "shippers": set(),
                    "shipment_count": 0,
                    "total_value": 0.0,
                    "keyword_hits": set(),
                    "sample_dates": [],
                }
                aggregates[key] = bucket

            bucket["shipment_count"] += 1
            if cols["role"]:
                role = (raw.get(cols["role"]) or "").strip()
                if role:
                    bucket["roles"].add(role)
            if cols["address"]:
                addr = (raw.get(cols["address"]) or "").strip()
                if addr:
                    bucket["addresses"].add(addr)
                    bucket["keyword_hits"].update(_keyword_hits(addr))
            if cols["product"]:
                prod = (raw.get(cols["product"]) or "").strip()
                if prod:
                    bucket["products"].add(prod)
            if cols["hs"]:
                hs = re.sub(r"\D", "", (raw.get(cols["hs"]) or "").strip())
                if hs:
                    bucket["hs_codes"].add(hs[:6] if len(hs) >= 6 else hs)
            if cols["shipper"]:
                ship = (raw.get(cols["shipper"]) or "").strip()
                if ship:
                    bucket["shippers"].add(ship)
            if cols["value"]:
                val = _parse_float(raw.get(cols["value"]) or "")
                if val is not None:
                    bucket["total_value"] += val
            if cols["date"]:
                dt = (raw.get(cols["date"]) or "").strip()
                if dt and len(bucket["sample_dates"]) < 5:
                    bucket["sample_dates"].append(dt)
            bucket["keyword_hits"].update(_keyword_hits(company))
            for role in list(bucket["roles"]):
                bucket["keyword_hits"].update(_keyword_hits(role))

        if not aggregates:
            return CustomsFilterResult(
                status="empty",
                candidates=[],
                summary={
                    "raw_rows": len(rows),
                    "companies": 0,
                    "excluded": 0,
                    "review": 0,
                    "likely_targets": 0,
                },
                source=source,
                warnings=warnings,
            )

        candidates: list[dict[str, Any]] = []
        for bucket in aggregates.values():
            scored = _score_company(bucket)
            candidates.append(scored)

        candidates.sort(
            key=lambda c: (
                c["importer_likelihood"],
                c["shipment_count"],
                c["total_value"],
            ),
            reverse=True,
        )
        lim = max(1, min(int(limit or 20), 100))
        top = candidates[:lim]

        summary = {
            "raw_rows": len(rows),
            "companies": len(candidates),
            "excluded": sum(1 for c in candidates if c["recommendation"] == "exclude"),
            "review": sum(
                1
                for c in candidates
                if c["recommendation"]
                in ("needs_manual_review", "possible_freight_forwarder", "possible_trader")
            ),
            "likely_targets": sum(
                1 for c in candidates if c["recommendation"] == "likely_real_importer"
            ),
            "returned": len(top),
        }
        return CustomsFilterResult(
            status="ok",
            candidates=top,
            summary=summary,
            source=source,
            warnings=warnings,
        )


def _score_company(bucket: dict[str, Any]) -> dict[str, Any]:
    roles = {str(r).strip().lower() for r in bucket["roles"]}
    hits = sorted(bucket["keyword_hits"])
    hs_codes = sorted(bucket["hs_codes"])
    products = sorted(bucket["products"])
    shippers = sorted(bucket["shippers"])
    shipment_count = int(bucket["shipment_count"])
    total_value = float(bucket["total_value"])

    freight_risk = min(100, 25 * len(hits))
    if any(r in _ROLE_BROKER for r in roles):
        freight_risk = min(100, freight_risk + 40)
    if any("po box" in a.lower() or "care of" in a.lower() for a in bucket["addresses"]):
        freight_risk = min(100, freight_risk + 20)

    importer_likelihood = 40
    if roles & _ROLE_IMPORTER:
        importer_likelihood += 20
    if roles & _ROLE_NOTIFY and not (roles & _ROLE_IMPORTER):
        importer_likelihood -= 15
    if roles & _ROLE_BROKER:
        importer_likelihood -= 35

    hs_n = len(hs_codes)
    if hs_n == 1:
        importer_likelihood += 20
    elif hs_n == 2:
        importer_likelihood += 10
    elif hs_n >= 4:
        importer_likelihood -= 15

    if 2 <= shipment_count <= 50:
        importer_likelihood += 10
    elif shipment_count > 80:
        importer_likelihood -= 15

    if len(shippers) == 1 and shipment_count >= 2:
        importer_likelihood += 8
    if total_value >= 10000:
        importer_likelihood += 5

    importer_likelihood -= freight_risk // 5
    importer_likelihood = max(0, min(100, importer_likelihood))

    if freight_risk >= 70 or importer_likelihood <= 20:
        recommendation = "exclude"
    elif freight_risk >= 45 or (roles & _ROLE_BROKER):
        recommendation = "possible_freight_forwarder"
    elif importer_likelihood >= 65 and hs_n <= 2 and roles & _ROLE_IMPORTER:
        recommendation = "likely_real_importer"
    elif importer_likelihood >= 45:
        recommendation = "possible_trader"
    else:
        recommendation = "needs_manual_review"

    evidence = []
    if hits:
        evidence.append("货代/物流关键词：" + "、".join(hits[:6]))
    if roles:
        evidence.append("角色：" + "、".join(sorted(roles)[:5]))
    if hs_codes:
        evidence.append("HS 集中：" + "、".join(hs_codes[:5]))
    if shippers:
        evidence.append("主要供应商：" + "、".join(shippers[:3]))
    evidence.append(f"Shipment 次数={shipment_count}")

    return {
        "company_name": bucket["company_name"],
        "roles": sorted(roles),
        "addresses": sorted(bucket["addresses"])[:3],
        "hs_codes": hs_codes[:8],
        "products": products[:8],
        "shippers": shippers[:5],
        "shipment_count": shipment_count,
        "total_value": round(total_value, 2),
        "sample_dates": list(bucket["sample_dates"]),
        "freight_forwarder_risk": freight_risk,
        "importer_likelihood": importer_likelihood,
        "keyword_hits": hits,
        "recommendation": recommendation,
        "evidence_summary": "；".join(evidence),
    }
