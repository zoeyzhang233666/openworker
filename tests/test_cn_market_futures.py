"""Run 3: domestic futures quote/OHLC/minute/L1/margin. Offline HTTP fixtures only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from coworker.cn_market.cache import MarketCache
from coworker.cn_market.futures.continuous import select_dominant_contract
from coworker.cn_market.futures.margin import calculate_theoretical_margin
from coworker.cn_market.models import (
    STATUS_INVALID_REQUEST,
    STATUS_INVALID_SYMBOL,
    STATUS_OK,
)
from coworker.cn_market.providers.futures import PublicCNFuturesProvider
from coworker.cn_market.source_policy import MAX_PROVIDER_ATTEMPTS, policy_for
from coworker.cn_market.symbols import resolve_futures
from coworker.cn_market.tools.futures import (
    make_calculate_cn_futures_margin_tool,
    make_lookup_cn_futures_l1_tool,
    make_lookup_cn_futures_minute_tool,
    make_lookup_cn_futures_ohlc_tool,
    make_lookup_cn_futures_quote_tool,
)


def _jsonp(payload) -> bytes:
    return ("=(" + json.dumps(payload, ensure_ascii=False) + ");").encode("utf-8")


def _l1_rows():
    return [
        {
            "symbol": "MA0",
            "name": "甲醇连续",
            "trade": "2410.00",
            "open": "2400.00",
            "high": "2450.00",
            "low": "2380.00",
            "bidprice1": "2409.00",
            "askprice1": "2411.00",
            "bidvol1": "12",
            "askvol1": "8",
            "volume": "999999",
            "position": "999999",
            "settlement": "2408.00",
            "presettlement": "2390.00",
            "ticktime": "15:00:00",
        },
        {
            "symbol": "MA2505",
            "name": "甲醇2505",
            "trade": "2380.00",
            "open": "2370.00",
            "high": "2390.00",
            "low": "2360.00",
            "bidprice1": "2379.00",
            "askprice1": "2381.00",
            "bidvol1": "20",
            "askvol1": "15",
            "volume": "80000",
            "position": "10000",
            "settlement": "2378.00",
            "presettlement": "2360.00",
            "ticktime": "15:00:00",
        },
        {
            "symbol": "MA2509",
            "name": "甲醇2509",
            "trade": "2420.00",
            "open": "2410.00",
            "high": "2440.00",
            "low": "2400.00",
            "bidprice1": "2419.00",
            "askprice1": "2421.00",
            "bidvol1": "30",
            "askvol1": "18",
            "volume": "120000",
            "position": "50000",
            "settlement": "2418.00",
            "presettlement": "2395.00",
            "ticktime": "15:00:00",
        },
        {
            "symbol": "",
            "name": "小计",
            "trade": "0",
            "volume": "200000",
            "position": "60000",
        },
    ]


def _daily_contract():
    return [
        ["2026-07-20", "2400", "2450", "2380", "2420", "100000", "200000", "2410"],
        ["2026-08-17", "2410", "2430", "2400", "2415", "110000", "210000", "2412"],
        ["2026-08-18", "2415", "2440", "2405", "2420", "120000", "220000", "2418"],
    ]


def _daily_continuous():
    return [
        ["2026-07-20", "1000", "1100", "900", "9999", "1", "1", "1000"],
        ["2026-08-18", "1000", "1100", "900", "9999", "1", "1", "1000"],
    ]


def _minute_bars():
    return [
        ["2026-08-18 14:55:00", "2418", "2421", "2417", "2420", "80", "219000"],
        ["2026-08-18 15:00:00", "2420", "2422", "2419", "2421", "90", "220000"],
    ]


def _router(url: str, headers=None):
    if "Market_Center.getHQFuturesData" in url:
        return 200, json.dumps(_l1_rows()).encode("utf-8")
    if "InnerFuturesNewService.getDailyKLine" in url:
        if "symbol=MA0" in url:
            return 200, _jsonp(_daily_continuous())
        return 200, _jsonp(_daily_contract())
    if "InnerFuturesNewService.getFewMinLine" in url:
        return 200, _jsonp(_minute_bars())
    return 404, b"missing"


def _provider(tmp_path: Path) -> PublicCNFuturesProvider:
    return PublicCNFuturesProvider(
        http_get=_router,
        cache=MarketCache(root=tmp_path),
        clock=lambda: datetime(2026, 8, 18, 16, 0, tzinfo=timezone.utc),
    )


def test_futures_policy_is_keyless_sina():
    daily = policy_for("futures_daily")
    assert daily.primary == "sina_futures_daily"
    assert daily.keyless is True
    minute = policy_for("futures_minute")
    assert minute.primary == "sina_futures_minute"
    l1 = policy_for("futures_l1")
    assert l1.primary == "sina_futures_realtime"
    assert MAX_PROVIDER_ATTEMPTS == 2


def test_sina_symbol_casing_follows_exchange():
    ma = resolve_futures("甲醇")
    assert ma.sina_node == "zc_qh"
    assert ma.sina_continuous == "MA0"
    contract = resolve_futures("MA2509")
    assert contract.sina_kline == "MA2509"
    assert contract.sina_node == "zc_qh"
    pg = resolve_futures("液化气")
    assert pg.sina_node == "pg_qh"
    assert pg.sina_continuous == "PG0"
    assert resolve_futures("pg2509").sina_kline == "PG2509"


def test_select_dominant_skips_summary_and_continuous_uses_oi_then_volume():
    picked = select_dominant_contract(_l1_rows())
    assert picked is not None
    assert picked["symbol"] == "MA2509"

    tied = [
        {"symbol": "MA2509", "name": "甲醇2509", "position": "10", "volume": "5"},
        {"symbol": "MA2510", "name": "甲醇2510", "position": "10", "volume": "9"},
        {"symbol": "MA0", "name": "连续", "position": "99", "volume": "99"},
        {"symbol": "XX", "name": "合计", "position": "99", "volume": "99"},
    ]
    assert select_dominant_contract(tied)["symbol"] == "MA2510"

    no_oi = [
        {"symbol": "MA2509", "name": "甲醇2509", "position": None, "volume": "3"},
        {"symbol": "MA2511", "name": "甲醇2511", "volume": "30"},
    ]
    assert select_dominant_contract(no_oi)["symbol"] == "MA2511"


def test_margin_formula_percent_vs_fraction_and_disclosure():
    a = calculate_theoretical_margin(price=100, multiplier=10, margin_rate=0.05, lots=2)
    b = calculate_theoretical_margin(price=100, multiplier=10, margin_rate=5, lots=2)
    assert a.status == STATUS_OK
    assert b.status == STATUS_OK
    assert a.margin == Decimal("100.00")
    assert b.margin == a.margin
    assert a.estimate_kind == "theoretical"
    assert "理论" in "".join(a.warnings)
    assert "期货公司" in "".join(a.warnings)

    missing = calculate_theoretical_margin(price=100, multiplier=None, margin_rate=0.08, lots=1)
    assert missing.status == STATUS_INVALID_REQUEST

    negative = calculate_theoretical_margin(price=-1, multiplier=10, margin_rate=0.08, lots=1)
    assert negative.status == STATUS_INVALID_REQUEST


def test_quote_and_l1_use_local_dominant_not_sina_continuous(tmp_path: Path):
    seen: list[str] = []

    def capturing_router(url: str, headers=None):
        seen.append(url)
        return _router(url, headers)

    p = PublicCNFuturesProvider(
        http_get=capturing_router,
        cache=MarketCache(root=tmp_path),
        clock=lambda: datetime(2026, 8, 18, 16, 0, tzinfo=timezone.utc),
    )
    quote = p.futures_quote("甲醇")
    assert quote.status == STATUS_OK
    assert quote.symbol == "MA2509.CZCE"
    assert quote.last == 2420.0
    assert quote.bid1 == 2419.0
    assert quote.ask1 == 2421.0
    assert quote.bid1_size == 30.0
    assert quote.ask1_size == 18.0
    assert quote.open_interest == 50000.0
    assert quote.market_depth == "L1"
    assert quote.market_depth != "L2"
    assert quote.series_method == "dominant_by_open_interest"
    assert quote.source.attempt <= 2
    assert "akshare" not in quote.to_dict()["source"]["provider"]
    assert any("node=zc_qh" in url for url in seen)
    assert not any("node=MA0" in url for url in seen)

    l1 = _provider(tmp_path).futures_l1("MA2505")
    assert l1.status == STATUS_OK
    assert l1.symbol == "MA2505.CZCE"
    assert l1.last == 2380.0
    assert l1.market_depth == "L1"


def test_daily_contract_ohlc_includes_oi_settle_and_chart_spec(tmp_path: Path):
    series = _provider(tmp_path).futures_daily("MA2509", chart_range="3mo", series="contract")
    assert series.status == STATUS_OK
    assert series.symbol == "MA2509.CZCE"
    assert series.series_method == "contract"
    assert series.adjustment == "none"
    assert len(series.labels) == 3
    assert series.ohlc[-1].c == 2420.0
    assert series.open_interest[-1] == 220000.0
    assert series.settlement[-1] == 2418.0
    spec = series.chart_spec()
    assert spec is not None
    assert spec["type"] == "candlestick"
    assert spec["ohlc"][-1]["c"] == 2420.0


def test_main_series_uses_dominant_contract_not_upstream_continuous(tmp_path: Path):
    series = _provider(tmp_path).futures_daily("甲醇", chart_range="3mo", series="main")
    assert series.status == STATUS_OK
    assert series.symbol == "MA2509.CZCE"
    assert series.series_method == "dominant_by_open_interest"
    assert series.ohlc[-1].c == 2420.0
    assert series.ohlc[-1].c != 9999.0
    assert series.dominant_contract[-1] == "MA2509"
    assert series.roll_count == 0
    assert any("未复权" in w or "none" in w for w in series.warnings)
    assert series.name == "甲醇"
    assert "甲醇" in series.aliases
    assert "郑醇" in series.aliases
    assert "甲醇" in series.to_dict()["aliases"]


def test_main_continuous_is_labelled_upstream_not_local_dominant(tmp_path: Path):
    series = _provider(tmp_path).futures_daily("MA", chart_range="3mo", series="main_continuous")
    assert series.status == STATUS_OK
    assert series.series_method == "upstream_sina_continuous"
    assert series.symbol.endswith(".CZCE")
    assert series.ohlc[-1].c == 9999.0
    assert any("upstream" in w.lower() or "新浪连续" in w for w in series.warnings)


def test_minute_maps_supported_intervals(tmp_path: Path):
    series = _provider(tmp_path).futures_minute("甲醇", interval="5m")
    assert series.status == STATUS_OK
    assert series.interval == "5m"
    assert series.symbol == "MA2509.CZCE"
    assert len(series.ohlc) == 2
    assert series.open_interest[-1] == 220000.0

    bad = _provider(tmp_path).futures_minute("MA2509", interval="2m")
    assert bad.status == STATUS_INVALID_REQUEST
    assert "1m" in (bad.error or "")


def test_invalid_product_and_range(tmp_path: Path):
    quote = _provider(tmp_path).futures_quote("不是品种")
    assert quote.status == STATUS_INVALID_SYMBOL
    bad = _provider(tmp_path).futures_daily("MA2509", chart_range="10y")
    assert bad.status == STATUS_INVALID_REQUEST


def test_daily_cache_hit(tmp_path: Path):
    p = _provider(tmp_path)
    first = p.futures_daily("MA2509", series="contract")
    assert first.source.cached is False
    second = p.futures_daily("MA2509", series="contract")
    assert second.status == STATUS_OK
    assert second.source.cached is True
    assert second.ohlc == first.ohlc


def test_tools_return_dicts_without_agent_wiring(tmp_path: Path):
    p = _provider(tmp_path)
    quote_tool = make_lookup_cn_futures_quote_tool(provider=p)
    ohlc_tool = make_lookup_cn_futures_ohlc_tool(provider=p)
    minute_tool = make_lookup_cn_futures_minute_tool(provider=p)
    l1_tool = make_lookup_cn_futures_l1_tool(provider=p)
    margin_tool = make_calculate_cn_futures_margin_tool(provider=p)

    q = quote_tool(symbol="甲醇")
    assert q["status"] == "ok"
    assert q["market_depth"] == "L1"
    assert q["last"] == 2420.0

    o = ohlc_tool(symbol="甲醇", range="3mo", series="main")
    assert o["chart_spec"]["type"] == "candlestick"
    assert o["series_method"] == "dominant_by_open_interest"

    m = minute_tool(symbol="MA2509", interval="5m")
    assert m["interval"] == "5m"

    l1 = l1_tool(symbol="甲醇")
    assert l1["bid1_size"] == 30.0

    margin = margin_tool(symbol="MA", lots=2, price=100, multiplier=10, margin_rate=0.08)
    assert margin["status"] == "ok"
    assert float(margin["margin"]) == 160.0
    assert margin["estimate_kind"] == "theoretical"

    assert quote_tool.__coworker_schema__["function"]["name"] == "lookup_cn_futures_quote"
    assert ohlc_tool.__coworker_schema__["function"]["name"] == "lookup_cn_futures_ohlc"
    assert l1_tool.__coworker_schema__["function"]["name"] == "lookup_cn_futures_l1"
    assert margin_tool.__coworker_schema__["function"]["name"] == "calculate_cn_futures_margin"
