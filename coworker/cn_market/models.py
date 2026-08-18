"""Normalized result contracts for CN market data."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_STALE_CACHE = "stale_cache"
STATUS_UNSUPPORTED = "unsupported"
STATUS_UNSUPPORTED_KEYLESS = "unsupported_keyless"
STATUS_SOURCE_UNAVAILABLE = "source_unavailable"
STATUS_INVALID_SYMBOL = "invalid_symbol"
STATUS_INVALID_REQUEST = "invalid_request"

STATEMENT_BALANCE_SHEET = "balance_sheet"
STATEMENT_INCOME = "income_statement"
STATEMENT_CASH_FLOW = "cash_flow"
STATEMENT_INDICATORS = "financial_indicators"
STATEMENT_EXPRESS = "performance_express"
STATEMENT_FORECAST = "performance_forecast"

REPORT_KIND_FORECAST = "forecast"
REPORT_KIND_EXPRESS = "express"
REPORT_KIND_AUDITED = "audited_report"


@dataclass(frozen=True)
class SourceMeta:
    provider: str
    upstream: str
    cached: bool
    fetched_at: Optional[str] = None
    attempt: int = 1
    source_version: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "upstream": self.upstream,
            "cached": self.cached,
            "fetched_at": self.fetched_at,
            "attempt": self.attempt,
            "source_version": self.source_version,
        }


@dataclass
class MarketResult:
    status: str
    source: SourceMeta
    as_of: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source.to_dict(),
            "as_of": self.as_of,
            "warnings": list(self.warnings),
            "error": self.error,
        }


@dataclass(frozen=True)
class OhlcBar:
    o: float
    h: float
    l: float
    c: float

    def to_dict(self) -> dict[str, float]:
        return {"o": self.o, "h": self.h, "l": self.l, "c": self.c}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "OhlcBar":
        return cls(o=float(raw["o"]), h=float(raw["h"]), l=float(raw["l"]), c=float(raw["c"]))


@dataclass
class OhlcSeries(MarketResult):
    labels: list[str] = field(default_factory=list)
    ohlc: list[OhlcBar] = field(default_factory=list)
    volume: list[Optional[float]] = field(default_factory=list)
    amount: list[Optional[float]] = field(default_factory=list)
    turnover: list[Optional[float]] = field(default_factory=list)
    open_interest: list[Optional[float]] = field(default_factory=list)
    settlement: list[Optional[float]] = field(default_factory=list)
    dominant_contract: list[Optional[str]] = field(default_factory=list)
    adjustment: Optional[str] = None
    symbol: Optional[str] = None
    interval: Optional[str] = None
    actual_range: Optional[str] = None
    series_method: Optional[str] = None
    roll_count: Optional[int] = None
    name: Optional[str] = None
    aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "symbol": self.symbol,
                "interval": self.interval,
                "actual_range": self.actual_range,
                "labels": list(self.labels),
                "ohlc": [bar.to_dict() for bar in self.ohlc],
                "volume": list(self.volume),
                "amount": list(self.amount),
                "turnover": list(self.turnover),
                "open_interest": list(self.open_interest),
                "settlement": list(self.settlement),
                "dominant_contract": list(self.dominant_contract),
                "adjustment": self.adjustment,
                "series_method": self.series_method,
                "roll_count": self.roll_count,
                "name": self.name,
                "aliases": list(self.aliases),
                "chart_spec": self.chart_spec(),
            }
        )
        return payload

    def chart_spec(self) -> Optional[dict[str, Any]]:
        from .charting import ohlc_chart_spec

        return ohlc_chart_spec(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, cached: Optional[bool] = None) -> "OhlcSeries":
        src = raw.get("source") or {}
        cached_flag = src.get("cached") if cached is None else cached
        source = SourceMeta(
            provider=str(src.get("provider") or "unknown"),
            upstream=str(src.get("upstream") or ""),
            cached=bool(cached_flag),
            fetched_at=src.get("fetched_at"),
            attempt=int(src.get("attempt") or 1),
            source_version=src.get("source_version"),
        )
        ohlc_raw = raw.get("ohlc") or []
        return cls(
            status=str(raw.get("status") or STATUS_OK),
            source=source,
            as_of=raw.get("as_of"),
            warnings=list(raw.get("warnings") or []),
            error=raw.get("error"),
            labels=list(raw.get("labels") or []),
            ohlc=[OhlcBar.from_dict(x) for x in ohlc_raw],
            volume=list(raw.get("volume") or []),
            amount=list(raw.get("amount") or []),
            turnover=list(raw.get("turnover") or []),
            open_interest=list(raw.get("open_interest") or []),
            settlement=list(raw.get("settlement") or []),
            dominant_contract=list(raw.get("dominant_contract") or []),
            adjustment=raw.get("adjustment"),
            symbol=raw.get("symbol"),
            interval=raw.get("interval"),
            actual_range=raw.get("actual_range"),
            series_method=raw.get("series_method"),
            roll_count=raw.get("roll_count"),
            name=raw.get("name") if isinstance(raw.get("name"), str) else None,
            aliases=[
                str(item).strip()
                for item in (raw.get("aliases") or [])
                if isinstance(item, str) and item.strip()
            ],
        )


@dataclass
class FinancialStatement(MarketResult):
    symbol: Optional[str] = None
    report_period: Optional[str] = None
    publish_date: Optional[str] = None
    statement_type: Optional[str] = None
    report_kind: Optional[str] = None
    currency: Optional[str] = None
    fields: dict[str, Any] = field(default_factory=dict)
    raw_fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "symbol": self.symbol,
                "report_period": self.report_period,
                "publish_date": self.publish_date,
                "statement_type": self.statement_type,
                "report_kind": self.report_kind,
                "currency": self.currency,
                "fields": dict(self.fields),
                "raw_fields": dict(self.raw_fields),
            }
        )
        return payload


@dataclass
class FinancialBundle(MarketResult):
    symbol: Optional[str] = None
    statement_type: Optional[str] = None
    statements: list[FinancialStatement] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "symbol": self.symbol,
                "statement_type": self.statement_type,
                "statements": [item.to_dict() for item in self.statements],
            }
        )
        return payload


@dataclass
class StockQuote(MarketResult):
    symbol: Optional[str] = None
    name: Optional[str] = None
    last: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    bid1: Optional[float] = None
    ask1: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "symbol": self.symbol,
                "name": self.name,
                "last": self.last,
                "open": self.open,
                "high": self.high,
                "low": self.low,
                "prev_close": self.prev_close,
                "change": self.change,
                "change_pct": self.change_pct,
                "volume": self.volume,
                "amount": self.amount,
                "bid1": self.bid1,
                "ask1": self.ask1,
            }
        )
        return payload


@dataclass
class FeatureTable(MarketResult):
    dataset: str = ""
    symbol: Optional[str] = None
    rows: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "dataset": self.dataset,
                "symbol": self.symbol,
                "rows": [dict(row) for row in self.rows],
            }
        )
        return payload


@dataclass
class FuturesQuote(MarketResult):
    symbol: Optional[str] = None
    name: Optional[str] = None
    product: Optional[str] = None
    exchange: Optional[str] = None
    last: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_settle: Optional[float] = None
    settle: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    open_interest: Optional[float] = None
    bid1: Optional[float] = None
    bid1_size: Optional[float] = None
    ask1: Optional[float] = None
    ask1_size: Optional[float] = None
    market_depth: str = "L1"
    series_method: Optional[str] = None
    contract_multiplier: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "symbol": self.symbol,
                "name": self.name,
                "product": self.product,
                "exchange": self.exchange,
                "last": self.last,
                "open": self.open,
                "high": self.high,
                "low": self.low,
                "prev_settle": self.prev_settle,
                "settle": self.settle,
                "change": self.change,
                "change_pct": self.change_pct,
                "volume": self.volume,
                "open_interest": self.open_interest,
                "bid1": self.bid1,
                "bid1_size": self.bid1_size,
                "ask1": self.ask1,
                "ask1_size": self.ask1_size,
                "market_depth": self.market_depth,
                "series_method": self.series_method,
                "contract_multiplier": self.contract_multiplier,
            }
        )
        return payload


@dataclass
class MarginEstimate(MarketResult):
    price: Optional[float] = None
    multiplier: Optional[float] = None
    margin_rate: Optional[float] = None
    lots: Optional[float] = None
    margin: Optional[Decimal] = None
    currency: str = "CNY"
    formula: str = "price × multiplier × margin_rate × lots"
    estimate_kind: str = "theoretical"
    symbol: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "symbol": self.symbol,
                "price": self.price,
                "multiplier": self.multiplier,
                "margin_rate": self.margin_rate,
                "lots": self.lots,
                "margin": str(self.margin) if self.margin is not None else None,
                "currency": self.currency,
                "formula": self.formula,
                "estimate_kind": self.estimate_kind,
            }
        )
        return payload


@dataclass
class OptionQuote(MarketResult):
    symbol: Optional[str] = None
    name: Optional[str] = None
    underlying: Optional[str] = None
    exchange: Optional[str] = None
    option_type: Optional[str] = None
    strike: Optional[float] = None
    expiry: Optional[str] = None
    last: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    open_interest: Optional[float] = None
    bid1: Optional[float] = None
    bid1_size: Optional[float] = None
    ask1: Optional[float] = None
    ask1_size: Optional[float] = None
    greeks_source: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "symbol": self.symbol,
                "name": self.name,
                "underlying": self.underlying,
                "exchange": self.exchange,
                "option_type": self.option_type,
                "strike": self.strike,
                "expiry": self.expiry,
                "last": self.last,
                "open": self.open,
                "high": self.high,
                "low": self.low,
                "prev_close": self.prev_close,
                "change_pct": self.change_pct,
                "volume": self.volume,
                "amount": self.amount,
                "open_interest": self.open_interest,
                "bid1": self.bid1,
                "bid1_size": self.bid1_size,
                "ask1": self.ask1,
                "ask1_size": self.ask1_size,
                "greeks_source": self.greeks_source,
            }
        )
        return payload


@dataclass
class OptionGreeks(MarketResult):
    symbol: Optional[str] = None
    name: Optional[str] = None
    trade_code: Optional[str] = None
    strike: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    implied_vol: Optional[float] = None
    theoretical: Optional[float] = None
    greeks_source: str = "upstream"

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "symbol": self.symbol,
                "name": self.name,
                "trade_code": self.trade_code,
                "strike": self.strike,
                "last": self.last,
                "volume": self.volume,
                "delta": self.delta,
                "gamma": self.gamma,
                "theta": self.theta,
                "vega": self.vega,
                "implied_vol": self.implied_vol,
                "theoretical": self.theoretical,
                "greeks_source": self.greeks_source,
            }
        )
        return payload
