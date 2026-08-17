"""Tests for unofficial Yahoo chart OHLC provider/tool."""

from __future__ import annotations

import json

from coworker.yahoo_finance.providers import YahooChartProvider
from coworker.yahoo_finance.tool import make_lookup_yahoo_ohlc_tool


def _sample_payload() -> dict:
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                        "symbol": "CL=F",
                        "instrumentType": "FUTURE",
                        "shortName": "Crude Oil",
                    },
                    "timestamp": [1718582400, 1718668800, 1718755200],
                    "indicators": {
                        "quote": [
                            {
                                "open": [80.0, 81.0, None],
                                "high": [82.0, 83.0, 84.0],
                                "low": [79.0, 80.0, 81.0],
                                "close": [81.5, 82.5, 83.0],
                                "volume": [1000, 2000, 3000],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


def test_yahoo_provider_parses_ohlc_fixture():
    payload = _sample_payload()

    def http_get(url, headers=None):
        assert "CL%3DF" in url or "CL=F" in url or "CL" in url
        return 200, json.dumps(payload).encode("utf-8")

    p = YahooChartProvider(http_get=http_get)
    result = p.lookup(symbol="CL=F", chart_range="3mo", interval="1d")
    assert result.status == "ok"
    assert result.symbol == "CL=F"
    assert len(result.ohlc) == 2  # third bar skipped (open null)
    assert result.ohlc[0]["o"] == 80.0
    assert result.ohlc[0]["c"] == 81.5
    assert len(result.labels) == 2
    assert "not licensed" in result.warnings[0].lower() or "Unofficial" in result.warnings[0]


def test_yahoo_provider_rejects_bad_symbol():
    p = YahooChartProvider(http_get=lambda *a, **k: (200, b"{}"))
    result = p.lookup(symbol="bad symbol!!")
    assert result.status == "error"


def test_lookup_yahoo_ohlc_tool_ok():
    payload = _sample_payload()

    def http_get(url, headers=None):
        return 200, json.dumps(payload).encode("utf-8")

    tool = make_lookup_yahoo_ohlc_tool(provider=YahooChartProvider(http_get=http_get))
    out = tool(symbol="CL=F")
    assert out["status"] == "ok"
    assert out["ohlc"][0]["h"] == 82.0
    assert tool.__coworker_schema__["function"]["name"] == "lookup_yahoo_ohlc"
    assert out["chart_spec"] is not None
    assert out["chart_spec"]["type"] == "candlestick"
    assert out["chart_spec"]["labels"] == out["labels"]
    assert out["chart_spec"]["ohlc"] == out["ohlc"]
    assert len(out["chart_spec"]["labels"]) == len(out["chart_spec"]["ohlc"])


def test_yahoo_error_has_null_chart_spec():
    p = YahooChartProvider(http_get=lambda *a, **k: (200, b"{}"))
    result = p.lookup(symbol="bad symbol!!")
    assert result.to_dict()["chart_spec"] is None
