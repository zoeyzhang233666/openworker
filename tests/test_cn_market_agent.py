"""Run 5: CN market tools register on the default Agent; Yahoo stays for global only."""

from __future__ import annotations

from coworker.agent import build_engine
from coworker.agents import chat_agent
from coworker.providers import ModelCapabilities
from coworker.tool_policy import NetworkScope, UsageClass, classify_tool
from coworker.yahoo_finance.tool import make_lookup_yahoo_ohlc_tool

CN_MARKET_TOOLS = (
    "lookup_cn_stock_quote",
    "lookup_cn_stock_ohlc",
    "lookup_cn_stock_minute",
    "lookup_cn_stock_financials",
    "lookup_cn_stock_feature",
    "lookup_cn_futures_quote",
    "lookup_cn_futures_ohlc",
    "lookup_cn_futures_minute",
    "lookup_cn_futures_l1",
    "calculate_cn_futures_margin",
    "lookup_cn_option_market",
)

WIND_TOOL = "wind_financial_reference_content"


class _Stub:
    def complete(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def capabilities(self, model):
        return ModelCapabilities()


def test_build_engine_registers_cn_market_tools_and_keeps_yahoo():
    eng = build_engine(agent=chat_agent(), provider=_Stub())
    names = set(eng.registry.names())
    for tool in CN_MARKET_TOOLS:
        assert tool in names, tool
    assert "lookup_yahoo_ohlc" in names
    assert WIND_TOOL not in names
    assert "akshare" not in names


def test_inline_guidance_routes_mainland_cn_away_from_yahoo():
    eng = build_engine(agent=chat_agent(), provider=_Stub())
    sys_msg = eng.messages[0]["content"]
    assert "lookup_cn_stock_ohlc" in sys_msg
    assert "lookup_cn_futures_ohlc" in sys_msg
    assert "lookup_cn_option_market" in sys_msg
    assert "lookup_yahoo_ohlc" in sys_msg
    lowered = sys_msg.lower()
    assert "mainland" in lowered or "a-share" in lowered or "A股" in sys_msg
    assert "do not use yahoo" in lowered or "never use yahoo" in lowered


def test_inline_guidance_defaults_unspecified_period_to_daily():
    eng = build_engine(agent=chat_agent(), provider=_Stub())
    sys_msg = eng.messages[0]["content"]
    assert "Default bar interval" in sys_msg
    assert "daily" in sys_msg.lower()
    assert "never `lookup_cn_*_minute`" in sys_msg
    assert "never Yahoo" in sys_msg
    assert "`interval=1wk` or `1mo`" in sys_msg
    assert "(or ≥12 monthly points)" not in sys_msg
    assert "only if the user asked for intraday/minutes" in sys_msg
    assert "action=daily" in sys_msg


def test_yahoo_tool_description_defers_mainland_cn():
    tool = make_lookup_yahoo_ohlc_tool()
    desc = tool.__coworker_schema__["function"]["description"]
    assert "CL=F" in desc
    assert "lookup_cn_" in desc
    assert "A-share" in desc or "A股" in desc or "mainland" in desc.lower()
    assert "Default is daily" in desc
    assert "1wk/1mo only" in desc


def test_cn_market_tools_are_remote_other_not_unknown():
    for name in CN_MARKET_TOOLS:
        scope, usage = classify_tool(name)
        assert scope is NetworkScope.REMOTE, name
        assert usage is UsageClass.OTHER, name
