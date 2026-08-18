"""Run 4: SSE ETF options + CFFEX board. Offline HTTP fixtures only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from coworker.cn_market.cache import MarketCache
from coworker.cn_market.models import (
    STATUS_INVALID_REQUEST,
    STATUS_INVALID_SYMBOL,
    STATUS_OK,
    STATUS_SOURCE_UNAVAILABLE,
    STATUS_UNSUPPORTED,
)
from coworker.cn_market.providers.options import PublicCNOptionProvider
from coworker.cn_market.providers.stocks import PublicCNStockProvider
from coworker.cn_market.source_policy import policy_for
from coworker.cn_market.symbols import resolve_option_underlying
from coworker.cn_market.tools.options import make_lookup_cn_option_market_tool


def _jsonp(payload) -> bytes:
    return ("(" + json.dumps(payload, ensure_ascii=False) + ")").encode("utf-8")


def _months_payload():
    return {
        "result": {
            "data": {
                "contractMonth": ["2026-08", "2026-08", "2026-09", "2026-12", "2027-03"],
            }
        }
    }


def _spot_body(code: str = "10011255") -> bytes:
    values = [""] * 48
    values[0] = "1"
    values[1] = "0.3500"
    values[2] = "0.3565"
    values[3] = "0.3750"
    values[4] = "1"
    values[5] = "1711"
    values[6] = "-11.32"
    values[7] = "2.6500"
    values[8] = "0.3865"
    values[9] = "0.3853"
    values[32] = "2026-08-18 11:13:25"
    values[36] = "510050"
    values[37] = "50ETF购9月2650"
    values[39] = "0.3853"
    values[40] = "0.3565"
    values[41] = "98"
    values[42] = "359405.00"
    values[44] = "0.4020"
    values[45] = "C"
    values[46] = "2026-09-23"
    values[47] = "36"
    return (f'var hq_str_CON_OP_{code}="' + ",".join(values) + '";\n').encode("gbk")


def _greeks_body(code: str = "10011255") -> bytes:
    inner = (
        "50ETF购9月2650,,,,98,0.9849,0.1948,-0.1416,0.0363,0.0008,"
        "0.3853,0.3565,510050C2609M02650,2.6500,0.3565,0.3915,M"
    )
    return (f'var hq_str_CON_SO_{code}="{inner}";\n').encode("gbk")


def _router(url: str, headers=None):
    if "StockOptionService.getStockName" in url:
        return 200, json.dumps(_months_payload()).encode("utf-8")
    if "list=OP_UP_510050" in url:
        body = 'var hq_str_OP_UP_5100502609="CON_OP_10011255,CON_OP_10011256,";\n'
        return 200, body.encode("gbk")
    if "list=OP_DOWN_510050" in url:
        body = 'var hq_str_OP_DOWN_5100502609="CON_OP_10011290,CON_OP_10011291,";\n'
        return 200, body.encode("gbk")
    if "list=CON_OP_" in url:
        return 200, _spot_body()
    if "list=CON_SO_" in url:
        return 200, _greeks_body()
    if "StockOptionDaylineService.getSymbolInfo" in url:
        payload = [
            {"d": "2026-08-17", "o": "0.3800", "h": "0.3900", "l": "0.3700", "c": "0.3850", "v": "100"},
            {"d": "2026-08-18", "o": "0.3853", "h": "0.3900", "l": "0.3565", "c": "0.3565", "v": "98"},
        ]
        return 200, _jsonp(payload)
    if "StockOptionDaylineService.getOptionMinline" in url:
        payload = {
            "result": {
                "status": {"code": 0},
                "data": [
                    {
                        "i": "09:30:00",
                        "p": "0.3853",
                        "v": "1",
                        "t": "1702",
                        "a": "0.3853",
                        "d": "2026-08-18",
                    },
                    {
                        "i": "09:31:00",
                        "p": "0.3860",
                        "v": "2",
                        "t": "1704",
                        "a": "0.3856",
                    },
                ],
            }
        }
        return 200, json.dumps(payload).encode("utf-8")
    if "OptionService.getOptionData" in url:
        payload = {
            "result": {
                "status": {"code": 0},
                "data": {
                    "up": [
                        ["1", "10", "11", "12", "1", "100", 0.1, "2800", "io2509C2800"],
                        ["2", "20", "21", "22", "2", "200", 0.2, "2900", "io2509C2900"],
                    ],
                    "down": [
                        ["3", "5", "6", "7", "3", "50", -0.1, "2800", "io2509P2800"],
                    ],
                },
            }
        }
        return 200, json.dumps(payload).encode("utf-8")
    if "query.sse.com.cn" in url or "commonQuery.do" in url:
        return 500, b"unavailable"
    return 404, b"missing"


def _provider(tmp_path: Path) -> PublicCNOptionProvider:
    return PublicCNOptionProvider(
        http_get=_router,
        cache=MarketCache(root=tmp_path),
        clock=lambda: datetime(2026, 8, 18, 16, 0, tzinfo=timezone.utc),
    )


def test_option_policy_and_underlying_aliases():
    policy = policy_for("option_sse")
    assert policy.keyless is True
    assert policy.primary in {"sse_option_list", "sina_option"}
    u = resolve_option_underlying("50ETF")
    assert u.code == "510050"
    assert u.exchange == "SSE"
    assert u.sina_cate == "50ETF"
    assert resolve_option_underlying("510300").sina_cate == "300ETF"
    assert resolve_option_underlying("沪深300").exchange == "CFFEX"


def test_contracts_discovery_call_put_and_expiry(tmp_path: Path):
    table = _provider(tmp_path).option_market(
        action="contracts", underlying="510050", expiry="202609"
    )
    assert table.status == STATUS_OK
    assert table.dataset == "option_contracts"
    codes = {row["contract"] for row in table.rows}
    assert "10011255" in codes
    assert "10011290" in codes
    types = {row["option_type"] for row in table.rows}
    assert types == {"call", "put"}


def test_quote_daily_minute_greeks(tmp_path: Path):
    p = _provider(tmp_path)
    quote = p.option_market(action="quote", contract="10011255")
    assert quote.status == STATUS_OK
    assert quote.symbol == "10011255"
    assert quote.last == 0.3565
    assert quote.bid1 == 0.3500
    assert quote.ask1 == 0.3750
    assert quote.strike == 2.65
    assert quote.option_type == "call"
    assert quote.underlying == "510050"

    daily = p.option_market(action="daily", contract="10011255", range="3mo")
    assert daily.status == STATUS_OK
    assert daily.interval == "1d"
    assert len(daily.ohlc) == 2
    assert daily.ohlc[-1].c == 0.3565
    assert daily.chart_spec()["type"] == "candlestick"

    minute = p.option_market(action="minute", contract="10011255")
    assert minute.status == STATUS_OK
    assert minute.interval == "1m"
    assert len(minute.ohlc) == 2

    greeks = p.option_market(action="greeks", contract="10011255")
    assert greeks.status == STATUS_OK
    assert greeks.greeks_source == "upstream"
    assert greeks.delta == 0.9849
    assert greeks.gamma == 0.1948
    assert greeks.theta == -0.1416
    assert greeks.vega == 0.0363
    assert greeks.implied_vol == 0.0008


def test_cffex_contracts_board(tmp_path: Path):
    table = _provider(tmp_path).option_market(
        action="contracts", underlying="IO", expiry="io2509"
    )
    assert table.status == STATUS_OK
    assert any(r["contract"] == "io2509C2800" for r in table.rows)
    assert any(r["option_type"] == "put" for r in table.rows)


def test_exchange_stats_and_invalid_actions(tmp_path: Path):
    stats = _provider(tmp_path).option_market(action="exchange_stats", underlying="510050")
    assert stats.status in {STATUS_SOURCE_UNAVAILABLE, STATUS_UNSUPPORTED}
    bad = _provider(tmp_path).option_market(action="invent_greeks")
    assert bad.status == STATUS_INVALID_REQUEST
    unknown = _provider(tmp_path).option_market(action="quote", contract="!!!!")
    assert unknown.status in {STATUS_INVALID_SYMBOL, STATUS_SOURCE_UNAVAILABLE}


def test_tool_action_enum_without_agent_wiring(tmp_path: Path):
    p = _provider(tmp_path)
    tool = make_lookup_cn_option_market_tool(provider=p)
    out = tool(action="quote", contract="10011255")
    assert out["status"] == "ok"
    assert out["last"] == 0.3565
    assert tool.__coworker_schema__["function"]["name"] == "lookup_cn_option_market"
    assert "akshare" not in str(out["source"]["provider"]).lower()


def test_core35_unverified_concept_stays_unsupported(tmp_path: Path):
    # Run 0 did not verify concept/industry endpoints; Run 4 must not invent sources.
    table = PublicCNStockProvider(
        http_get=lambda url, headers=None: (404, b"missing"),
        cache=MarketCache(root=tmp_path),
    ).stock_feature("concept_list")
    assert table.status == STATUS_UNSUPPORTED
