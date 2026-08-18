"""Deterministic CN stock / futures symbol resolvers. No LLM, no web."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from .errors import InvalidSymbolError

_STOCK_PREFIX = re.compile(
    r"^(?:(?P<prefix>sh|sz|bj))?(?P<code>\d{6})(?:\.(?P<suffix>SH|SZ|BJ))?$",
    re.IGNORECASE,
)

DEFAULT_STOCK_NAMES: dict[str, str] = {
    "贵州茅台": "600519",
    "茅台": "600519",
    "平安银行": "000001",
}


@dataclass(frozen=True)
class CNStockSymbol:
    code: str
    exchange: str
    canonical: str
    name: Optional[str] = None

    @property
    def sina_code(self) -> str:
        return f"{self.exchange.lower()}{self.code}"


def sina_futures_code(product: str, exchange: str, suffix: str) -> str:
    """Sina kline codes use the listed contract form (MA0, PG0, MA2509)."""
    _ = exchange
    return f"{product.upper()}{suffix}"


@dataclass(frozen=True)
class CNFuturesSymbol:
    product: str
    exchange: str
    name: str
    contract: Optional[str] = None
    sina_l1_node: str = ""
    aliases: tuple[str, ...] = ()

    @property
    def sina_node(self) -> str:
        return self.sina_l1_node or sina_futures_code(self.product, self.exchange, "0")

    @property
    def sina_continuous(self) -> str:
        return sina_futures_code(self.product, self.exchange, "0")

    @property
    def sina_kline(self) -> str:
        if self.contract:
            digits = re.sub(r"^[A-Za-z]+", "", self.contract)
            return sina_futures_code(self.product, self.exchange, digits)
        return self.sina_continuous

    @property
    def canonical(self) -> str:
        code = self.contract or self.product
        return f"{code}.{self.exchange}"


@dataclass(frozen=True)
class _FuturesProduct:
    product: str
    exchange: str
    name: str
    aliases: tuple[str, ...]
    sina_l1_node: str


# ChemClaw chemical / adjacent high-frequency products (plan §12.1).
# sina_l1_node is the Sina Market_Center node from qihuohangqing.js (not MA0/pg0).
_FUTURES_PRODUCTS: tuple[_FuturesProduct, ...] = (
    _FuturesProduct("PG", "DCE", "液化石油气", ("液化石油气", "液化气", "LPG"), "pg_qh"),
    _FuturesProduct("MA", "CZCE", "甲醇", ("甲醇", "郑醇"), "zc_qh"),
    _FuturesProduct("EB", "DCE", "苯乙烯", ("苯乙烯",), "byx_qh"),
    _FuturesProduct("PP", "DCE", "聚丙烯", ("聚丙烯",), "jbx_qh"),
    _FuturesProduct("L", "DCE", "聚乙烯", ("聚乙烯", "塑料"), "lldpe_qh"),
    _FuturesProduct("V", "DCE", "PVC", ("PVC", "聚氯乙烯"), "pvc_qh"),
    _FuturesProduct("EG", "DCE", "乙二醇", ("乙二醇",), "yec_qh"),
    _FuturesProduct("SA", "CZCE", "纯碱", ("纯碱",), "cj_qh"),
    _FuturesProduct("UR", "CZCE", "尿素", ("尿素",), "ns_qh"),
    _FuturesProduct("SC", "INE", "原油", ("原油",), "yy_qh"),
    _FuturesProduct("FU", "SHFE", "燃料油", ("燃料油", "燃油"), "ry_qh"),
    _FuturesProduct("BU", "SHFE", "沥青", ("沥青",), "lq_qh"),
    _FuturesProduct("RU", "SHFE", "天然橡胶", ("天然橡胶", "橡胶"), "xj_qh"),
    _FuturesProduct("BR", "SHFE", "丁二烯橡胶", ("丁二烯橡胶",), "br_qh"),
    _FuturesProduct("TA", "CZCE", "PTA", ("PTA",), "pta_qh"),
    _FuturesProduct("PF", "CZCE", "短纤", ("短纤",), "pf_qh"),
    _FuturesProduct("PX", "CZCE", "对二甲苯", ("对二甲苯", "PX", "二甲苯"), "px_qh"),
    _FuturesProduct("SH", "CZCE", "烧碱", ("烧碱",), "sh_qh"),
    _FuturesProduct("FG", "CZCE", "玻璃", ("玻璃",), "bl_qh"),
    _FuturesProduct("SI", "GFEX", "工业硅", ("工业硅",), "si_qh"),
    _FuturesProduct("LC", "GFEX", "碳酸锂", ("碳酸锂",), "lc_qh"),
)

_CONTRACT_RE = re.compile(r"^([A-Za-z]{1,2})(\d{3,4})$")


def _exchange_for_code(code: str) -> str:
    if code.startswith(("600", "601", "603", "605", "688", "689", "510", "511", "512", "513", "518", "588", "900")):
        return "SH"
    if code.startswith(("000", "001", "002", "003", "300", "301", "159", "399", "200")):
        return "SZ"
    if code.startswith(("4", "8", "92")):
        return "BJ"
    raise InvalidSymbolError(f"无法识别交易所: {code}")


def resolve_stock(
    query: str,
    *,
    name_master: Optional[Mapping[str, str]] = None,
) -> CNStockSymbol:
    raw = (query or "").strip()
    if not raw:
        raise InvalidSymbolError("股票代码为空")

    master = dict(DEFAULT_STOCK_NAMES)
    if name_master:
        master.update(name_master)
    if raw in master:
        code = master[raw]
        exchange = _exchange_for_code(code)
        return CNStockSymbol(code=code, exchange=exchange, canonical=f"{code}.{exchange}", name=raw)

    match = _STOCK_PREFIX.fullmatch(raw)
    if not match:
        raise InvalidSymbolError(f"无效股票代码: {query}")
    code = match.group("code")
    prefix = (match.group("prefix") or "").upper()
    suffix = (match.group("suffix") or "").upper()
    if suffix:
        exchange = suffix
    elif prefix:
        exchange = prefix
    else:
        exchange = _exchange_for_code(code)
    name = None
    for n, c in master.items():
        if c == code:
            name = n
            break
    return CNStockSymbol(code=code, exchange=exchange, canonical=f"{code}.{exchange}", name=name)


def _futures_index() -> dict[str, _FuturesProduct]:
    idx: dict[str, _FuturesProduct] = {}
    for product in _FUTURES_PRODUCTS:
        idx[product.product.upper()] = product
        idx[product.name] = product
        for alias in product.aliases:
            idx[alias.upper()] = product
            idx[alias] = product
    return idx


_FUTURES_INDEX = _futures_index()


def resolve_futures(query: str) -> CNFuturesSymbol:
    raw = (query or "").strip()
    if not raw:
        raise InvalidSymbolError("期货品种为空")

    contract_match = _CONTRACT_RE.fullmatch(raw)
    if contract_match:
        product_code = contract_match.group(1).upper()
        product = _FUTURES_INDEX.get(product_code)
        if product is None:
            raise InvalidSymbolError(f"未知期货品种: {query}")
        contract = f"{product.product}{contract_match.group(2)}"
        return CNFuturesSymbol(
            product=product.product,
            exchange=product.exchange,
            name=product.name,
            contract=contract,
            sina_l1_node=product.sina_l1_node,
            aliases=product.aliases,
        )

    product = _FUTURES_INDEX.get(raw) or _FUTURES_INDEX.get(raw.upper())
    if product is None:
        raise InvalidSymbolError(f"未知期货品种: {query}")
    return CNFuturesSymbol(
        product=product.product,
        exchange=product.exchange,
        name=product.name,
        contract=None,
        sina_l1_node=product.sina_l1_node,
        aliases=product.aliases,
    )


@dataclass(frozen=True)
class CNOptionUnderlying:
    code: str
    exchange: str
    name: str
    sina_cate: str
    cffex_product: Optional[str] = None


_OPTION_UNDERLYINGS: tuple[CNOptionUnderlying, ...] = (
    CNOptionUnderlying("510050", "SSE", "上证50ETF", "50ETF"),
    CNOptionUnderlying("510300", "SSE", "沪深300ETF", "300ETF"),
    CNOptionUnderlying("510500", "SSE", "中证500ETF", "500ETF"),
    CNOptionUnderlying("588000", "SSE", "科创50ETF", "科创50ETF"),
    CNOptionUnderlying("IO", "CFFEX", "沪深300股指期权", "IO", "io"),
    CNOptionUnderlying("HO", "CFFEX", "上证50股指期权", "HO", "ho"),
    CNOptionUnderlying("MO", "CFFEX", "中证1000股指期权", "MO", "mo"),
)


def _option_index() -> dict[str, CNOptionUnderlying]:
    idx: dict[str, CNOptionUnderlying] = {}
    for item in _OPTION_UNDERLYINGS:
        idx[item.code] = item
        idx[item.sina_cate.upper()] = item
        idx[item.sina_cate] = item
        idx[item.name] = item
        if item.cffex_product:
            idx[item.cffex_product.upper()] = item
            idx[item.cffex_product] = item
    # Chinese aliases
    idx["上证50ETF"] = _OPTION_UNDERLYINGS[0]
    idx["50ETF期权"] = _OPTION_UNDERLYINGS[0]
    idx["沪深300"] = _OPTION_UNDERLYINGS[4]
    idx["沪深300期权"] = _OPTION_UNDERLYINGS[4]
    idx["中证1000"] = _OPTION_UNDERLYINGS[6]
    return idx


_OPTION_INDEX = _option_index()


def resolve_option_underlying(query: str) -> CNOptionUnderlying:
    raw = (query or "").strip()
    if not raw:
        raise InvalidSymbolError("期权标的为空")
    hit = _OPTION_INDEX.get(raw) or _OPTION_INDEX.get(raw.upper())
    if hit is None:
        raise InvalidSymbolError(f"未知期权标的: {query}")
    return hit


def normalize_option_contract(query: str) -> str:
    raw = (query or "").strip()
    if not raw:
        raise InvalidSymbolError("期权合约为空")
    if raw.upper().startswith("CON_OP_"):
        raw = raw.split("_")[-1]
    if raw.isdigit() and len(raw) >= 8:
        return raw
    # CFFEX style io2509C2800
    if re.fullmatch(r"[A-Za-z]{1,2}\d{3,4}[CPcp]\d+", raw):
        return raw
    raise InvalidSymbolError(f"无效期权合约: {query}")

