"""Platform-neutral, content-safe report progress contracts."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ReportStage(str, Enum):
    QUEUED = "queued"
    RESOLVING_PRODUCT = "resolving_product"
    FETCHING_PRICES = "fetching_prices"
    FETCHING_NEWS = "fetching_news"
    VERIFYING_WEB = "verifying_web"
    ANALYZING = "analyzing"
    RENDERING = "rendering"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


_LABELS = {
    ReportStage.QUEUED: "已开始准备市场报告",
    ReportStage.RESOLVING_PRODUCT: "正在确认品名与报价口径",
    ReportStage.FETCHING_PRICES: "正在读取结构化现货价格",
    ReportStage.FETCHING_NEWS: "正在核验市场资讯",
    ReportStage.VERIFYING_WEB: "正在补充公开来源",
    ReportStage.ANALYZING: "正在归纳周度变化与驱动",
    ReportStage.RENDERING: "正在生成完整报告",
    ReportStage.UPLOADING: "正在准备 HTML 与预览图",
    ReportStage.COMPLETED: "市场报告已完成",
    ReportStage.PARTIAL: "市场报告已部分完成",
    ReportStage.FAILED: "市场报告未能完成",
}


@dataclass(frozen=True)
class ReportProgress:
    job_id: str
    stage: ReportStage
    detail: str = ""
    updated_at: float = field(default_factory=time.time)

    @property
    def text(self) -> str:
        base = _LABELS[self.stage]
        return f"ChemClaw {base}{'：' + self.detail if self.detail else '…'}"
