from coworker.reports import MarketSeriesAggregator


def test_market_series_aggregator_returns_bounded_summary_and_chart() -> None:
    raw = {
        "source_refs": ["chem-data-hub"],
        "prices": [
            {"date": "2026-08-26", "price": 6000, "region": "山东", "spec": "民用气"},
            {"date": "2026-09-02", "price": 6300, "region": "山东", "spec": "民用气"},
            {"date": "2026-09-02", "price": 6400, "region": "华南", "spec": "民用气"},
        ],
    }
    summary = MarketSeriesAggregator.summarize(raw, product_name="液化石油气")
    assert summary.product_name == "液化石油气"
    assert summary.observations == 3
    assert summary.start_date == "2026-08-26"
    assert any(item["price"] == 6300 for item in summary.latest)
    assert any(item["change_pct"] == 5.0 for item in summary.weekly_change)
    assert summary.chart_spec is not None
    assert summary.chart_spec["labels"]
    assert summary.chart_spec["series"][0]["values"]
    assert summary.source_refs == ("chem-data-hub",)


def test_market_series_aggregator_does_not_leak_unparseable_large_payload() -> None:
    summary = MarketSeriesAggregator.summarize({"data": "x" * 300_000})
    assert summary.observations == 0
    assert summary.chart_spec is None
    assert summary.data_gaps


def test_multiple_regions_align_without_filling_missing_quotes():
    summary = MarketSeriesAggregator.summarize({"data": [
        {"date": "2026-09-28", "price": 2000, "region": "山东", "unit": "元/吨"},
        {"date": "2026-09-29", "price": 2100, "region": "山东", "unit": "元/吨"},
        {"date": "2026-09-29", "price": 2050, "region": "华南", "unit": "元/吨"},
    ]})
    assert summary.chart_spec["labels"] == ["2026-09-28", "2026-09-29"]
    assert {s["name"]: s["values"] for s in summary.chart_spec["series"]} == {
        "华南｜现货": [None, 2050], "山东｜现货": [2000, 2100]}


def test_different_units_are_never_joined_into_a_single_curve():
    summary = MarketSeriesAggregator.summarize({"data": [
        {"date": "2026-09-28", "price": 2, "unit": "元/公斤"},
        {"date": "2026-09-29", "price": 2100, "unit": "元/吨"},
    ]})
    assert len(summary.latest) == 2 and summary.data_gaps
    assert len(summary.chart_spec["series"]) == 1
