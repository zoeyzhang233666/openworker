"""Run 1: CN market contracts, cache, symbols, calendar, fake providers.

Unit tests must not touch the network, user state_dir, or the repo workspace cache.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from coworker.cn_market.calendar import TradeCalendar
from coworker.cn_market.cache import CacheKey, MarketCache, ttl_for
from coworker.cn_market.errors import InvalidSymbolError, UnsupportedKeylessError
from coworker.cn_market.models import (
    OhlcBar,
    OhlcSeries,
    SourceMeta,
    STATUS_INVALID_SYMBOL,
    STATUS_OK,
    STATUS_STALE_CACHE,
    STATUS_UNSUPPORTED_KEYLESS,
)
from coworker.cn_market.providers.fake import FakeCNMarketProvider
from coworker.cn_market.source_policy import (
    FORBIDDEN_RUNTIME_FALLBACKS,
    MAX_PROVIDER_ATTEMPTS,
    assert_attempt_allowed,
    policy_for,
)
from coworker.cn_market.symbols import (
    resolve_futures,
    resolve_stock,
)
from coworker.secrets import state_dir


def test_stock_symbol_normalizes_code_and_prefixed_forms():
    a = resolve_stock("600519")
    assert a.code == "600519"
    assert a.exchange == "SH"
    assert a.canonical == "600519.SH"

    b = resolve_stock("600519.SH")
    assert b.canonical == "600519.SH"
    assert resolve_stock("sh600519").canonical == "600519.SH"
    assert resolve_stock("000001.SZ").canonical == "000001.SZ"
    assert resolve_stock("sz000001").canonical == "000001.SZ"


def test_stock_symbol_resolves_chinese_name_from_master_not_llm():
    resolved = resolve_stock("贵州茅台")
    assert resolved.canonical == "600519.SH"
    assert resolved.name == "贵州茅台"

    ping_an = resolve_stock("平安银行")
    assert ping_an.canonical == "000001.SZ"


def test_stock_symbol_rejects_garbage():
    with pytest.raises(InvalidSymbolError):
        resolve_stock("not-a-stock!!")
    with pytest.raises(InvalidSymbolError):
        resolve_stock("")


def test_futures_symbol_resolves_chemical_aliases_deterministically():
    methanol = resolve_futures("甲醇")
    assert methanol.product == "MA"
    assert methanol.exchange == "CZCE"
    assert methanol.contract is None

    by_code = resolve_futures("MA")
    assert by_code.product == "MA"
    assert by_code.exchange == "CZCE"

    contract = resolve_futures("MA2509")
    assert contract.product == "MA"
    assert contract.contract == "MA2509"
    assert contract.exchange == "CZCE"

    lpg = resolve_futures("液化气")
    assert lpg.product == "PG"
    assert lpg.exchange == "DCE"
    assert resolve_futures("郑醇").product == "MA"

    ru = resolve_futures("橡胶")
    assert ru.product == "RU"
    assert ru.name == "天然橡胶"
    assert "橡胶" in ru.aliases
    assert "天然橡胶" in ru.aliases


def test_futures_symbol_rejects_unknown_product():
    with pytest.raises(InvalidSymbolError):
        resolve_futures("不是品种")


def test_trade_calendar_previous_and_latest_are_deterministic():
    holidays = {date(2026, 8, 17)}  # Monday holiday fixture
    cal = TradeCalendar(
        holidays=holidays,
        clock=lambda: datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc),
    )
    assert cal.is_trading_day(date(2026, 8, 18)) is True
    assert cal.is_trading_day(date(2026, 8, 16)) is False  # Sunday
    assert cal.is_trading_day(date(2026, 8, 17)) is False  # holiday
    assert cal.previous_trade_date(date(2026, 8, 18)) == date(2026, 8, 14)
    assert cal.latest_trade_date() == date(2026, 8, 18)


def test_cache_roundtrip_and_ttl_with_injected_root(tmp_path: Path):
    clock = {"now": datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc)}

    def now():
        return clock["now"]

    cache = MarketCache(root=tmp_path, clock=now)
    key = CacheKey(
        domain="stock",
        symbol="600519.SH",
        dataset="daily",
        interval="1d",
        adjustment="qfq",
        source_version="sina-1",
    )
    cache.put(key, {"labels": ["2026-08-18"], "c": [1400.0]}, dataset_kind="daily")
    hit = cache.get(key)
    assert hit is not None
    assert hit.fresh is True
    assert hit.payload["c"] == [1400.0]

    clock["now"] = now() + timedelta(days=30)
    stale = cache.get(key)
    assert stale is not None
    assert stale.fresh is False


def test_cache_default_root_is_state_dir_not_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COWORKER_STATE_DIR", str(tmp_path / "state"))
    cache = MarketCache()
    root = cache.root.resolve()
    assert root == (state_dir() / "cn_market" / "cache").resolve()
    repo = Path(__file__).resolve().parents[1]
    assert root != (repo / "cn_market").resolve()
    assert root != (repo / "cn_market" / "cache").resolve()
    assert not (repo / "cn_market").exists()


def test_cache_put_does_not_write_into_repo_workspace(tmp_path: Path):
    repo = Path(__file__).resolve().parents[1]
    before = {p.name for p in repo.iterdir()}
    cache = MarketCache(root=tmp_path / "cache")
    cache.put(
        CacheKey(domain="stock", symbol="000001.SZ", dataset="daily"),
        {"ok": True},
        dataset_kind="daily",
    )
    after = {p.name for p in repo.iterdir()}
    assert after == before
    assert not (repo / "cn_market").exists()
    assert list((tmp_path / "cache").rglob("*.json"))


def test_ttl_kinds_are_ordered_quote_shorter_than_daily():
    assert ttl_for("quote") < ttl_for("minute") < ttl_for("daily") < ttl_for("statement")
    assert ttl_for("calendar") >= ttl_for("daily")


def test_source_policy_caps_attempts_and_forbids_runtime_web_shell():
    assert MAX_PROVIDER_ATTEMPTS == 2
    assert "web_search" in FORBIDDEN_RUNTIME_FALLBACKS
    assert "curl" in FORBIDDEN_RUNTIME_FALLBACKS
    assert "shell" in FORBIDDEN_RUNTIME_FALLBACKS
    policy = policy_for("stock_daily")
    assert policy.keyless is True
    assert policy.fallback is None or policy.fallback != policy.primary
    assert_attempt_allowed(1)
    assert_attempt_allowed(2)
    with pytest.raises(ValueError):
        assert_attempt_allowed(3)


def test_tick_l2_is_unsupported_keyless_in_policy():
    policy = policy_for("tick_l2")
    assert policy.capability_status == STATUS_UNSUPPORTED_KEYLESS
    assert policy.keyless is False


def test_ohlc_series_contract_and_to_dict():
    series = OhlcSeries(
        status=STATUS_OK,
        source=SourceMeta(
            provider="fake",
            upstream="fixture",
            cached=False,
            fetched_at="2026-08-18T10:00:00+00:00",
        ),
        as_of="2026-08-18",
        warnings=["fixture only"],
        error=None,
        labels=["2026-08-17", "2026-08-18"],
        ohlc=[OhlcBar(o=10.0, h=11.0, l=9.5, c=10.6), OhlcBar(o=10.6, h=11.2, l=10.4, c=11.0)],
        volume=[100.0, 110.0],
        amount=[1000.0, 1100.0],
        adjustment="qfq",
    )
    payload = series.to_dict()
    assert payload["status"] == "ok"
    assert payload["ohlc"][0] == {"o": 10.0, "h": 11.0, "l": 9.5, "c": 10.6}
    assert payload["adjustment"] == "qfq"
    assert payload["source"]["provider"] == "fake"
    assert payload["source"]["cached"] is False
    assert "akshare" not in str(payload).lower()


def test_ohlc_series_roundtrips_name_and_aliases():
    series = OhlcSeries(
        status=STATUS_OK,
        source=SourceMeta(
            provider="fake",
            upstream="fixture",
            cached=False,
            fetched_at="2026-08-18T10:00:00+00:00",
        ),
        labels=["2026-08-17", "2026-08-18"],
        ohlc=[OhlcBar(o=10.0, h=11.0, l=9.5, c=10.6), OhlcBar(o=10.6, h=11.2, l=10.4, c=11.0)],
        symbol="RU.SHFE",
        name="天然橡胶",
        aliases=["天然橡胶", "橡胶"],
    )
    payload = series.to_dict()
    assert payload["name"] == "天然橡胶"
    assert payload["aliases"] == ["天然橡胶", "橡胶"]
    roundtrip = OhlcSeries.from_dict(payload)
    assert roundtrip.name == "天然橡胶"
    assert roundtrip.aliases == ["天然橡胶", "橡胶"]


def test_fake_provider_stock_daily_is_offline_and_uses_cache(tmp_path: Path):
    cache = MarketCache(root=tmp_path)
    provider = FakeCNMarketProvider(cache=cache)
    first = provider.stock_daily("贵州茅台", chart_range="1mo", adjustment="qfq")
    assert first.status == STATUS_OK
    assert first.symbol == "600519.SH"
    assert len(first.labels) >= 2
    assert len(first.labels) == len(first.ohlc)
    assert first.source.cached is False
    assert first.adjustment == "qfq"

    second = provider.stock_daily("600519.SH", chart_range="1mo", adjustment="qfq")
    assert second.status == STATUS_OK
    assert second.source.cached is True
    assert second.ohlc == first.ohlc


def test_fake_provider_invalid_symbol_status(tmp_path: Path):
    provider = FakeCNMarketProvider(cache=MarketCache(root=tmp_path))
    result = provider.stock_daily("!!!!")
    assert result.status == STATUS_INVALID_SYMBOL
    assert result.error


def test_fake_provider_tick_l2_is_unsupported_keyless():
    provider = FakeCNMarketProvider()
    result = provider.tick_l2("000001.SZ")
    assert result.status == STATUS_UNSUPPORTED_KEYLESS
    with pytest.raises(UnsupportedKeylessError):
        raise UnsupportedKeylessError("tick_l2")


def test_fake_provider_can_serve_stale_cache(tmp_path: Path):
    clock = {"now": datetime(2026, 8, 18, tzinfo=timezone.utc)}
    cache = MarketCache(root=tmp_path, clock=lambda: clock["now"])
    provider = FakeCNMarketProvider(cache=cache, clock=lambda: clock["now"])
    warm = provider.stock_daily("600519", chart_range="1mo", adjustment="none")
    assert warm.source.cached is False
    clock["now"] = clock["now"] + timedelta(days=60)
    stale = provider.stock_daily("600519", chart_range="1mo", adjustment="none")
    assert stale.status == STATUS_STALE_CACHE
    assert stale.source.cached is True
    assert stale.labels == warm.labels
