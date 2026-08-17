"""Catalog of built-in platform Providers shown under 连接 → API 公开查询.

Skills/Agents call Tools; credentials live in SecretStore. This module never
returns secret values — only status and non-secret fields (e.g. base_url).
"""

from __future__ import annotations

from typing import Any, Optional

from .secrets import SecretStore

# Writable ids (POST). Free / workspace_file ids are list-only.
WRITABLE_IDS = frozenset(
    {"web_search", "sam", "comtrade", "cn_registry", "huagongshe"}
)

_HELP_KEYS = (
    "purpose_zh",
    "purpose_en",
    "used_by_zh",
    "used_by_en",
    "setup_zh",
    "setup_en",
    "docs_url",
    "signup_url",
)

CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "pubchem",
        "kind": "free",
        "label_zh": "PubChem 化学身份",
        "label_en": "PubChem chemical identity",
        "tool": "lookup_chemical_identity",
        "summary_zh": "已内置 · 无需密钥（只读化学标识辅助）",
        "summary_en": "Built-in · no API key (read-only chemical identity)",
        "purpose_zh": "根据品名或 CAS 查询化学标识（如 CAS、分子式）。只读辅助，不推断商业应用或采购意图。",
        "purpose_en": "Look up chemical identity (CAS, formula, etc.) from a name or CAS. Read-only; does not infer commercial use.",
        "used_by_zh": "外贸拓客 / 内贸拓客 · 产品情报（chem-product-intelligence）",
        "used_by_en": "Export/domestic prospecting · product intelligence",
        "setup_zh": "无需操作。ChemClaw 已内置，打开即可用。",
        "setup_en": "No setup. Built into ChemClaw.",
        "docs_url": "https://pubchem.ncbi.nlm.nih.gov/",
        "signup_url": "",
    },
    {
        "id": "huagongshe",
        "kind": "optional_secret",
        "label_zh": "化工社化学检索",
        "label_en": "Huagongshe chemistry search",
        "tool": "search_huagongshe",
        "summary_zh": "默认可公开检索 · 校验/保存须 API Token",
        "summary_en": "Public search by default · Token required for validate/create",
        "purpose_zh": "按名称/CAS/SMILES/DOI 等检索化工社化合物与反应（只读可不配密钥）。同卡 Token 供校验/保存：validate_huagongshe_reaction（不写库）与 create_huagongshe_reaction（须审批）。另有详情 Tool lookup_huagongshe_chemical。仅为化学证据补充，不参与客户搜索与 Lead 评分。",
        "purpose_en": "Search Huagongshe chemicals/reactions (read-only without a key). Same Token powers validate_huagongshe_reaction (no write) and create_huagongshe_reaction (requires approval). Detail: lookup_huagongshe_chemical. Chemical evidence only — not Lead scoring.",
        "used_by_zh": "产品情报 · 写反应 Skill（chem-huagongshe-reaction，按需）· 外贸/内贸龙虾（只读可选）",
        "used_by_en": "Product intelligence · chem-huagongshe-reaction (on demand) · export/domestic (read optional)",
        "setup_zh": "只读检索可不填密钥。校验或保存反应必须填 Token：打开下方申请页 → 账户设置生成含 reaction:write 的 Token → 粘贴到本卡片保存（密钥不回显）。Token 只发给 huagongshe.com；写库走审批卡。",
        "setup_en": "Search works without a key. Validate/create require a Token with reaction:write — paste it here (never echoed). Token is sent only to huagongshe.com; create goes through approval.",
        "docs_url": "https://huagongshe.com/guide",
        "signup_url": "https://huagongshe.com/guide",
        "secret_profile": "huagongshe:default",
    },
    {
        "id": "huagongshe_chemical",
        "kind": "free",
        "label_zh": "化工社化合物详情",
        "label_en": "Huagongshe chemical detail",
        "tool": "lookup_huagongshe_chemical",
        "summary_zh": "已内置 · 按 HCID 只读详情（Token 与检索卡共用）",
        "summary_en": "Built-in · HCID detail (shares optional token with search card)",
        "purpose_zh": "按化工社 HCID 读取化合物标识与结构摘要。化学证据补充，不进 Lead 评分。",
        "purpose_en": "Fetch chemical identifiers by HCID. Evidence only — not Lead scoring.",
        "used_by_zh": "产品情报（chem-product-intelligence）",
        "used_by_en": "Product intelligence",
        "setup_zh": "无需单独密钥。公开可用；若在「化工社化学检索」卡片保存了 Token，详情请求会自动带上。",
        "setup_en": "No separate key. Public by default; token from the Huagongshe search card is reused automatically.",
        "docs_url": "https://huagongshe.com/guide",
        "signup_url": "",
    },
    {
        "id": "huagongshe_svg",
        "kind": "free",
        "label_zh": "化工社 2D 结构图 SVG",
        "label_en": "Huagongshe 2D structure SVG",
        "tool": "fetch_huagongshe_svg",
        "summary_zh": "已内置 · 公开 SVG 落盘产物（不回传正文）",
        "summary_en": "Built-in · public SVG saved to workspace (no body in tool result)",
        "purpose_zh": "按 HCID/HRID 拉取分子或反应 2D SVG，写入工作区 huagongshe_assets/；回包仅路径与元数据。禁止用 web_fetch 搬 SVG 源码。化学证据补充，不进 Lead 评分。",
        "purpose_en": "Fetch molecule/reaction 2D SVG by HCID/HRID into workspace huagongshe_assets/; metadata only in the tool result. Do not web_fetch SVG bodies. Evidence only — not Lead scoring.",
        "used_by_zh": "产品情报（chem-product-intelligence）· 需要结构图时",
        "used_by_en": "Product intelligence when structure images are needed",
        "setup_zh": "无需密钥。公开接口；交付用 artifact: 链接或 Markdown 图。",
        "setup_en": "No API key. Public endpoint; deliver via artifact: link or Markdown image.",
        "docs_url": "https://huagongshe.com/guide",
        "signup_url": "",
    },
    {
        "id": "huagongshe_validate",
        "kind": "free",
        "label_zh": "化工社反应校验",
        "label_en": "Huagongshe reaction validate",
        "tool": "validate_huagongshe_reaction",
        "summary_zh": "须 Token · 校验草稿不写库（无审批）",
        "summary_en": "Token required · validate draft without saving (no approval)",
        "purpose_zh": "调用化工社 POST /api/reactions/validate，返回标准化草稿或错误。不保存；不进 Lead 评分。编排见 chem-huagongshe-reaction。",
        "purpose_en": "POST /api/reactions/validate — normalize draft or return errors. Does not save; not Lead scoring. See chem-huagongshe-reaction.",
        "used_by_zh": "chem-huagongshe-reaction（按需 load_skill）",
        "used_by_en": "chem-huagongshe-reaction (on-demand load_skill)",
        "setup_zh": "须先在「化工社化学检索」卡片保存 Token。校验本身不写库、不弹审批。",
        "setup_en": "Save Token on the Huagongshe search card first. Validate does not write or ask approval.",
        "docs_url": "https://huagongshe.com/guide",
        "signup_url": "",
    },
    {
        "id": "huagongshe_create",
        "kind": "free",
        "label_zh": "化工社反应保存",
        "label_en": "Huagongshe reaction create",
        "tool": "create_huagongshe_reaction",
        "summary_zh": "须 Token · 写库须审批 + Idempotency-Key",
        "summary_en": "Token required · write needs approval + Idempotency-Key",
        "purpose_zh": "用户确认后调用 POST /api/reactions 保存反应（须审批与幂等键）。未成功响应不得声称已保存；不进 Lead 评分。",
        "purpose_en": "After user confirmation, POST /api/reactions (approval + Idempotency-Key). Never claim saved without success; not Lead scoring.",
        "used_by_zh": "chem-huagongshe-reaction（按需 load_skill）",
        "used_by_en": "chem-huagongshe-reaction (on-demand load_skill)",
        "setup_zh": "须先在「化工社化学检索」卡片保存含 reaction:write 的 Token。调用后仍须审批卡通过才算写入成功。",
        "setup_en": "Save a reaction:write Token on the search card first. Approval is still required before the write succeeds.",
        "docs_url": "https://huagongshe.com/guide",
        "signup_url": "",
    },
    {
        "id": "gleif",
        "kind": "free",
        "label_zh": "GLEIF 法定主体",
        "label_en": "GLEIF legal entity",
        "tool": "lookup_legal_entity",
        "summary_zh": "已内置 · 无需密钥（国际 LEI 主体核验）",
        "summary_en": "Built-in · no API key (international LEI lookup)",
        "purpose_zh": "用公司名或 LEI 核验国际法定主体，帮助确认「这家公司是谁」。不能代替国内工商登记。",
        "purpose_en": "Verify international legal entities by name or LEI. Not a China business-registry substitute.",
        "used_by_zh": "外贸/内贸拓客 · 企业核验（chem-company-qualification）",
        "used_by_en": "Export/domestic prospecting · company qualification",
        "setup_zh": "无需操作。ChemClaw 已内置，打开即可用。",
        "setup_en": "No setup. Built into ChemClaw.",
        "docs_url": "https://www.gleif.org/",
        "signup_url": "",
    },
    {
        "id": "vatcomply",
        "kind": "free",
        "label_zh": "欧盟 VAT 核验",
        "label_en": "EU VAT validation",
        "tool": "validate_eu_vat",
        "summary_zh": "已内置 · 无需密钥（VATComply 只读核验）",
        "summary_en": "Built-in · no API key (VATComply read-only check)",
        "purpose_zh": "核验欧盟 VAT 号格式与登记状态，辅助欧盟 B2B 主体确认。不是法律结论，不能单独据此判定 Qualified。",
        "purpose_en": "Validate EU VAT numbers for B2B assist. Not a legal conclusion; never sole grounds for Qualified.",
        "used_by_zh": "外贸拓客 / 商机雷达 · 企业核验（chem-company-qualification）",
        "used_by_en": "Export / opportunity · company qualification",
        "setup_zh": "无需操作。ChemClaw 已内置，打开即可用（大陆网络探针已通过）。",
        "setup_en": "No setup. Built into ChemClaw (mainland reachability probed).",
        "docs_url": "https://www.vatcomply.com/documentation",
        "signup_url": "",
    },
    {
        "id": "frankfurter",
        "kind": "free",
        "label_zh": "汇率换算（Frankfurter）",
        "label_en": "FX rates (Frankfurter)",
        "tool": "lookup_fx_rate",
        "summary_zh": "已内置 · 无需密钥（报价多币种换算）",
        "summary_en": "Built-in · no API key (quote multi-currency FX)",
        "purpose_zh": "查询汇率并把用户已给出的金额换算到目标币种。不得编造单价或数量；仅服务询盘报价。",
        "purpose_en": "Look up FX and convert amounts the user already provided. Never invents unit prices.",
        "used_by_zh": "外贸转化龙虾 · 询盘转报价（chem-inquiry-to-quote）",
        "used_by_en": "Export-engagement lobster · inquiry-to-quote",
        "setup_zh": "无需操作。ChemClaw 已内置。在「连接 → API 公开查询」可见本卡片即表示已接入。",
        "setup_en": "No setup. Built into ChemClaw. Seeing this card means the provider is wired.",
        "docs_url": "https://www.frankfurter.app/docs",
        "signup_url": "",
    },
    {
        "id": "yahoo_chart_unofficial",
        "kind": "free",
        "label_zh": "期货/股票 OHLC（Yahoo 非官方）",
        "label_en": "Futures/stock OHLC (Yahoo unofficial)",
        "tool": "lookup_yahoo_ohlc",
        "summary_zh": "已内置 · 无需密钥（best-effort，非持牌行情）",
        "summary_en": "Built-in · no API key (best-effort; not licensed market data)",
        "purpose_zh": "拉取股票/期货日线开高低收，供蜡烛图。不替代化工现货 chem-data-hub；非投资建议。",
        "purpose_en": "Fetch stock/futures daily OHLC for candlesticks. Not a chem spot substitute; not investment advice.",
        "used_by_zh": "默认 ChemClaw · 期货/股价走势问句",
        "used_by_en": "Default ChemClaw · futures/stock price questions",
        "setup_zh": "无需密钥。若直连失败可设环境变量 CHEMCLAW_HTTP_PROXY 后重启。",
        "setup_en": "No API key. If blocked, set CHEMCLAW_HTTP_PROXY and restart.",
        "docs_url": "https://finance.yahoo.com/",
        "signup_url": "",
    },
    {
        "id": "wikipedia",
        "kind": "free",
        "label_zh": "维基百科摘要",
        "label_en": "Wikipedia extract",
        "tool": "lookup_wikipedia",
        "summary_zh": "已内置 · 无需密钥（化工品百科背景）",
        "summary_en": "Built-in · no API key (chemical encyclopedia background)",
        "purpose_zh": "按品名/别名读取维基百科简介，辅助产品背景。不是采购证据，不得单独支撑 Qualified。",
        "purpose_en": "Fetch Wikipedia intro for product/synonym background. Not purchase evidence; never sole Qualified support.",
        "used_by_zh": "产品情报（chem-product-intelligence）· 外贸/内贸/商机龙虾",
        "used_by_en": "Product intelligence · export/domestic/opportunity lobsters",
        "setup_zh": "无需操作。ChemClaw 已内置；默认中文维基，可切英文。",
        "setup_en": "No setup. Built into ChemClaw; default zh Wikipedia, en allowed.",
        "docs_url": "https://www.mediawiki.org/wiki/API:Main_page",
        "signup_url": "",
    },
    {
        "id": "ted",
        "kind": "free",
        "label_zh": "EU TED 招标",
        "label_en": "EU TED tenders",
        "tool": "search_tenders",
        "summary_zh": "已内置 · 无需密钥（欧盟公开招标检索）",
        "summary_en": "Built-in · no API key (EU public procurement search)",
        "purpose_zh": "检索欧盟公开招标公告，发现可能的采购商机。不伪造公告号；无命中会如实说明。",
        "purpose_en": "Search EU public procurement notices. Never invents notice IDs; empty results are disclosed.",
        "used_by_zh": "商机雷达龙虾 · chem-opportunity-radar",
        "used_by_en": "Opportunity radar lobster · chem-opportunity-radar",
        "setup_zh": "无需操作。ChemClaw 已内置，打开即可用。大陆主路径商机源优先用本项，不必先配 SAM。",
        "setup_en": "No setup. Built into ChemClaw. Prefer this for mainland opportunity search; SAM is optional.",
        "docs_url": "https://ted.europa.eu/",
        "signup_url": "",
    },
    {
        "id": "web_fetch",
        "kind": "free",
        "label_zh": "网页抓取",
        "label_en": "Web fetch",
        "tool": "web_fetch",
        "summary_zh": "已内置 · 无需密钥（只读抓取网页正文）",
        "summary_en": "Built-in · no API key (read-only page fetch)",
        "purpose_zh": "只读抓取对话中给出的网页正文，便于摘证据。不能登录需账号的网站，也不会自动发帖。",
        "purpose_en": "Read-only fetch of page text from URLs in chat. No login to private sites; never posts.",
        "used_by_zh": "各龙虾通用（搜索后打开页面取证）",
        "used_by_en": "All agents (open pages after search for evidence)",
        "setup_zh": "无需操作。ChemClaw 已内置，打开即可用。",
        "setup_en": "No setup. Built into ChemClaw.",
        "docs_url": "",
        "signup_url": "",
    },
    {
        "id": "customs_file",
        "kind": "workspace_file",
        "label_zh": "海关企业级文件",
        "label_en": "Customs enterprise file",
        "tool": "filter_customs_importers",
        "summary_zh": "工作区 CSV/XLSX · 无外部海关 API 密钥",
        "summary_en": "Workspace CSV/XLSX · no external customs API key",
        "purpose_zh": "读取你放进工作区的海关/提单 CSV 或 XLSX，筛货代噪声并给候选进口商打分。收货方不等于终端买家；不会把结果直接标成合格客户。",
        "purpose_en": "Screen workspace customs/BOL CSV or XLSX: filter forwarders and rank importer candidates. Consignee ≠ end buyer; never auto-marks Qualified.",
        "used_by_zh": "外贸拓客龙虾 · 买家发现 / 拓客主流程",
        "used_by_en": "Export-sales lobster · buyer discovery / prospecting",
        "setup_zh": "无需网站密钥。把文件放进当前对话工作区后，让外贸拓客调用筛选。点检样例：tests/fixtures/customs/sample_shipments.csv（或 .xlsx）。大陆找买家优先本项，不必先配 Comtrade。",
        "setup_en": "No website API key. Put CSV/XLSX in the session workspace, then ask export prospecting to filter. Prefer this over Comtrade for mainland buyer discovery.",
        "docs_url": "",
        "signup_url": "",
    },
    {
        "id": "web_search",
        "kind": "optional_secret",
        "label_zh": "网页搜索",
        "label_en": "Web search",
        "tool": "web_search",
        "summary_zh": "默认可 DuckDuckGo；可选 Tavily/Brave 等引擎密钥",
        "summary_en": "DuckDuckGo by default; optional Tavily/Brave API key",
        "purpose_zh": "在互联网上搜索公开网页，供拓客与核验取证。默认 DuckDuckGo 免密钥即可用；换更好引擎时再填密钥。",
        "purpose_en": "Search the public web for evidence. DuckDuckGo works with no key; optional Tavily/Brave for better results.",
        "used_by_zh": "各龙虾通用（尤其买家发现、企业核验）",
        "used_by_en": "All agents (especially buyer discovery and qualification)",
        "setup_zh": "默认可不填密钥。若选择 Tavily：打开 tavily.com 注册后复制 API Key；若选 Brave：打开 brave.com/search/api 申请后复制密钥。回到本卡片选择引擎、粘贴密钥并保存。",
        "setup_en": "Default needs no key. For Tavily: sign up at tavily.com and copy the API key. For Brave: request a key at brave.com/search/api. Then pick the engine here, paste, and save.",
        "docs_url": "https://tavily.com/",
        "signup_url": "https://brave.com/search/api/",
        "secret_profile": "web_search:default",
    },
    {
        "id": "sam",
        "kind": "secret",
        "label_zh": "SAM.gov（境外可选）",
        "label_en": "SAM.gov (optional overseas)",
        "tool": "search_sam_opportunities",
        "summary_zh": "境外可选 · 美国联邦采购 · 需 api_key（sam:default）",
        "summary_en": "Optional overseas · US federal opportunities · api_key (sam:default)",
        "purpose_zh": "检索美国联邦公开采购/招标机会。可用性：境外账号/网络可选；中国大陆用户通常难以自助申请密钥。未配置不影响主流程（请用 EU TED）。未配置时只中文提示，不编造公告编号。",
        "purpose_en": "Search US federal opportunities. Optional for overseas accounts/networks; mainland users often cannot self-serve keys. Unconfigured does not block the main path (use EU TED). Never invents notice IDs.",
        "used_by_zh": "商机雷达龙虾 · chem-opportunity-radar（仅当用户要美国联邦标且已配密钥）",
        "used_by_en": "Opportunity radar · only when US federal tenders are requested and keyed",
        "setup_zh": "境外可选，非大陆刚需。1）能访问 sam.gov 时打开申请页注册并申请 Public API Key；2）粘贴到本卡片保存。若申请不了：改用「EU TED 招标」（免密钥）或网页搜索，无需本密钥。",
        "setup_en": "Optional overseas — not required on mainland. 1) If you can reach sam.gov, request a Public API Key and paste it here. 2) If not: use EU TED (keyless) or web search instead.",
        "docs_url": "https://open.gsa.gov/api/get-opportunities-public-api/",
        "signup_url": "https://sam.gov/",
        "secret_profile": "sam:default",
    },
    {
        "id": "comtrade",
        "kind": "secret",
        "label_zh": "UN Comtrade（境外可选）",
        "label_en": "UN Comtrade (optional overseas)",
        "tool": "lookup_trade_flow",
        "summary_zh": "境外可选 · 贸易流汇总 · 需 api_key（非买家名单）",
        "summary_en": "Optional overseas · trade-flow aggregates · api_key (not buyer lists)",
        "purpose_zh": "按国家与 HS 编码查看进出口贸易流汇总，辅助选市场。可用性：境外账号/网络可选；大陆用户通常难以自助申请。未配置不影响主流程（请用海关文件 + 网页搜索）。结果不是企业买家名单。",
        "purpose_en": "Country/HS trade-flow aggregates. Optional overseas; mainland users often cannot self-serve keys. Unconfigured does not block the main path (customs files + web search). Not a buyer list.",
        "used_by_zh": "外贸拓客龙虾 · 选市场旁证（仅当已配密钥）",
        "used_by_en": "Export-sales · market assist only when keyed",
        "setup_zh": "境外可选，非大陆刚需。1）能访问 comtradedeveloper.un.org 时注册订阅并复制密钥；2）粘贴保存。若申请不了：改用工作区「海关企业级文件」筛选 + 网页搜索找买家，无需本密钥。",
        "setup_en": "Optional overseas — not required on mainland. 1) If you can reach the UN developer portal, create a subscription and paste the key. 2) If not: use workspace customs CSV/XLSX + web search instead.",
        "docs_url": "https://comtradedeveloper.un.org/",
        "signup_url": "https://comtradedeveloper.un.org/",
        "secret_profile": "comtrade:default",
    },
    {
        "id": "cn_registry",
        "kind": "secret",
        "label_zh": "国内登记",
        "label_en": "China registry",
        "tool": "lookup_legal_entity",
        "summary_zh": "国内主体核验 · 需 base_url，可选 api_key",
        "summary_en": "CN legal entity · base_url required, optional api_key",
        "purpose_zh": "用中文名或统一社会信用代码核验国内主体。ChemClaw 不托管公共登记网站，需对接你们自己的登记服务地址。",
        "purpose_en": "Verify China entities by Chinese name or USCC. ChemClaw does not host a public registry — you supply your service base URL.",
        "used_by_zh": "内贸拓客龙虾 · 企业核验（国内路由）",
        "used_by_en": "Domestic-sales lobster · company qualification (CN route)",
        "setup_zh": "向贵司 IT 或数据供应商要登记查询服务的 HTTPS 地址（base_url），填到下方「服务地址」。若该服务还发了 api_key，一并粘贴（可选）。不要去随便一个公开网站乱填地址。",
        "setup_en": "Ask your IT or data vendor for the registry HTTPS base_url and paste it below. Optional api_key if they issue one. Do not invent a random public website URL.",
        "docs_url": "",
        "signup_url": "",
        "secret_profile": "cn_registry:default",
    },
)


def _meta(entry: dict[str, Any]) -> dict[str, Any]:
    out = {
        "id": entry["id"],
        "kind": entry["kind"],
        "label_zh": entry["label_zh"],
        "label_en": entry["label_en"],
        "tool": entry["tool"],
        "summary_zh": entry["summary_zh"],
        "summary_en": entry["summary_en"],
    }
    for key in _HELP_KEYS:
        out[key] = entry.get(key) or ""
    return out


def status_for_entry(
    entry: dict[str, Any],
    secrets: SecretStore,
    *,
    web_search_status: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build one list/detail row. Never includes api_key values."""
    out = _meta(entry)
    kind = entry["kind"]
    eid = entry["id"]

    # Write tools share huagongshe:default Token (configured on search card).
    if eid in ("huagongshe_validate", "huagongshe_create"):
        profile = secrets.get("huagongshe:default") or {}
        has_key = bool(str(profile.get("api_key") or "").strip())
        out["ready"] = has_key
        out["configured"] = has_key
        out["has_api_key"] = has_key
        return out

    if kind in ("free", "workspace_file"):
        out["ready"] = True
        out["configured"] = True
        out["has_api_key"] = False
        return out

    if eid == "web_search":
        ws = web_search_status or {}
        provider = ws.get("provider") or "duckduckgo"
        has_key = bool(ws.get("has_key"))
        out["ready"] = True  # DuckDuckGo works without a key
        out["configured"] = True
        out["has_api_key"] = has_key
        out["provider"] = provider
        out["providers"] = list(ws.get("providers") or [])
        return out

    if eid == "huagongshe":
        profile = secrets.get("huagongshe:default") or {}
        has_key = bool(str(profile.get("api_key") or "").strip())
        out["ready"] = True  # public search works without a key
        out["configured"] = True
        out["has_api_key"] = has_key
        return out

    if eid == "sam":
        profile = secrets.get("sam:default") or {}
        has_key = bool(str(profile.get("api_key") or "").strip())
        out["ready"] = has_key
        out["configured"] = has_key
        out["has_api_key"] = has_key
        return out

    if eid == "comtrade":
        profile = secrets.get("comtrade:default") or {}
        has_key = bool(str(profile.get("api_key") or "").strip())
        out["ready"] = has_key
        out["configured"] = has_key
        out["has_api_key"] = has_key
        return out

    if eid == "cn_registry":
        profile = secrets.get("cn_registry:default") or {}
        base_url = str(profile.get("base_url") or "").strip()
        has_key = bool(str(profile.get("api_key") or "").strip())
        configured = bool(base_url)
        out["ready"] = configured
        out["configured"] = configured
        out["has_api_key"] = has_key
        out["base_url"] = base_url
        return out

    out["ready"] = False
    out["configured"] = False
    out["has_api_key"] = False
    return out


def list_lookups(
    secrets: SecretStore,
    *,
    web_search_status: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    return [
        status_for_entry(e, secrets, web_search_status=web_search_status)
        for e in CATALOG
    ]


def get_lookup(
    lookup_id: str,
    secrets: SecretStore,
    *,
    web_search_status: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    for e in CATALOG:
        if e["id"] == lookup_id:
            return status_for_entry(e, secrets, web_search_status=web_search_status)
    return None


def apply_lookup_update(
    lookup_id: str,
    body: dict[str, Any],
    secrets: SecretStore,
    *,
    set_web_search: Any = None,
) -> dict[str, Any]:
    """Persist writable lookup config. Returns {ok, error?} plus refreshed fields."""
    if lookup_id not in WRITABLE_IDS:
        return {
            "ok": False,
            "error": "该项无需配置或不可在此修改（免密钥 / 工作区文件）",
        }

    clear_key = bool(body.get("clear_api_key"))
    api_key = body.get("api_key")
    if api_key is not None:
        api_key = str(api_key).strip()

    if lookup_id == "web_search":
        if set_web_search is None:
            return {"ok": False, "error": "网页搜索配置不可用"}
        provider = str(body.get("provider") or "").strip()
        if not provider:
            return {"ok": False, "error": "请选择搜索引擎（provider）"}
        key_arg = None if clear_key else (api_key if api_key else None)
        if not clear_key and api_key is None:
            existing = secrets.get("web_search:default") or {}
            key_arg = str(existing.get("api_key") or "").strip() or None
        result = set_web_search(provider, key_arg)
        if result.get("ok") is False:
            err = result.get("error") or "保存失败"
            if "unknown provider" in str(err):
                return {"ok": False, "error": f"未知搜索引擎：{provider}"}
            return {"ok": False, "error": str(err)}
        return {"ok": True, "id": lookup_id}

    if lookup_id == "sam":
        profile = dict(secrets.get("sam:default") or {})
        if clear_key:
            profile.pop("api_key", None)
            if profile:
                secrets.put("sam:default", profile)
            else:
                secrets.delete("sam:default")
            return {"ok": True, "id": lookup_id}
        if not api_key:
            return {"ok": False, "error": "请填写 SAM.gov API 密钥（api_key）"}
        profile["api_key"] = api_key
        secrets.put("sam:default", profile)
        return {"ok": True, "id": lookup_id}

    if lookup_id == "huagongshe":
        profile = dict(secrets.get("huagongshe:default") or {})
        if clear_key:
            profile.pop("api_key", None)
            if profile:
                secrets.put("huagongshe:default", profile)
            else:
                secrets.delete("huagongshe:default")
            return {"ok": True, "id": lookup_id}
        if not api_key:
            return {
                "ok": False,
                "error": "请填写化工社 API Token（api_key），或不填则保持公开检索",
            }
        profile["api_key"] = api_key
        secrets.put("huagongshe:default", profile)
        return {"ok": True, "id": lookup_id}

    if lookup_id == "comtrade":
        profile = dict(secrets.get("comtrade:default") or {})
        if clear_key:
            profile.pop("api_key", None)
            if profile:
                secrets.put("comtrade:default", profile)
            else:
                secrets.delete("comtrade:default")
            return {"ok": True, "id": lookup_id}
        if not api_key:
            return {"ok": False, "error": "请填写 UN Comtrade 订阅密钥（api_key）"}
        profile["api_key"] = api_key
        secrets.put("comtrade:default", profile)
        return {"ok": True, "id": lookup_id}

    if lookup_id == "cn_registry":
        profile = dict(secrets.get("cn_registry:default") or {})
        if "base_url" in body:
            base_url = str(body.get("base_url") or "").strip()
            if base_url:
                profile["base_url"] = base_url
            else:
                profile.pop("base_url", None)
        if clear_key:
            profile.pop("api_key", None)
        elif api_key:
            profile["api_key"] = api_key
        if not str(profile.get("base_url") or "").strip():
            return {
                "ok": False,
                "error": "请填写国内登记服务地址（base_url）",
            }
        secrets.put("cn_registry:default", profile)
        return {"ok": True, "id": lookup_id}

    return {"ok": False, "error": "未知配置项"}
