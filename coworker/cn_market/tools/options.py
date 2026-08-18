"""Structured China options tool registered on the global Agent in Run 5."""

from __future__ import annotations

from typing import Any, Callable, Optional

import aisuite as ai

from ..providers.options import PublicCNOptionProvider

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_cn_option_market",
        "description": (
            "Keyless China options market data. action enum: "
            "contracts, quote, daily, minute, greeks, exchange_stats. "
            "Price charts default to action=daily; use action=minute only when "
            "the user asked for 分时/分钟. "
            "SSE ETF (510050/50ETF) via Sina; CFFEX board via OptionService. "
            "greeks_source is upstream only — never invent local Greeks. "
            "exchange_stats may be source_unavailable. Not licensed market data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": (
                        "contracts | quote | daily | minute | greeks | exchange_stats. "
                        "Price chart default is daily."
                    ),
                },
                "underlying": {
                    "type": "string",
                    "description": "510050 / 50ETF / 510300 / IO / 沪深300 …",
                },
                "contract": {
                    "type": "string",
                    "description": "SSE numeric id (e.g. 10011255) or CFFEX code.",
                },
                "expiry": {
                    "type": "string",
                    "description": "YYYYMM for SSE, or CFFEX pinzhong like io2509.",
                },
                "option_type": {
                    "type": "string",
                    "description": "call / put / all",
                },
                "range": {
                    "type": "string",
                    "description": "For daily: 1mo, 3mo (default), 6mo, 1y, …",
                },
            },
            "required": ["action"],
        },
    },
}


def make_lookup_cn_option_market_tool(
    *, provider: Optional[PublicCNOptionProvider] = None
) -> Callable[..., Any]:
    p = provider or PublicCNOptionProvider()

    def lookup_cn_option_market(
        action: str,
        underlying: str = "",
        contract: str = "",
        expiry: str = "",
        option_type: str = "",
        range: str = "3mo",
    ) -> dict[str, Any]:
        return p.option_market(
            action=action,
            underlying=underlying,
            contract=contract,
            expiry=expiry,
            option_type=option_type,
            range=range,
        ).to_dict()

    lookup_cn_option_market.__name__ = "lookup_cn_option_market"
    lookup_cn_option_market.__doc__ = _SCHEMA["function"]["description"]
    lookup_cn_option_market.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="lookup_cn_option_market",
        category="web",
        risk_level="low",
        capabilities=["search", "fetch"],
        requires_approval=False,
    )
    lookup_cn_option_market.__coworker_schema__ = _SCHEMA
    return lookup_cn_option_market
