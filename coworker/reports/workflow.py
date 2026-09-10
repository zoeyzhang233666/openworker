"""The D-201 report workflow's small public interface.

Callers only ask whether a turn starts a report and request a bounded background brief;
the Scenario, background profile, timing and presentation details remain local here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReportBudget:
    summary_model_turns: int = 3
    soft_deadline_seconds: int = 180
    hard_deadline_seconds: int = 240


class ReportWorkflow:
    budget = ReportBudget()
    scenario_id = "chemical_market_report"

    @classmethod
    def starts_for(cls, plan: Any) -> bool:
        resolution = getattr(plan, "scenario_resolution", None)
        return getattr(resolution, "scenario_id", None) == cls.scenario_id

    @staticmethod
    def background_brief(request: str, summary: str) -> str:
        return (
            "为以下请求完成市场报告：\n"
            f"{request}\n\n"
            "前台摘要如下（只可复用其中的结论，不得假设未展示的原始数据）：\n"
            f"{summary[:6000]}"
        )
