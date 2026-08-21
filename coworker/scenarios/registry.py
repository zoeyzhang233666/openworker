"""Versioned built-in Scenario registry.

Scenario entries deliberately contain business Capability IDs only. Exact Tool names
belong to the Capability registry so product intent and provider plumbing cannot drift.
"""

from __future__ import annotations

from .models import ScenarioSpec


class ScenarioRegistry:
    def __init__(self, specs: tuple[ScenarioSpec, ...]) -> None:
        by_id: dict[str, ScenarioSpec] = {}
        for spec in specs:
            if spec.id in by_id:
                raise ValueError(f"duplicate scenario id: {spec.id}")
            by_id[spec.id] = spec
        self._by_id = by_id

    def get(self, scenario_id: str) -> ScenarioSpec | None:
        return self._by_id.get(scenario_id)

    def require(self, scenario_id: str) -> ScenarioSpec:
        spec = self.get(scenario_id)
        if spec is None:
            raise KeyError(f"unknown scenario id: {scenario_id}")
        return spec

    def list(self) -> tuple[ScenarioSpec, ...]:
        return tuple(sorted(self._by_id.values(), key=lambda item: (-item.priority, item.id)))


_BUILTINS = ScenarioRegistry(
    (
        ScenarioSpec(
            id="chemical_spot_price",
            category="market",
            title="化工现货价格",
            description="查询化工品现货价格或现货趋势。",
            examples=("甲醇现货多少钱", "查询苯酚现货价格", "chemical spot price"),
            aliases=("现货", "spot"),
            required_capabilities=("market.price.chemical_spot",),
            output_contract="market_quote",
            fallback_policy=("report_unavailable",),
            priority=100,
        ),
        ScenarioSpec(
            id="cn_futures_market",
            category="market",
            title="国内期货行情",
            description="查询国内期货报价、日线或指定周期行情。",
            examples=("甲醇期货现在多少钱", "MA 主力日线走势", "国内期货报价"),
            aliases=("期货", "主力", "futures"),
            required_capabilities=("market.price.cn_futures.quote",),
            optional_capabilities=("market.ohlc.cn_futures",),
            output_contract="market_quote_or_ohlc",
            fallback_policy=("report_unavailable",),
            priority=100,
        ),
        ScenarioSpec(
            id="chemical_identity",
            category="chemical",
            title="化学品标识",
            description="按名称或 CAS 查询化学品标识。",
            examples=("查询 CAS 67-56-1", "甲醇的分子式", "identify chemical"),
            aliases=("CAS", "分子式", "化学标识"),
            required_capabilities=("chem.identity",),
            output_contract="chemical_identity",
            fallback_policy=("report_unavailable",),
            priority=90,
        ),
        ScenarioSpec(
            id="chemical_company_research",
            category="research",
            title="化工企业研究",
            description="研究化工企业、主体和经营证据。",
            examples=("深度研究万华化学", "调研巴斯夫公司", "chemical company research"),
            aliases=("企业研究", "公司调研"),
            required_capabilities=("company.identity", "research.web.search"),
            optional_capabilities=("research.web.fetch",),
            output_contract="research_report",
            fallback_policy=("continue_with_available_evidence",),
            allow_subagent=True,
            priority=70,
        ),
        ScenarioSpec(
            id="chemical_market_research",
            category="research",
            title="化工市场研究",
            description="研究化工品市场、供需、产业链与未来趋势。",
            examples=("研究未来半年 MDI 市场", "化工市场供需分析", "chemical market research"),
            aliases=("市场研究", "产业链", "供需"),
            required_capabilities=("research.web.search",),
            optional_capabilities=("research.web.fetch",),
            output_contract="research_report",
            fallback_policy=("continue_with_available_evidence",),
            allow_subagent=True,
            priority=60,
        ),
    )
)


def builtin_scenario_registry() -> ScenarioRegistry:
    return _BUILTINS
