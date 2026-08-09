"""Deterministic lead-list formatting for ChemClaw sales workbench."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any, Optional

FORMATTER_VERSION = "1.0.0"
VALID_STATUS = {
    "new",
    "needs_review",
    "contactable",
    "contacted",
    "replied",
    "opportunity",
    "excluded",
}
STATUS_BUCKET = {
    "new": "needs_review",
    "needs_review": "needs_review",
    "contactable": "contactable",
    "contacted": "contactable",
    "replied": "contactable",
    "opportunity": "contactable",
    "excluded": "excluded",
}


@dataclass
class LeadListResult:
    status: str  # ok | error
    markdown: str = ""
    csv: str = ""
    counts: dict[str, int] = field(default_factory=dict)
    formatter_version: str = FORMATTER_VERSION
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "markdown": self.markdown,
            "csv": self.csv,
            "counts": dict(self.counts),
            "formatter_version": self.formatter_version,
            "error": self.error,
        }


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def format_lead_list(payload: dict[str, Any]) -> LeadListResult:
    """Format a LeadList payload into Markdown table + CSV text."""
    if not isinstance(payload, dict):
        return LeadListResult(status="error", error="payload must be an object")

    list_id = _as_str(payload.get("list_id")) or "lead-list"
    title = _as_str(payload.get("title")) or "客户清单"
    sku = _as_str(payload.get("sku_summary"))
    market = _as_str(payload.get("market_summary"))
    rule_version = _as_str(payload.get("rule_version")) or "chem-lead-fit@1.0.0"
    leads = payload.get("leads")
    if not isinstance(leads, list):
        return LeadListResult(status="error", error="leads must be an array")

    rows: list[dict[str, str]] = []
    counts = {"contactable": 0, "needs_review": 0, "excluded": 0, "total": 0}

    for index, raw in enumerate(leads):
        if not isinstance(raw, dict):
            return LeadListResult(status="error", error=f"leads[{index}] must be an object")
        company = _as_str(raw.get("company"))
        if not company:
            return LeadListResult(status="error", error=f"leads[{index}].company is required")
        sales_status = _as_str(raw.get("sales_status")) or "needs_review"
        if sales_status not in VALID_STATUS:
            return LeadListResult(
                status="error",
                error=f"leads[{index}].sales_status invalid: {sales_status}",
            )
        bucket = STATUS_BUCKET[sales_status]
        counts[bucket] += 1
        counts["total"] += 1
        fit = raw.get("fit_score")
        conf = raw.get("evidence_confidence")
        rows.append(
            {
                "company": company,
                "customer_type": _as_str(raw.get("customer_type")),
                "fit_score": "" if fit is None else str(fit),
                "evidence_confidence": "" if conf is None else str(conf),
                "match_reason": _as_str(raw.get("match_reason")),
                "key_evidence": _as_str(raw.get("key_evidence")),
                "latest_signal": _as_str(raw.get("latest_signal")),
                "risks_gaps": _as_str(raw.get("risks_gaps")),
                "next_action": _as_str(raw.get("next_action")),
                "sales_status": sales_status,
                "bucket": bucket,
                "notes": _as_str(raw.get("notes")),
                "exclude_reason": _as_str(raw.get("exclude_reason")),
            }
        )

    # Stable order: contactable, needs_review, excluded; then company name.
    bucket_order = {"contactable": 0, "needs_review": 1, "excluded": 2}
    rows.sort(key=lambda r: (bucket_order.get(r["bucket"], 9), r["company"].lower()))

    headers = [
        "company",
        "customer_type",
        "fit_score",
        "evidence_confidence",
        "match_reason",
        "key_evidence",
        "latest_signal",
        "risks_gaps",
        "next_action",
        "sales_status",
        "bucket",
        "notes",
        "exclude_reason",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({h: row.get(h, "") for h in headers})
    csv_text = buf.getvalue()

    md_lines = [
        f"# {title}",
        "",
        f"- 清单 ID：`{list_id}`",
        f"- SKU：{sku or '（未填）'}",
        f"- 市场：{market or '（未填）'}",
        f"- 规则版本：`{rule_version}`",
        f"- 可联系：{counts['contactable']} · 待补查：{counts['needs_review']} · 已排除：{counts['excluded']} · 合计：{counts['total']}",
        "",
        "| 企业 | 类型 | 商业匹配 | 证据置信度 | 匹配原因 | 下一步 | 状态 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        md_lines.append(
            "| "
            + " | ".join(
                [
                    row["company"].replace("|", "/"),
                    row["customer_type"].replace("|", "/") or "-",
                    row["fit_score"] or "-",
                    row["evidence_confidence"] or "-",
                    (row["match_reason"] or "-").replace("|", "/")[:80],
                    (row["next_action"] or "-").replace("|", "/")[:60],
                    row["sales_status"],
                ]
            )
            + " |"
        )
    if not rows:
        md_lines.append("| （空清单） | - | - | - | - | - | - |")

    md_lines.extend(
        [
            "",
            "## 分桶说明",
            "",
            "- `contactable`：可联系（含已联系/已回复/商机）",
            "- `needs_review`：待补查或新发现",
            "- `excluded`：已排除（保留排除原因，避免重复搜索）",
            "",
            f"_formatter `{FORMATTER_VERSION}` · 草稿清单，非自动外发_",
        ]
    )

    return LeadListResult(
        status="ok",
        markdown="\n".join(md_lines) + "\n",
        csv=csv_text,
        counts=counts,
    )
