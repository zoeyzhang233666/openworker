"""Verified child-tool effects; approval preference is not evidence of read-only."""
from __future__ import annotations

from ..risk import RiskClass

# Reviewed first-party queries. Unknown extensions never enter via a naming heuristic.
READ_TOOLS = frozenset({
    "grep", "read_file", "list_files", "read_file_lines", "git_log", "git_status", "git_diff",
    "search_tools", "load_tools", "search_skills", "load_skill", "web_search", "web_fetch",
    "lookup_chemical_identity", "lookup_legal_entity", "validate_eu_vat", "lookup_fx_rate",
    "lookup_wikipedia", "lookup_yahoo_ohlc", "lookup_cn_stock_quote", "lookup_cn_stock_ohlc",
    "lookup_cn_stock_minute", "lookup_cn_stock_financials", "lookup_cn_stock_feature",
    "lookup_cn_futures_quote", "lookup_cn_futures_ohlc", "lookup_cn_futures_minute",
    "lookup_cn_futures_l1", "calculate_cn_futures_margin", "lookup_cn_option_market",
    "search_huagongshe", "lookup_huagongshe_chemical", "search_tenders",
    "search_sam_opportunities", "lookup_trade_flow",
})


def verified_readonly(name, spec, overrides=None):
    if spec is None:
        return False
    category = getattr(spec.metadata, "category", "")
    if category in {"mcp", "connector"} or name.startswith("mcp__"):
        # Only an explicit user-local classification, never requires_approval=False,
        # risk_level=low, a remote hint, or a word such as `get` in the tool name.
        return overrides is not None and overrides(name) is RiskClass.READ
    return name in READ_TOOLS


RETIRED_MESSAGE = "该小助手原先允许写入，现已暂停使用；历史记录保留，请由主助手接管文件修改或报告交付。"
