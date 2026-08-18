"""Run 2: A-share quote/OHLC/minute/financials/features. Offline HTTP fixtures only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from coworker.cn_market.cache import MarketCache
from coworker.cn_market.models import (
    STATUS_INVALID_REQUEST,
    STATUS_INVALID_SYMBOL,
    STATUS_OK,
    STATUS_PARTIAL,
    STATUS_SOURCE_UNAVAILABLE,
    STATUS_UNSUPPORTED,
)
from coworker.cn_market.providers.stocks import PublicCNStockProvider
from coworker.cn_market.source_policy import policy_for
from coworker.cn_market.tools.stock_features import make_lookup_cn_stock_feature_tool
from coworker.cn_market.tools.stock_fundamentals import make_lookup_cn_stock_financials_tool
from coworker.cn_market.tools.stocks import (
    make_lookup_cn_stock_minute_tool,
    make_lookup_cn_stock_ohlc_tool,
    make_lookup_cn_stock_quote_tool,
)


def _jsonp(payload) -> bytes:
    return ("=(" + json.dumps(payload, ensure_ascii=False) + ");").encode("utf-8")


def _kline_bars():
    return [
        {
            "day": "2026-07-20",
            "open": "1400.00",
            "high": "1410.00",
            "low": "1390.00",
            "close": "1405.00",
            "volume": "1000",
            "amount": "1405000",
        },
        {
            "day": "2026-08-17",
            "open": "1410.00",
            "high": "1420.00",
            "low": "1408.00",
            "close": "1418.00",
            "volume": "1100",
            "amount": "1550000",
        },
        {
            "day": "2026-08-18",
            "open": "1418.00",
            "high": "1435.00",
            "low": "1415.00",
            "close": "1430.00",
            "volume": "1200",
            "amount": "1710000",
        },
    ]


def _finance_payload():
    return {
        "result": {
            "data": {
                "report_date": [
                    {"date_value": "20251231"},
                    {"date_value": "20260630"},
                ],
                "report_list": {
                    "20251231": {
                        "data": [
                            {"item_title": "货币资金", "item_value": "100"},
                            {"item_title": "资产总计", "item_value": "1000"},
                        ],
                        "data_source": "定期报告",
                        "is_audit": "1",
                        "publish_date": "20260331",
                        "rCurrency": "CNY",
                        "rType": "合并",
                        "update_time": 1710000000,
                    },
                    "20260630": {
                        "data": [
                            {"item_title": "货币资金", "item_value": "120"},
                            {"item_title": "资产总计", "item_value": "1100"},
                        ],
                        "data_source": "定期报告",
                        "is_audit": "0",
                        "publish_date": "20260820",
                        "rCurrency": "CNY",
                        "rType": "合并",
                        "update_time": 1720000000,
                    },
                },
            }
        }
    }


def _router(url: str, headers=None):
    if "hq.sinajs.cn" in url:
        body = (
            'var hq_str_sh600519="贵州茅台,1418.00,1410.00,1430.00,1435.00,1415.00,'
            '1429.00,1431.00,1200,1710000,10,1429.00,20,1431.00,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,'
            '2026-08-18,15:00:00,00,";\n'
        )
        return 200, body.encode("gbk")
    if "CN_MarketDataService.getKLineData" in url and "scale=240" in url:
        return 200, _jsonp(_kline_bars())
    if "CN_MarketDataService.getKLineData" in url and "scale=5" in url:
        bars = [
            {
                "day": "2026-08-18 14:55:00",
                "open": "1428.00",
                "high": "1431.00",
                "low": "1427.00",
                "close": "1430.00",
                "volume": "80",
            },
            {
                "day": "2026-08-18 15:00:00",
                "open": "1430.00",
                "high": "1432.00",
                "low": "1429.00",
                "close": "1431.00",
                "volume": "90",
            },
        ]
        return 200, _jsonp(bars)
    if "getFinanceReport2022" in url:
        return 200, json.dumps(_finance_payload()).encode("utf-8")
    if "RPT_DAILYBILLBOARD_DETAILSNEW" in url:
        payload = {
            "result": {
                "pages": 1,
                "data": [
                    {
                        "SECURITY_CODE": "600519",
                        "SECURITY_NAME_ABBR": "贵州茅台",
                        "TRADE_DATE": "2026-08-10",
                        "CLOSE_PRICE": 1410.0,
                        "CHANGE_RATE": 2.1,
                        "BILLBOARD_NET_AMT": 1.0,
                        "BILLBOARD_BUY_AMT": 5.0,
                        "BILLBOARD_SELL_AMT": 4.0,
                        "EXPLANATION": "涨幅偏离值达7%",
                    }
                ],
            }
        }
        return 200, json.dumps(payload).encode("utf-8")
    if "queryMargin.do" in url:
        payload = {
            "result": [
                {
                    "opDate": "20260814",
                    "rzye": 1354997636588,
                    "rzmre": 101595270337,
                    "rqyl": 2883001415,
                    "rqylje": 16563289961,
                    "rqmcl": 46915442,
                    "rzrqye": 1371560926549,
                }
            ]
        }
        return 200, json.dumps(payload).encode("utf-8")
    if "RPT_MUTUAL_DEAL_HISTORY" in url:
        payload = {
            "result": {
                "pages": 1,
                "data": [
                    {
                        "TRADE_DATE": "2026-08-11",
                        "NET_DEAL_AMT": None,
                        "BUY_AMT": None,
                        "SELL_AMT": None,
                        "FUND_INFLOW": None,
                        "LEAD_STOCKS_NAME": "金一文化",
                        "LS_CHANGE_RATE": 10.11,
                        "HOLD_MARKET_CAP": 0.0,
                    }
                ],
            }
        }
        return 200, json.dumps(payload).encode("utf-8")
    if "RPT_FCI_PERFORMANCEE" in url or "RPT_PUBLIC_OP_NEWPREDICT" in url:
        payload = {
            "result": {
                "pages": 1,
                "data": [
                    {
                        "SECURITY_CODE": "600519",
                        "SECURITY_NAME_ABBR": "贵州茅台",
                        "NOTICE_DATE": "2026-07-01",
                        "PREDICT_FINANCE": "归属于上市公司股东的净利润",
                    }
                ],
            }
        }
        return 200, json.dumps(payload).encode("utf-8")
    return 404, b"missing"


def _provider(tmp_path: Path) -> PublicCNStockProvider:
    return PublicCNStockProvider(
        http_get=_router,
        cache=MarketCache(root=tmp_path),
        clock=lambda: datetime(2026, 8, 18, 16, 0, tzinfo=timezone.utc),
    )


def test_quote_policy_uses_sina_not_eastmoney():
    policy = policy_for("stock_quote")
    assert policy.primary == "sina_hq"
    assert policy.keyless is True


def test_stock_quote_parses_sina_hq(tmp_path: Path):
    quote = _provider(tmp_path).stock_quote("贵州茅台")
    assert quote.status == STATUS_OK
    assert quote.symbol == "600519.SH"
    assert quote.name == "贵州茅台"
    assert quote.last == 1430.0
    assert quote.prev_close == 1410.0
    assert quote.bid1 == 1429.0
    assert quote.ask1 == 1431.0
    assert quote.change_pct is not None
    assert "akshare" not in quote.to_dict()["source"]["provider"]


def test_stock_daily_ohlc_and_chart_spec(tmp_path: Path):
    series = _provider(tmp_path).stock_daily("600519.SH", chart_range="3mo", adjustment="none")
    assert series.status == STATUS_OK
    assert len(series.labels) == 3
    assert series.ohlc[-1].c == 1430.0
    assert series.adjustment == "none"
    spec = series.chart_spec()
    assert spec is not None
    assert spec["type"] == "candlestick"
    assert spec["labels"] == series.labels
    assert spec["ohlc"][-1] == {"o": 1418.0, "h": 1435.0, "l": 1415.0, "c": 1430.0}


def test_stock_daily_rejects_unknown_range(tmp_path: Path):
    bad = _provider(tmp_path).stock_daily("600519", chart_range="10y", adjustment="none")
    assert bad.status == STATUS_INVALID_REQUEST


def test_stock_minute_ok(tmp_path: Path):
    series = _provider(tmp_path).stock_minute("sh600519", interval="5m")
    assert series.status == STATUS_OK
    assert series.interval == "5m"
    assert len(series.ohlc) == 2
    assert series.actual_range


def test_invalid_minute_interval(tmp_path: Path):
    series = _provider(tmp_path).stock_minute("600519", interval="2m")
    assert series.status == STATUS_INVALID_REQUEST


def test_financials_two_periods(tmp_path: Path):
    bundle = _provider(tmp_path).stock_financials("600519.SH", statement_type="balance_sheet")
    assert bundle.status in {STATUS_OK, STATUS_PARTIAL}
    assert len(bundle.statements) >= 2
    assert bundle.statements[0].statement_type == "balance_sheet"
    assert bundle.statements[0].report_kind in {"forecast", "express", "audited_report"}
    last = bundle.statements[-1]
    assert "货币资金" in last.fields or "货币资金" in last.raw_fields


def test_lhb_and_margin_and_northbound(tmp_path: Path):
    p = _provider(tmp_path)
    lhb = p.stock_feature("lhb_list", start_date="20260801", end_date="20260815")
    assert lhb.status == STATUS_OK
    assert lhb.dataset == "lhb_list"
    assert lhb.rows[0]["code"] == "600519"

    margin = p.stock_feature("margin_summary", start_date="20260801", end_date="20260815")
    assert margin.status == STATUS_OK
    assert margin.rows[0]["trade_date"] == "20260814"

    nb = p.stock_feature("northbound_history")
    assert nb.status == STATUS_PARTIAL
    assert nb.warnings

    hold = p.stock_feature("northbound_holdings")
    assert hold.status == STATUS_SOURCE_UNAVAILABLE


def test_unknown_feature_is_unsupported(tmp_path: Path):
    table = _provider(tmp_path).stock_feature("repurchase")
    assert table.status == STATUS_UNSUPPORTED


def test_tools_return_dicts_without_agent_wiring(tmp_path: Path):
    p = _provider(tmp_path)
    quote_tool = make_lookup_cn_stock_quote_tool(provider=p)
    ohlc_tool = make_lookup_cn_stock_ohlc_tool(provider=p)
    minute_tool = make_lookup_cn_stock_minute_tool(provider=p)
    fina_tool = make_lookup_cn_stock_financials_tool(provider=p)
    feat_tool = make_lookup_cn_stock_feature_tool(provider=p)

    q = quote_tool(symbol="600519")
    assert q["status"] == "ok"
    assert q["last"] == 1430.0

    o = ohlc_tool(symbol="600519", range="3mo", adjustment="none")
    assert o["chart_spec"]["type"] == "candlestick"
    assert o["status"] == "ok"

    m = minute_tool(symbol="600519", interval="5m")
    assert m["interval"] == "5m"

    f = fina_tool(symbol="600519", statement_type="balance_sheet")
    assert len(f["statements"]) >= 2

    feat = feat_tool(dataset="lhb_list", start_date="20260801", end_date="20260815")
    assert feat["dataset"] == "lhb_list"

    assert quote_tool.__coworker_schema__["function"]["name"] == "lookup_cn_stock_quote"
    assert ohlc_tool.__coworker_schema__["function"]["name"] == "lookup_cn_stock_ohlc"


def test_invalid_symbol_on_quote(tmp_path: Path):
    quote = _provider(tmp_path).stock_quote("!!!!")
    assert quote.status == STATUS_INVALID_SYMBOL
