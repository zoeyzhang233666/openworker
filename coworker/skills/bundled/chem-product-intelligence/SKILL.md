---
name: chem-product-intelligence
description: "Use when 外贸拓客需要核验化工商业 SKU、应用证据或受控的多语言产品检索词。"
---

# 产品商业情报

把产品名、CAS、规格、牌号和用途转为可审计的 `CommercialSKU`、`ApplicationGraph` 与 `ProductLanguageMap`。这是客户发现的前置门禁，不是把化学常识扩写成市场需求。

## 身份门禁

先从用户资料或平台化学身份 Tool 收集名称、CAS、结构、等级、纯度、粒径、包装和交付形态。可用只读 Tool `lookup_chemical_identity`（默认 PubChem）辅助查询 CID/标准名/同义词/CAS；结果是外部证据，不是采购意图。需要品名/别名/用途百科背景时，可调用免密钥平台 Tool `lookup_wikipedia`（默认中文维基，可 `lang=en`）；摘要仅为背景，**不得**单独支撑 Qualified / Actionable 或采购意图，证据等级按百科上限处理。需要化工社化合物/反应库补充时，可调用只读平台 Tool `search_huagongshe` / `lookup_huagongshe_chemical`（可选 `huagongshe:default` Bearer；无密钥也可公开检索）；**仅为化学证据补充，禁止写入 Lead Fit / 企业评分主路径，不得据此编造买家**；本 Skill **不**调用化工社写反应接口。需要化合物或反应 **2D 结构图（SVG）** 时，调用平台 Tool `fetch_huagongshe_svg`（公开接口，完整落盘到 `huagongshe_assets/`，回包只有路径/元数据）；交付用 `[标题](artifact:相对路径)` 或 Markdown 图链；**禁止**用 `web_fetch` / shell 拉取或把 SVG 源码塞进对话。先调用 `load_skill` 加载本 Skill，读取返回的 `resources_path`；只用 `resources_path/scripts/cas.py` 的绝对路径执行 CAS 格式与校验位检查，不得假设当前工作目录，也不能把格式有效或 Provider 命中误称为商业身份已确认。

CAS、名称、结构或规格相互冲突时不得静默选择：输出冲突字段、每一方来源与需要用户确认的问题，状态为未解决。`lookup_chemical_identity` 返回 `ambiguous`/`not_found`/`error` 时保持 `unresolved` 并请求补证，不得编造 CID/CAS。身份未解决时不得生成客户名单。网络请求只通过平台 Provider/Tool，不在本 Skill 内直接访问 PubChem、维基或化工社。

选市场时可调用只读平台 Tool `lookup_trade_flow`（UN Comtrade，需配置 `comtrade:default` 的 `api_key`）查询国家/HS 贸易流汇总；**不**在本 Skill 内嵌 Comtrade 客户端。贸易流是国家级指标，**禁止**据此编造企业买家或进口商名单；无密钥或 empty/error 时披露缺口，不得伪造金额。

## 应用与语言地图

将应用关系逐条标为 `direct`、`cross_supported`、`inference` 或 `unverified`，保存证据 ID；“理论可用于”只能是 inference，不能写成市场正在采购。化学同义词、商业同义词、牌号、规格、应用词、客户角色、本地语言词和排除词必须分栏；动态词必须记录来源 ID，不得从模型记忆补词。

输出必须分别符合 `schemas/commercial-sku.schema.json`、`schemas/application-graph.schema.json` 和 `schemas/product-language-map.schema.json`。`resolved` 身份必须有非空标准名，且有 CAS 或明确身份证据；目标/排除用途与监管状态也要链接证据。不依赖 RDKit、Datamol、pip 或 npm；网络请求仍属于 Provider 层。
