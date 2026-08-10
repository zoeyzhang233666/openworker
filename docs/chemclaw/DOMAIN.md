# ChemClaw 领域术语

本文件给人和 Codex 提供统一语言。代码名可以逐步演进，但产品设计和接口语义不得混用这些概念。

## 产品与运行环境

### ChemClaw

芯化和云面向化工领域的本地优先 AI 桌面产品，是唯一对外品牌。它继承 OpenWorker 的对话、MCP、权限和自动化能力，并逐步增加 Skill/Agent 平台与 SAG 知识检索/图谱。

### ChemClaw-Dev

源码开发模式使用的持久运行配置。不同普通 Worktree 可以复用连接凭据和依赖缓存，但对话、任务和测试数据库与稳定版分开。

### 稳定版

从 `main` 的稳定里程碑构建的 ChemClaw 安装程序/桌面应用。不是日常每次修改都重建的开发环境。

### Worktree

同一 Git 仓库的一个完整受控源码检出，用于隔离功能开发。Worktree 不是空环境，也不等于一套新的 MCP、Skill 和用户账号配置。

## 能力模型

### Skill

一个可复用工作流或专业能力单元。可以包含 `SKILL.md`、references、assets、scripts、依赖和配置要求。Skill 不是只有一份 Markdown 文档。

### Agent

一个可对话的角色与编排配置，组合系统提示、默认 Skills、工具、MCP、模型偏好和权限策略。Agent 引用 Skill，不复制 Skill。

### 智能体

产品界面中 Agent 的品类名（一级导航与管理页）。英文界面为 Agents。代码与会话字段仍可使用 `persona` / `agent`。个别角色的显示名可以包含「龙虾」等品牌趣味，但品类导航不使用「专家龙虾」。

### 白毛股神 Serenity

历史上由 `serenity-full-package` 识别出的 OpenClaw 风格 Agent 显示名。ChemClaw **内置**化工产业链智能体已更名为「产业链龙虾」（id `chain-lobster`，D-072）。上传 zip 仍可能合成独立的 `serenity` 用户智能体，与内置龙虾并存。

### 产业链龙虾

ChemClaw 内置的化工产业链研究智能体（id `chain-lobster`）。以原料→工艺/中间体→主产品→下游→终端为锚，默认挂载七个中文投研 Skill 与少量工具/行情 Skill；过程类 Skill（grill 等）在技能库中按需加载，不默认挂满。

### 任务模板

可复用的任务定义，包含提示词、Agent、Skills、输入、输出和可选时间规则。添加时间规则并启用后成为定时任务。

### 能力包

从本地目录或 Git 仓库提交给安装器的输入。一个能力包可以包含一个或多个 Agent、Skills、资源、脚本和依赖。

### 包检查结果

安装器在执行任何脚本前产生的结构化结果，包括识别出的能力、兼容性、依赖、配置、权限、安装步骤和风险。

### 最新有效版本

最近一次通过语法校验和最小可用性测试的 Skill/Agent 修订。所有对话的后续调用默认使用它。

### 修订

Skill/Agent 内容的一次可追溯变化。恢复旧内容也会产生新的修订，不把旧版本静默设为隐藏运行状态。

### 挂载

把一个 Agent、Skill 或知识项目加入当前对话的可见运行上下文。挂载项以标签展示，可查看、移除或更换。

### 待配置

能力与当前操作系统兼容，但缺少账号、API Key、授权码、端点或其他用户才能提供的设置。通过配置向导和连接测试后转为可用。

### 不兼容

能力要求当前 Windows 环境无法提供的平台或系统组件。普通用户界面不显示；安装报告保留跳过原因。

### 持久运行环境

由 ChemClaw 管理、跨对话和应用重启复用的 Python/Node 等依赖环境。它与 ChemClaw 主程序依赖隔离。

### 凭据保险箱

保存模型、MCP、邮箱和外部服务秘密的系统边界。秘密不得进入模型上下文、日志、Skill Git 历史或默认备份。

### ApiHub

芯化和云提供的 OpenAI 兼容模型中转网关。ChemClaw 以两个独立提供商接入：`apihub-cn`（国内，默认端点 `https://apihub.chem-cloud.cn/v1`）与 `apihub-intl`（国际，默认端点 `https://www.tokenfoundryx.com/v1`）。各自独立密钥与精选模型目录；端点可自定义。ApiHub 不是 ChemClaw 品牌本身，卡片显示为 `ApiHub CN (chem-cloud)` / `ApiHub Intl (chem-cloud)`。

## OpenWorker 能力

### MCP 连接

公司内部或外部工具/数据服务的标准连接。ChemClaw 保留 OpenWorker 的 MCP 能力，并为用户提供中文可视化配置、测试和审批。

### 权限与审批

对工具调用、写操作和外部副作用进行限制、确认和审计的既有安全边界。任何 Agent 或 Skill 都不能绕过。

### 自动化

OpenWorker 原有的调度执行能力。ChemClaw 的定时任务界面复用该引擎。

### 步骤组

一次 turn 内工具调用、已决议审批与中间叙述收成的 disclosure（界面常显示为「N 个步骤」；代码 `TurnGroup`）。最终回答在步骤组之外以普通助手气泡展示。

### 步骤组默认态

用户尚未点击步骤组标题时的展开/收起策略：进行中默认展开；成功结算默认收起；失败或中断默认保持展开（见 D-069）。

### 手动覆盖

用户点击步骤组标题后产生的粘性开关，在该步骤组实例生命周期内优先于步骤组默认态。

### 首包空窗

turn 已在运行（`running`），但尚未出现任一可见进展（reasoning、流式正文、工具或审批）时的静默区间。界面不得长期只显示含糊的「正在等待 Agent…」。

### 首包期

从用户发送到首包空窗结束的时段。此间 live ThinkingBlock 默认展开；无 reasoning 时可用龙虾口吻等待文案按前池→后池约每 3 秒轮播。

## 销售增长智能

### 外贸拓客任务

以具体产品/SKU、目标国家或区域、客户类型和排除条件为输入，形成可核验候选客户、双评分、证据和下一步动作的可恢复工作流。它不是一次搜索，也不是研究报告。

### `CommercialSKU`

一个可销售的具体化工产品。除化学身份外，还包含牌号、等级、纯度、粒径、包装、交付形态、用途、法规状态、来源、冲突和待确认字段。不同规格可能对应不同客户和应用，不得默认合并。

### `ApplicationGraph`

SKU 到功能、工艺、下游制品、行业和客户角色的有证据关系图。每条关系区分直接来源、交叉支持、专业推断和待验证。

### `ProductLanguageMap`

用于受控检索的多语言产品表达集合，包括化学同义词、商业同义词、牌号、规格、应用、企业角色、本地语言和排除词；动态学习项保留来源。

### `TargetMarket`

一次拓客任务的市场约束，包括国家、区域、语言、行业、客户类型、规模偏好、排除条件、合规约束和搜索预算。

### ICP

Ideal Customer Profile，目标客户画像。定义本次寻找哪些行业、角色、规模和地区的企业，以及哪些企业应排除；不能把“贸易商”等标签写成跨任务永久排除规则。

### `CompanyCandidate`

搜索阶段发现、尚未证明合格的企业线索。候选记录包含原始名称、国家、域名、发现来源和去重信息。

### `Account`、`Company`、`Site` 与 `Brand`

`Account` 是销售经营层面的集团或客户账户；`Company` 是法律或可识别经营主体；`Site` 是工厂、采购地点或经营场所；`Brand` 是产品或市场品牌。四者保留关系，不简单压成一个企业名称。

### `EvidenceItem`

支持一个具体结论的最小证据单元，记录来源、原始事实摘要、支持结论、事件/采集日期、证据等级、独立性和冲突状态。搜索摘要不是已验证页面证据。

### `CompanyEvidencePack`

围绕一个规范化企业主体聚合的主体、产品/应用、商业信号、联系人事实、风险、冲突和待补查证据集合。

### Lead

经过主体、企业角色和业务相关性核验，适合销售继续处理的企业。搜索结果或目录条目本身不是 Lead。

### `LeadList`

可经营的客户清单制品：分桶为可联系 / 待补查 / 已排除，含企业、双评分、下一步与销售状态。由平台 Tool `format_lead_list` 生成 Markdown/CSV；GUI「客户清单」可导入 JSON、导出 CSV、展开证据、注入补查/重评对话意图，并本地标记状态。清单不等于已发送邮件，也不等于 CRM 写入；工作台不静默改分。

### `Lead Fit Score`

由版本化确定性规则计算的商业匹配分，表达 SKU/应用、企业角色、商业信号、市场适配、可接触性和时效。它不等于成交概率。

### `Evidence Confidence`

由来源等级、独立来源数、主体归一、关键字段覆盖、时效和冲突计算的证据置信度。它与商业匹配分分开显示；未知主要降低置信度，不自动等同负面。

### `RecommendedAction`

基于 Lead 和证据缺口生成的下一步补查、联系、培育或排除建议。没有可靠事实时只建议联系人岗位角色，不猜测姓名、邮箱或采购量。

### `ProspectingRun`

一次可恢复、可审计的拓客任务，记录输入、查询、Provider、候选企业、证据、评分、规则/Skill 版本、失败和下一步动作。

### `OpportunitySignal`

询盘、招标、交易、扩产、招聘、价格、展会等有来源的业务事件。单个信号不自动等于商机。须含可回溯 locator；口述无来源不得伪造信号。

### TED 招标检索（`search_tenders`）

平台只读 Tool：检索欧盟 TED 公开采购公告，返回 `signal_type=tender` 的 `OpportunitySignal` 行（`signal_id=ted:<publication-number>` + `source.url`）。不评分、不伪造公告号；空结果为 `empty`。

### SAM.gov 招标检索（`search_sam_opportunities`）

平台只读 Tool：检索美国 SAM.gov 联邦采购机会，返回 `signal_id=sam:<noticeId>` 的 `OpportunitySignal` 行。需 SecretStore `sam:default` 的 `api_key`；无 noticeId 的行跳过；不评分、不伪造编号。

### `TradeFlow` / Comtrade（`lookup_trade_flow`）

国家/HS 层面的贸易流汇总（进口/出口金额与重量等），用于市场吸引力旁证。由平台 Tool `lookup_trade_flow`（UN Comtrade，`comtrade:default` 订阅密钥）返回；**不等于**企业买家名单，不得据此编造进口商。

### 海关企业级筛选（`filter_customs_importers`）

平台只读 Tool：读取工作区海关/提单 **CSV 或 XLSX**，筛货代/物流噪声并对候选进口商评分（`recommendation`、货代风险、进口商可能性、证据摘要）。**收货方/进口商不等于终端买家**；须与官网/主体交叉核验后再写入 Lead。与 Comtrade 用途不同；无外部海关 API；旧版 `.xls` 请另存为 `.xlsx`/CSV。

### Opportunity

一个或多个 `OpportunitySignal` 经主体归一、产品相关性和确定性商机评分（`chem-opportunity-fit`）后形成的可跟进业务机会。状态含 Watch / NeedsReview / Actionable / Rejected；无主体或无事件日期不得标为 Actionable。

### `OpportunityRadarRun`

一次可恢复的商机雷达任务，记录输入、阶段（signal_collect → normalize → score）、信号/商机 ID、预算、失败与下一步。

### `OutreachDraft`

一封待人工审阅的开发信/消息草稿：渠道、语言、收件岗位（个人邮箱可空）、主题正文、关联 Lead/Opportunity 与证据 ID，以及是否含价格/交期声明。草稿不等于已发送。

### `ready_for_human_send`

质量门禁通过后的推荐动作：草稿可提交**人工发送审批**。不等于已调用 `email_send`，也不等于邮件已发出。

### 发送审批（`email_send`）

通过 Email（IMAP/SMTP）连接器外发：凭据在 SecretStore；Tool `requires_approval=True`，须审批卡允许后才 SMTP 发送。须用户明确触发（对话或「提交发送审批」CTA）；无连接时返回中文错误。草稿就绪 ≠ 已发送。

### `ready_for_crm_write`

转化跟进可提交**人工 CRM 写入审批**的门禁标记（可与 `ready_for_human_send` 同轮或后续轮）。不等于已调用 HubSpot 写工具，也不等于已写入 CRM。

### CRM 笔记写入（`hubspot_log_note`）

复用 HubSpot 连接器：对已有 contact/company/deal 写 timeline 笔记；`requires_approval=True`。须文案含 `ready_for_crm_write` 且用户明确触发（对话或「提交 CRM 写入审批」CTA）；未连接返回中文错误。笔记流程不经 CTA 调用 `hubspot_create_contact`。客户清单页不显示 CRM 按钮。

### `ready_for_crm_create_contact`

转化跟进可提交**人工创建 HubSpot 联系人审批**的门禁标记。不等于已调用 `hubspot_create_contact`，也不等于已创建成功。须已有可靠 email；与 `ready_for_crm_write` 并列、互不替代。

### CRM 创建联系人（`hubspot_create_contact`）

复用 HubSpot 连接器创建联系人（`email` 必填）；`requires_approval=True`。须文案含 `ready_for_crm_create_contact` 且用户明确触发（对话或「提交创建联系人审批」CTA）；禁止编造邮箱/姓名；未开 `update_object` / `create_task` 产品 CTA。

### `FollowupPlan`

多轮跟进节拍：日偏移、目的、草稿要点、停止条件与人工确认点；不得假设邮件已发出。

### `EngagementRun`

一次可恢复的销售转化任务，状态 `input → strategy → draft → quality_gate → complete|blocked`，记录草稿/计划 ID、质量门禁结果与下一步；可选在人工确认后进入发送审批。

### Provider

对外部数据源的可替换适配边界，负责认证、请求、限流、响应规范化、来源和失败语义。API 客户端位于 Provider/Tool 层，不写进 Skill；Skill 负责业务流程和判断规则。

### 化学身份查询（`lookup_chemical_identity`）

平台只读 Tool：按 CAS 或品名查询化学身份（首包实现为 PubChem）。返回 `resolved` / `not_found` / `ambiguous` / `error` 与来源 URL；不推断商业应用或采购意图。格式与校验位仍由 Skill 本地 `cas.py` 负责。

### 法定主体查询（`lookup_legal_entity`）

平台只读 Tool：按 LEI、统一社会信用代码（USCC）或法律名称查询法定主体。路由：LEI/拉丁名 → GLEIF；USCC/中文名 → 国内登记（`cn_registry`，需配置 `base_url`）。返回 `resolved` / `not_found` / `ambiguous` / `error`、可选 LEI/USCC、登记状态、法域与来源；不推断产品需求，不冒充法律或制裁结论。LEI/USCC 经证据 locator 进入企业核验台账。

### 统一社会信用代码（USCC）

中国大陆 18 位主体标识码（含校验位）。平台校验格式与校验位；不得由模型编造。经 `cn_registry` 命中后作为 `government_registry` 证据。

### `Inquiry`

一次客户询盘的结构化表示：来源摘要、币种、Incoterm、行项目（SKU/数量/单位/单价可空）与未决字段。缺价或缺量不得静默补全。

### `QuoteDraft`

待人工审阅的报价草稿：分项、运费、税金、合计与计算器版本；推荐动作最多到 `ready_for_human_review`。草稿不等于已发送报价。

### `QuoteRun`

一次可恢复的询盘转报价任务，状态 `input → parse → calculate → draft → complete|blocked`。

### 报价合计（`calculate_quote`）

平台确定性 Tool：仅用显式数量与单价计算行合计与总计；缺失字段返回 `needs_review`，不编造价格。

## 知识与图谱

### 知识项目

一组文档、切片、实体、事件、关系、向量索引和探索记录的可备份边界。对话可以挂载一个或多个知识项目。

### SAG 图谱引擎

ChemClaw 后续使用的独立本地 Sidecar，负责结构化索引、向量检索、查询时动态关系推理、图谱查询、导入和备份恢复。它不负责 ChemClaw 最终对话回答。

### 快速检索

SAG 的 `vector` 策略，优先响应速度，适合事实和原文定位。

### 深度检索

SAG 的 `multi` 策略，利用 event–entity 索引和查询时动态超边进行精确、多跳关系检索。

### 探索模式

ChemClaw 对话框与 2D 图谱并列联动的工作界面。对话检索可定位图谱；节点选择可成为对话上下文。

### 完整备份

可恢复知识项目的备份，包含关系数据、向量索引、上传资料、格式/引擎版本、清单和校验值。敏感凭据默认排除。

### 结构化 JSON 导入

导入文档、切片、实体、事件和关系的交换格式。它通常不包含可直接使用的向量索引，因此可能需要后台向量化。

## 阶段五化工知识

### 化工百科页

具有稳定化学品 ID 的权威知识页，包含名称、CAS、别名、来源、应用、上下游、证据、价格入口和标准产业链图，并与相关页面建立双向链接。

### 双向链接

关系两端都可导航。例如“乙烯 → 聚乙烯”存在时，聚乙烯页面也能返回乙烯及关系语义。链接必须基于稳定 ID，而不是易歧义的显示文本。

### 来源路径树（线1）

从一次原料出发，按工业生产路径展开到基础原料、中间体、产品/制品和选择性精细品的分类体系。

### 应用去向树（线2/A线）

以国民经济行业分类为骨架，把化学品应用映射到行业、工艺/用途/原料及上游来源的分类体系。

### 标准产业链图

由版本化知识数据生成、经过审阅并发布的确定性图形。相同数据版本和模板必须得到相同图，不依赖每次对话临时发挥。

### 缩写消歧

在数据库写入、读取、跨源合并和安全合规场景中识别歧义缩写的强制过程。CAS 是首要唯一键；上下文不足或安全场景进入人工确认。

### 交互价格图

由有来源、时间戳、单位和品种 ID 的价格数据驱动的可缩放、筛选和联动图表。它是数据可视化，不是让模型凭文本即时编造曲线。

## 对话与上下文机制

### 出站上下文
发给模型的「当次 outbound view」消息集合；用户在界面上看到的对话历史不等同于出站上下文。

### 上下文压缩（OPE-27）
当出站上下文接近模型上下文上限时，把更老的部分用 LLM 摘要 + 机械提取状态替换；canonical 历史不改，只改变发给模型的消息。

### 上下文压缩失败降级
压缩器摘要失败后不阻塞用户交互，改为自动 Trim 并继续。压缩后续跑依赖 OPE-27 `<compacted-history>`（摘要、机械 working_state、用户原话与近期原文）；Trim 硬裁几乎无叙事摘要时，模型应重读工作区产物或必要时重跑工具。侧栏 Progress/`todo_write` 仅供人看计划，不作为压缩记忆通道。

### 出站裁剪
对出站视图中 `role="tool"` 的大回包统一按字符上限裁剪；溢出部分落盘到会话产物文件，并在出站内容中给出可读路径指针。

## 交付与产物

### 文档版

用户面向的最终 Markdown 报告产物，是默认主阅读面与存档/再编辑来源。

### 网页版

可选的、以文档版为素材在对话中生成的精装或可交互 HTML。不是默认交付；需用户同意并经对齐后再生成。定量控件不得使用报告中未出现的数与关系。

### 网页对齐

用户选择要网页版之后、正式写 HTML 之前，用一次一问澄清风格、篇幅与交互重量的过程（类似 grilling）。

### 价格表

文档版中用 Markdown 表格呈现的化工品行情数据（日期、区域、价格、涨跌等），来源为已配置 MCP/技能返回，不得编造。

### 交互行情图

网页版中可悬停查看细节的价格走势图；序列与价格表同源或经只读公开接口刷新，不把网页当作第二套研究代理。
