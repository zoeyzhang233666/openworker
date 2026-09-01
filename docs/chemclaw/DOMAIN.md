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

### API 公开查询

「连接」页第三栏（D-113 / D-114）：展示 Skill/Agent 使用的平台 Provider 清单，并写清做什么、谁在用、如何配置；需密钥项提供官方说明/申请外链（如 SAM、Comtrade）。与 MCP（自建工具服务器）和连接器（HubSpot/邮箱）分离；界面与 API **永不回显**密钥明文。

### ApiHub

芯化和云提供的 OpenAI 兼容模型中转网关。ChemClaw 以两个独立提供商接入：`apihub-cn`（国内，默认端点 `https://apihub.chem-cloud.cn/v1`）与 `apihub-intl`（国际，默认端点 `https://www.tokenfoundryx.com/v1`）。各自独立密钥与精选模型目录；端点可自定义。ApiHub 不是 ChemClaw 品牌本身，卡片显示为 `ApiHub CN (chem-cloud)` / `ApiHub Intl (chem-cloud)`。

## OpenWorker 能力

### Channel（多平台消息通道）

平台无关的入站/出站消息边界（D-188 / D-193 / D-196）。`coworker/channels` 提供 Envelope、Capabilities、媒体安全与按会话 FIFO；适配器覆盖企业微信、飞书、钉钉、官方个人微信 iLink（仅私聊）以及既有 Slack/Telegram。Channel 用户不提升本机权限；普通消息排队为独立轮次，明确补充/停止命令优先处理，`ask_user` 回答不入普通队列而直接释放对应挂起轮次。

### Channel 待答交互

一个以 Inbox item 为唯一状态源的跨终端 `ask_user` 等待状态。它绑定精确 `platform/account/conversation`，携带当前分组步骤与已收集答案；只接受同一授权私聊，或同一自动管理群中的已授权成员回答。桌面正在显示同一会话时，桌面卡片和 Channel 文本问题引用同一个 item，任一端回答均只释放一次。镜像以真实 `SendResult` 为准，短暂失败在 pending 期间有限重试。无效答案保持等待，多个待答冲突时拒绝猜测。本机目录、计划与外部写入审批不属于该交互，仍须电脑端处理。

### Channel 托管会话

由 ChemClaw 为一个 Channel target 自动创建并持久化的对话。`/new`、`/reset` 以及“开新的对话”“新的对话”“新建对话”等有限整句同义命令，原子把 target 映射到新会话，不删除旧会话；包含其它请求的长句不触发重置。旧轮次在所有权切换后不得再向该 target 发送 stream、终态或工具文本。显式订阅到桌面对话的群不是托管会话，群成员不能用命令重置它。

### 个人微信增量流

官方 iLink 私聊通道上的渐进式回答合同。iLink 没有企微 `reply_stream` 的单气泡原位刷新接口，因此 ChemClaw 先发一次处理提示，再按标点、长度和时间阈值发送有序正文段，终态只补未发送尾段；诊断值为 `streaming_mode=incremental_messages`。每段复用同一入站会话的 `context_token`，并在发送前校验 Channel 会话所有权。

### Channel 富内容交付

无前端渲染能力的 IM Channel 对 assistant 正文的出站策略（D-199 / D-199b）。`chart`/`mermaid`/`mmd` 围栏及其 JSON 源码不得进入聊天气泡；`channel_visible_text` 在流式阶段隐藏未闭合围栏，终态/`send_message` 经 `compose_channel_rich_reply` 把完整正文或 workspace `report.md` cook 为精装 HTML，再按 D-194 FileStorage 发 COS 链接或原生 `.html` 附件。有 chart 时 best-effort 另发与 HTML **同源**的 PNG 预览图。`report.md` 优先于正文 inline chart；只发一条链接。交付失败时只保留可读结论与中文降级说明，不回退原始 ChartSpec。桌面 GUI 仍保存并渲染完整 assistant message；普通代码围栏不受影响。

### 云文件存储（FileStorage）

平台无关的跨终端文件对象层（D-194）。本机 GUI 对话产物默认只保存在会话 workspace；向 IM Channel 发送文件时按需上传腾讯云 COS 得到 `FileRef`，再按平台矩阵投递（原生附件或公开 URL）。密钥存 SecretStore，不进入模型上下文。

### MCP 连接

公司内部或外部工具/数据服务的标准连接。ChemClaw 保留 OpenWorker 的 MCP 能力，并为用户提供中文可视化配置、测试和审批。

### 权限与审批

对工具调用、写操作和外部副作用进行限制、确认和审计的既有安全边界。任何 Agent 或 Skill 都不能绕过。

### 自动化

OpenWorker 原有的调度执行能力。ChemClaw 的定时任务界面复用该引擎。

### 本轮计划（TurnPlan）

`TurnPlanner` 在每个用户 turn 开始时生成的不可变执行合同，统一包含路由、`ExecutionProfile`、prompt profile、Provider 可见工具策略、Skill 元数据候选与 reasoning 展示策略。同一 turn 的所有模型迭代和 retry 复用同一计划；durable resume 生成保守 Agent 计划。它是优化层，不是权限授权层。

### Prompt Profile

本轮出站 system prompt 的投影等级。FAST/KNOWLEDGE 只保留 ChemClaw 身份、默认中文、安全边界、用户规则和会话固定记忆；VERIFIED 仅加入核验指南，行情 VERIFIED 再加入图表规范；明确 Agent 动作区分定向、普通工作区与可视化工作区 profile。不确定 Agent/Deep 使用完整 legacy prompt。投影只改 Provider 出站视图，不重写 canonical transcript。

### 工具能力包

根据明确意图从已注册 registry 选择的一组 Provider-visible schema，例如工作区、Memory、调度、消息、Skill 或销售。能力包不注销 Tool，也不改变 `PermissionEngine`；附件、后台、pending、Persona、未知 MCP/connector 或无法安全分类时回退完整 registry。

### Reasoning 请求与展示

`reasoning_mode` 表达向 Provider 请求的推理模式；`show_reasoning` 独立决定已返回 reasoning 是否广播到界面。只有模型能力明确支持时才发送关闭参数；Provider 有 reasoning 时默认实时展示，没有时沿用等待提示且不伪造。第一方 system/guidance 与核心工具 description 默认简体中文并要求用简体中文思考与回复（D-180）；研究路径上的子智能体工具、技能目录、行情口径政策与 Profile instructions 亦默认简体中文（D-182）；界面不翻译、不改写 upstream reasoning 正文。

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

可经营的客户清单制品：分桶为可联系 / 待补查 / 已排除，含企业、双评分、下一步与销售状态。由平台 Tool `format_lead_list` 生成 Markdown/CSV，作为对话产物供人工经营。清单不等于已发送邮件，也不等于 CRM 写入。GUI 不再提供独立「客户清单」导航页（D-168）；补查与重评在对话中进行。

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

平台只读 Tool：检索美国 SAM.gov 联邦采购机会，返回 `signal_id=sam:<noticeId>` 的 `OpportunitySignal` 行。需 SecretStore `sam:default` 的 `api_key`；无 noticeId 的行跳过；不评分、不伪造编号。**定位为境外可选**：大陆用户通常难以自助申请密钥；未配置时主路径改用 EU TED（`search_tenders`）与网页搜索，不以拿到 SAM key 为验收刚需。

### `TradeFlow` / Comtrade（`lookup_trade_flow`）

国家/HS 层面的贸易流汇总（进口/出口金额与重量等），用于市场吸引力旁证。由平台 Tool `lookup_trade_flow`（UN Comtrade，`comtrade:default` 订阅密钥）返回；**不等于**企业买家名单，不得据此编造进口商。**定位为境外可选**：未配置时主路径改用海关 CSV/XLSX（`filter_customs_importers`）与网页搜索。

### 欧盟 VAT 核验（`validate_eu_vat`）

平台只读 Tool：经 VATComply（免密钥）核验欧盟 VAT 号，返回 `valid`/`invalid`/`error` 与可选登记名址。仅为主体辅助，**不是**法律结论，不得仅凭 valid 判定 `Qualified`。

### 汇率换算（`lookup_fx_rate`）

平台只读 Tool：Frankfurter（免密钥）查询汇率并换算**用户已给出**的金额。用于询盘转报价多币种场景；**禁止**用其编造单价或数量。

### 维基百科摘要（`lookup_wikipedia`）

平台只读 Tool：MediaWiki 摘要（默认 `zh`，可 `en`）。用于品名/别名/用途百科背景；**不得**单独支撑 `Qualified` / `Actionable` 或采购意图。

### 化工社化学检索与写反应（`search_huagongshe` / `lookup_huagongshe_chemical` / `fetch_huagongshe_svg` / `validate_huagongshe_reaction` / `create_huagongshe_reaction`）

平台 Tool：对接 [化工社](https://huagongshe.com/guide) `GET /api/search`、`GET /api/chemicals/{id}`、公开 SVG（`GET /api/mol/{id}/svg/{w}x{h}.svg`、`GET /api/reactions/{id}/svg/{w}x{h}.svg`）、`POST /api/reactions/validate`、`POST /api/reactions`。可选 SecretStore `huagongshe:default` Bearer Token——公开检索与 SVG 可不配；**校验与保存必须配置**（含 `reaction:write`）。`fetch_huagongshe_svg` 将完整 SVG **落盘到工作区产物**，回包不含 SVG 正文；禁止用 `web_fetch` 搬运源码。`validate` 不写库、不审批；`create` 须 `Idempotency-Key` 且 `requires_approval=True`。**仅为化学证据补充**，不参与客户搜索与 Lead 评分。编排 Skill：`chem-huagongshe-reaction`（按需 `load_skill`，不强制进销售龙虾）。编辑/删改/改可见性在化工社网页完成；不引入本机 RDKit。

### 海关企业级筛选（`filter_customs_importers`）

平台只读 Tool：读取工作区海关/提单 **CSV 或 XLSX**，筛货代/物流噪声并对候选进口商评分（`recommendation`、货代风险、进口商可能性、证据摘要）。**收货方/进口商不等于终端买家**；须与官网/主体交叉核验后再写入 Lead。与 Comtrade 用途不同；无外部海关 API；旧版 `.xls` 请另存为 `.xlsx`/CSV。

### 单位与不确定度（`uncertainty-and-units`）

bundled Skill（D-111）：K-Dense MIT，经化工社合集单包引入。辅助询盘/报价中的单位换算与不确定度核对；`audit_units.py` 无第三方依赖。可选 pip extra `uncertainty`（pint/uncertainties）。**不**进入 Lead 评分；不替代 `calculate_quote`；不联网。

### 化工社合集分流（Triage）

治理制品（D-112）：对 `D:\化工社skills合集` 158 个 K-Dense zip 分档 DONE/P0/P1/P2/Skip，见 `docs/chemclaw/HUAGONGSHE_SKILL_TRIAGE.md`。Triage **不等于**批量安装；P0/P1 须确认后逐包实现。

### 内容策略词表（managed / user）

`chem-content-policy` 确定性扫描用的禁词层（D-128）：官方 `references/lexicon/managed/`（含 `rule_version`）可随发版热升级；用户 `user.csv` 可增删/`suppress` 规则且永不被官方同步覆盖。扫描输出含 `rule_set:{id,version}`。

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

复用 HubSpot 连接器创建联系人（`email` 必填）；`requires_approval=True`。须文案含 `ready_for_crm_create_contact` 且用户明确触发（对话或「提交创建联系人审批」CTA）；禁止编造邮箱/姓名。客户清单页不显示 CRM 按钮。

### `ready_for_crm_update_object`

转化跟进可提交**人工更新 HubSpot 字段审批**的门禁标记（D-127）。不等于已调用 `hubspot_update_object`。须可靠 `object_type`/`object_id` 与非空 `properties`；与笔记/创建联系人/创建任务门禁并列。

### CRM 字段更新（`hubspot_update_object`）

复用 HubSpot 连接器更新已有记录属性；`requires_approval=True`。须文案含 `ready_for_crm_update_object` 且用户明确触发（对话或「提交 CRM 字段更新审批」CTA）；禁止编造对象 ID 或字段值。

### `ready_for_crm_create_task`

转化跟进可提交**人工创建 HubSpot 任务审批**的门禁标记（D-127）。不等于已调用 `hubspot_create_task`。须已确认跟进动作作 `title`；已知联系人写入 `notes`（工具不关联对象）。

### CRM 任务创建（`hubspot_create_task`）

复用 HubSpot 连接器创建跟进任务；`requires_approval=True`。须文案含 `ready_for_crm_create_task` 且用户明确触发（对话或「提交 CRM 任务创建审批」CTA）；禁止编造标题。

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
压缩器摘要失败后不阻塞用户交互，也不弹 Retry 对话框。正常与紧缩摘要都失败时，先建立确定性 continuity ledger，机械保留最近 todo、产物路径、命令状态、MCP 查询、助手结论、用户原话与近期原文；只有该层也无法建立时才使用最小 Trim。压缩后续跑依赖 OPE-27 `<compacted-history>`，必要时重读工作区产物或重跑工具。侧栏 Progress/`todo_write` 仍是人看的计划 UI；压缩器只从 canonical tool record 机械提取其最近状态，不把侧栏本身作为独立记忆库。

### 摘要预算
摘要模型拥有独立于主聊触发阈值的输入预算。预算按摘要模型 context window 计算并预留输出与安全空间；未知模型使用保守窗口。摘要输入只包含受预算约束的用户意图、助手结论和工具摘要，不携带旧工具原文。`reasoning_content` 仅用于判断 reasoning-only 失败，不能直接成为后续对话记忆。

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

网页版中可悬停查看细节的价格走势图；序列与价格表同源或经只读公开接口刷新，不把网页当作第二套研究代理。对话内 inline `line`/`area`/`candlestick` 支持滚轮缩放与左右拖动（D-140/D-153）；现货密点时抽稀圆点与日期刻度；小图不画高低价，全屏才标可见窗全局极值（D-155）；阶段方向由区间涨跌幅重算，左栏驱动只写主导因素、不含具体价格（D-156）；短引用可用中文品种名对上工具回包别名（D-157）；阶段色带互斥、同柱不混色（D-158）；Yahoo/CN 短引用用本会话工具回包出图，直播不依赖 300 字截断 preview（D-159）；股票/期货/上市期权未指定周期时默认日线，不默认月线或分钟线（D-160）；产物 Markdown 预览与对话共用同一份会话 OHLC 回查（D-162）。

### 国内行情层

`coworker/cn_market/`：免登录、只读的中国市场结构化数据层（A 股/国内期货/期权等）。与 Yahoo 非官方 OHLC 并列，不是 Wind/Tushare/PandaData。AKShare 若使用只做可选 adapter，不是产品能力名，也不进入核心依赖。缓存写在用户 `state_dir`，不写仓库。A 股（D-149）、国内期货（D-150）、期权（D-151）adapter 已落地；Run 5（D-152）已将 `lookup_cn_*` 注册到默认对话。大陆 A 股/期货/期权走 CN 工具，美股/港股/全球期货走 Yahoo；结构化失败后不得用网页探测补数。

### 市场口径

一次行情请求所指的交易与报价体系，例如化工现货、国内期货或全球期货。市场口径由用户明确说出的“现货/期货”、交易所或合约代码决定，品种名本身不等于市场口径；甲醇、原油等裸品种问价存在多种合理口径时应先澄清。**默认一次只选一个口径**；当用户明确要求期现对照、基差或期货套利并结合现货时，允许同一轮同时读取化工现货与国内期货（D-177），但仍须标注来源，禁止把期货价冒充现货或反之。D-197 后，这些口径规则是 Planner/投影/prompt 的来源选择引导与回答质量合同，不再在 Tool 执行前产生 `market-scope denied` 硬拒绝。

### 化工现货价格

chem-data-hub MCP 返回的分区域、带时间戳和来源的化工商品现货序列。它不是交易所期货合约价，也不是网页摘要中的报价。连接未提供 `get_price_trend` 或返回空数据时记为 unavailable，不得用 Web、Yahoo 或期货价格替代。

### 期货行情

交易所合约、主力/连续合约的报价或 OHLC 序列。国内期货由 `lookup_cn_futures_*` 提供，WTI/Brent 等全球期货由 Yahoo OHLC best-effort 提供。期货行情不能冒充化工现货价格。

## Agent Harness 规划与诊断

### Scenario

一次用户请求的业务执行场景。Scenario 描述业务目标、所需与可选 Capability、输出约定、fallback policy 和 Subagent eligibility；它不是 Persona、Skill 或 Agent，也不直接保存底层 Tool 名。

### Capability

可由一个或多个 Provider 实现的稳定业务能力，例如化工现货价格、国内期货报价或化学品身份识别。Capability taxonomy 是面向规划的有限业务词表，不替代 ToolRegistry。

### Capability Provider binding

Capability 到具体 built-in Tool 或动态 MCP Tool 的唯一绑定位置，同时声明 authority、freshness、latency、cost、network scope、risk 与 fallback 关系。动态 MCP 可在未连接时显示 configured，但只有 live ToolDescriptor 匹配后才是 ready。

### Capability Resolution

按当前 ToolRegistry 与 MCP 配置解析每个 required/optional Capability 的 provider、工具集合和 `ready/configured/unavailable` 状态。required capability 不可用时不得偷偷开放未声明的 Web、期货或其他替代源。

### TurnPlan Preview

对真实 Planner/Resolver 的无副作用预演，展示 Scenario、route、readiness、选中/阻止工具、Skill、fallback、预计模型调用数、Subagent eligibility 与 warnings。Preview 不追加消息、不执行 Tool、不写 Audit 或 TurnTrace。

### ToolOutcome

Tool 执行结果的兼容状态层：`success/unavailable/partial/failed/denied`。模型继续读取 legacy raw result；诊断界面与 Trace 读取标准化摘要，持久 Trace 不保存 `data` 或 `source_refs`。

### TurnTrace

一次普通 turn、retry、durable resume 或后台投递的内容无关执行诊断记录。只保存 trace/session/source、Scenario/route、Capability/Tool 名称、调用与 token 计数、阶段耗时、fallback、Outcome 分类和最终状态；不保存消息正文、提示词、Tool 参数/结果或 reasoning。它与合规 Audit 分表，默认保留 30 天且全局最多 5000 条。

### Subagent Profile

平台声明式子智能体合同，定义 agent/mode/model/effort/max turns、Tool allowlist/denylist、Skill、声明 MCP、后台与隔离策略。Profile 不是 Persona，也不拥有独立权限系统。`explore` 为 plan + 只读；`research`（D-174）为 interactive + shared_workspace，可写报告并含国内期货等研究工具，子引擎继承父会话 PermissionEngine 模式；`worker` 等同属 shared_workspace，每次实际 Tool 调用仍由既有 PermissionEngine 和审批裁决。禁止默认嵌套 Subagent。

### Subagent Runtime

把 `SubagentProfile` 绑定到现有 `TurnEngine` 与持久 child conversation 的编排层。它负责创建/恢复 child session、前台兼容返回、后台 task、steering、stop 与 parent trace 关联；不实现第二套 Planner、Session、Memory、Permission 或 Tool 执行循环。停止分双模式（D-187）：用户手动 `immediate` 立刻 interrupt；智能体/系统 `wrap_up` 先 steer 催写部分报告再硬停。协作超时后仍非终态则 BackgroundTaskManager 强制落库 `cancelled`，晚到的 worker 不得回写覆盖。

### Background Task

Agent 或 Shell 的统一生命周期记录，状态为 `queued/running/completed/failed/cancelled/interrupted`。包含 owner session、父子关联、最小 metadata、时间与计数；输出另表按 cursor 增量读取。完成的 Agent 可接收后续消息并复用 child session；Shell 不接受消息且重启后不自动重放。

### Task Gather

在 owner session 边界内等待一组 Background Task 到达 terminal 状态并汇总记录。D-175 后它主要是短查/读终态报告的兜底（默认超时 60s），不再作为并行研究最终综合的主等待通道。

### Delegation Cohort

同批后台 Agent 子任务的汇合跟踪，键为 `(owner_session_id, parent_trace_id)`。全部到达终态后只触发一次合成通知；失败/取消/中断也算终态。前台 `explore`/同步子任务不入 cohort。

### Cohort Synthesis Wake

Cohort 全齐后由 harness 向父会话注入的汇合消息（`source.kind=subagent_cohort_complete`）。复用既有 `deliver_to_session`：父轮 idle 则开新回合，busy 则 steer 注入。这是最终综合的主触发通道，对标 Claude Code 完成后通知，不引入第二套 Agent Loop。

### Background Task Change

后台任务生命周期的轻量变化通知，类型为 `created/status/output`，只携带最新任务记录，不携带 Prompt、Tool 参数/结果正文、凭据或 reasoning。`SessionManager` 将其发送到 owner session 的 `background_task_changed` WebSocket 事件；事件只提示客户端刷新，REST/SQLite 才是权威状态。

### 会话任务栏

当前对话 RightRail 中按需出现的“子智能体与后台任务”模块。无任务时完全隐藏；有任务时按 owner session 加载列表和输出，可查看状态/耗时/工具工作记录/最终文本，停止运行中任务，或向 Agent task 续发要求。它不是合规 Audit、执行诊断页或隐藏推理查看器，也不提供权限提升。

### Subagent eligibility

TurnPlan 对“当前业务场景是否允许有界委派”的声明，不代表已启动子智能体。只有模型成功调用 `start_subagent` 后才产生 Background Task；默认委派门槛是存在至少两个互不依赖的研究分支，单事实查询与简单查价不启动。

Eligibility 需要同时满足：匹配到 `allow_subagent=true` 的 Scenario（当前为 `chemical_company_research` / `chemical_market_research`），且本轮 route 为 `AGENT` 或 `DEEP_RESEARCH`。含「深度研究/周报/产业链/上下游/套利研究」等研究标记的请求优先于 D-166 现货/期货查价 Scenario；命中研究 Scenario 后 TurnPlanner 可将仍为 `AGENT` 的路由升级为 `DEEP_RESEARCH`，并对父代理投影窄工具面（web + subagent 控制 + 合成写工具，不含行情 MCP/CN），避免主代理串行代劳查价（D-184）。纯「多少钱/报价」仍走查价 Scenario。模型若读到 readiness 中的 `subagent_eligible: false` 而自报「未被授权」，属于规划结果，不是 PermissionEngine 拒绝。`start_subagent` 默认 Profile 为 `research`；代码探索须显式 `explore`。
