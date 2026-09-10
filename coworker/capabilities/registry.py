"""Built-in Capability registry; the only Phase 1 home for exact Tool bindings."""

from __future__ import annotations

from .models import CapabilityProvider, CapabilitySpec


class CapabilityRegistry:
    def __init__(self, specs: tuple[CapabilitySpec, ...]) -> None:
        by_id: dict[str, CapabilitySpec] = {}
        for spec in specs:
            if spec.id in by_id:
                raise ValueError(f"duplicate capability id: {spec.id}")
            if not spec.providers:
                raise ValueError(f"capability has no provider: {spec.id}")
            by_id[spec.id] = spec
        self._by_id = by_id

    def get(self, capability_id: str) -> CapabilitySpec | None:
        return self._by_id.get(capability_id)

    def require(self, capability_id: str) -> CapabilitySpec:
        spec = self.get(capability_id)
        if spec is None:
            raise KeyError(f"unknown capability id: {capability_id}")
        return spec

    def list(self) -> tuple[CapabilitySpec, ...]:
        return tuple(self._by_id.values())


def _tool(capability_id: str, description: str, tool_name: str, **metadata: object) -> CapabilitySpec:
    return CapabilitySpec(
        id=capability_id,
        description=description,
        providers=(CapabilityProvider(provider_id=tool_name, binding_kind="tool", selector=tool_name, **metadata),),
    )


_BUILTINS = CapabilityRegistry(
    (
        CapabilitySpec(
            id="market.price.chemical_spot",
            description="化工品现货价格与趋势。",
            providers=(
                CapabilityProvider(
                    provider_id="chem-data-hub",
                    binding_kind="mcp_metadata",
                    selector="chem-data-hub:get_price_trend",
                    priority=100,
                    authority="specialist",
                    freshness="live",
                    network_scope="mcp",
                ),
            ),
        ),
        CapabilitySpec(
            id="market.price.chemical_spot_catalog",
            description="化工现货品名与别名查询。",
            providers=(
                CapabilityProvider(
                    provider_id="chem-data-hub",
                    binding_kind="mcp_metadata",
                    selector="chem-data-hub:search_compound",
                    priority=100,
                    authority="specialist",
                    freshness="live",
                    network_scope="mcp",
                ),
            ),
        ),
        CapabilitySpec(
            id="market.news.chemical",
            description="化工品市场资讯。",
            providers=(
                CapabilityProvider(
                    provider_id="chem-data-hub",
                    binding_kind="mcp_metadata",
                    selector="chem-data-hub:list_market_news_live",
                    priority=100,
                    authority="specialist",
                    freshness="live",
                    network_scope="mcp",
                ),
            ),
        ),
        _tool("market.price.cn_futures.quote", "国内期货实时报价。", "lookup_cn_futures_quote", authority="exchange_public", freshness="live", network_scope="public_web"),
        _tool("market.ohlc.cn_futures", "国内期货 OHLC。", "lookup_cn_futures_ohlc", authority="exchange_public", freshness="daily", network_scope="public_web"),
        _tool("chem.identity", "化学品名称、CAS 与分子式标识。", "lookup_chemical_identity", authority="pubchem", network_scope="public_api"),
        _tool("company.identity", "企业法定主体标识。", "lookup_legal_entity", authority="registry", network_scope="public_api"),
        _tool("research.web.search", "公开网页检索。", "web_search", authority="open_web", freshness="live", network_scope="web"),
        _tool("research.web.fetch", "读取已选择的公开网页。", "web_fetch", authority="open_web", freshness="live", network_scope="web"),
        _tool("interaction.clarify", "向用户澄清必要选择。", "ask_user", authority="user", network_scope="none"),
    )
)


def builtin_capability_registry() -> CapabilityRegistry:
    return _BUILTINS
