import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type React from "react";
import { interfaceMessagesZh, type InterfaceMessageKey } from "./interfaceMessages";

export type Locale = "zh-CN" | "en-US";

const messages = {
  "zh-CN": {
    "nav.conversations": "对话",
    "nav.skills": "技能",
    "nav.experts": "智能体",
    "nav.leads": "客户清单",
    "leads.title": "客户清单",
    "leads.subtitle": "导入拓客 JSON，导出 CSV，本地标记状态。不自动发邮件、不写 CRM。",
    "leads.importJson": "导入 JSON",
    "leads.exportCsv": "导出 CSV",
    "leads.importInvalid": "无效的客户清单 JSON（需要 leads 数组，且每项含 company 与 sales_status）。",
    "leads.counts": "可联系 {contactable} · 待补查 {needsReview} · 已排除 {excluded} · 合计 {total}",
    "leads.filterAll": "全部",
    "leads.filterContactable": "可联系",
    "leads.filterNeedsReview": "待补查",
    "leads.filterExcluded": "已排除",
    "leads.empty": "还没有客户。请先用拓客龙虾生成清单并导入 JSON，或从对话产物粘贴 LeadList。",
    "leads.col.company": "企业",
    "leads.col.type": "类型",
    "leads.col.fit": "商业匹配",
    "leads.col.conf": "证据置信度",
    "leads.col.next": "下一步",
    "leads.col.status": "状态",
    "leads.col.notes": "备注",
    "leads.col.actions": "操作",
    "leads.markContactable": "可联系",
    "leads.markNeedsReview": "待补查",
    "leads.markExcluded": "排除",
    "leads.defaultExcludeReason": "用户排除",
    "leads.footer": "状态保存在本机浏览器。发送与 CRM 未在本页提供；补查/重评仅注入对话，须人工确认。",
    "leads.showDetail": "详情",
    "leads.hideDetail": "收起",
    "leads.continueResearch": "继续补查",
    "leads.researchHint": "向当前对话注入补查请求，不会自动外发。",
    "leads.rescore": "调整 ICP 并重评",
    "leads.rescoreHint": "向当前对话注入重评请求；工作台不会静默改分。",
    "leads.runSummary": "拓客断点：run {runId} · 阶段 {stage} · 预算 {budget}",
    "leads.detail.match": "匹配原因",
    "leads.detail.evidence": "关键证据",
    "leads.detail.next": "下一步",
    "leads.detail.exclude": "排除原因",
    "sendApproval.submit": "提交发送审批",
    "sendApproval.hint": "将请求助手调用 email_send；仍须在审批卡中确认。不会自动外发。",
    "crmWriteApproval.submit": "提交 CRM 写入审批",
    "crmWriteApproval.hint":
      "将请求助手调用 hubspot_log_note；仍须在审批卡中确认。不会自动写入 CRM。",
    "crmCreateContact.submit": "提交创建联系人审批",
    "crmCreateContact.hint":
      "将请求助手调用 hubspot_create_contact；仍须在审批卡中确认。不会自动创建联系人。",
    "crmUpdateObject.submit": "提交 CRM 字段更新审批",
    "crmUpdateObject.hint":
      "将请求助手调用 hubspot_update_object；仍须在审批卡中确认。不会自动更新字段。",
    "crmCreateTask.submit": "提交 CRM 任务创建审批",
    "crmCreateTask.hint":
      "将请求助手调用 hubspot_create_task；仍须在审批卡中确认。不会自动创建任务。",
    "nav.scheduled": "定时任务",
    "nav.connections": "连接",
    "nav.settings": "设置",
    "skills.pageTitle": "技能",
    "skills.pageIntro": "可复用的工作流与能力说明。在此关闭的技能在所有对话中都不会被调用。",
    "skills.title": "技能",
    "skills.subtitle": "可复用的工作流说明，助手可在任意对话中调用。在此关闭即全局关闭。",
    "skills.add": "添加技能",
    "skills.writeMyself": "手动编写",
    "skills.writeMyselfHint": "填写名称、描述与指令正文",
    "skills.importFile": "导入文件",
    "skills.importFileHint": "导入他人分享的 .zip 或 SKILL.md，安装前可预览",
    "skills.createWithChemClaw": "用 ChemClaw 创建",
    "skills.createWithChemClawHint": "开启新对话，由助手编写技能并在添加前征求确认",
    "skills.reviewTitle": "安装前预览",
    "skills.reviewIntro": "请阅读指令内容——安装后助手会按此执行。",
    "skills.install": "安装技能",
    "skills.bundledFiles": "附带文件",
    "skills.noSkills": "还没有技能。使用「添加技能」创建或导入。",
    "skills.confirmDelete": "确认删除",
    "skills.enabled": "启用",
    "skills.showFolder": "打开文件夹",
    "skills.files": "{count} 个文件",
    "skills.confirmReady": "— 助手现在可以在所有对话中使用它。",
    "skills.confirmOff": "已在全局关闭。若某对话已使用过，请新建对话以获得完全干净的状态。",
    "skills.confirmDeleted": "已删除。若某对话已使用过，请新建对话以获得完全干净的状态。",
    "skills.errorGeneric": "出了点问题。",
    "skills.loading": "正在加载技能…",
    "skills.noMatch": "没有匹配的技能。",
    "skills.slashTitle": "技能",
    "skills.noDescription": "无描述",
    "skills.newSkill": "新建技能",
    "skills.fieldName": "名称",
    "skills.fieldDescription": "描述",
    "skills.fieldDescriptionHint": "助手用来判断何时启用此技能的一句话说明",
    "skills.fieldInstructions": "指令",
    "skills.saveSkill": "保存技能",
    "experts.pageIntro":
      "智能体组合了提示词、工具与默认技能。启用后可在新建对话时选用；主按钮按标星默认一键开聊，也可点 ▾ 换一个。",
    "experts.enableHint":
      "启用后可选择是否出现在新建对话的 ▾ 列表中。标星的智能体是新建对话的默认选项（改标星不会更换已打开会话的智能体）。",
    "experts.enabled": "启用",
    "experts.inPicker": "出现在选择器",
    "experts.setDefault": "设为默认",
    "experts.builtin": "内置",
    "experts.defaultTitle": "新建对话的默认智能体",
    "experts.configure": "查看 {name}",
    "experts.view": "查看",
    "experts.delete": "删除",
    "experts.keep": "保留",
    "experts.deleteTitle": "删除此智能体",
    "experts.disableWarning": "禁用将归档其 {count} 个对话——仍可在「显示已归档」中查看。",
    "experts.disable": "禁用",
    "experts.keepEnabled": "保持启用",
    "experts.add": "添加智能体",
    "experts.addHint":
      "支持 GitHub 地址、本地目录，或上传 zip / .md。包内含 SKILL.md 的目录会整树装入「技能」（保留 scripts 等）；OpenClaw 的 IDENTITY/SOUL 会合成进智能体提示词；安装前可预览冲突并批量覆盖或跳过。不会自动安装运行时依赖。",
    "experts.sourceGit": "GitHub 地址",
    "experts.sourceDir": "本地目录",
    "experts.sourceZip": "上传 zip / md",
    "experts.placeholderGit": "https://github.com/acme/ops-persona",
    "experts.placeholderDir": "/path/to/personas",
    "experts.install": "安装",
    "experts.installing": "正在安装…",
    "experts.installed": "已安装 {count} 个智能体——请在下方审阅并启用。",
    "experts.installFailed": "安装失败",
    "experts.packageAgents": "智能体：{list}",
    "experts.packageSkills": "技能：{list}",
    "experts.packageIgnored": "已忽略：{list}",
    "experts.packageEmpty": "无",
    "experts.decisionOverwrite": "覆盖",
    "experts.decisionSkip": "跳过",
    "experts.overwriteAll": "全部覆盖",
    "experts.skipAll": "全部跳过",
    "experts.composedFrom": "已从 {list} 生成智能体提示词（安装后生效，非 OpenClaw 热读）",
    "experts.ignoredHint":
      "已合成进提示词的工作区文件不会出现在忽略列表；memory/ 目录本阶段不整树导入。",
    "experts.zipUnsupported":
      "当前服务未支持压缩包安装，请完全退出并重启 ChemClaw 后再试（需加载含 zip 联装的版本）。",
    "experts.detailBack": "返回",
    "experts.detailLoading": "正在加载…",
    "experts.detailLoadFailed": "无法加载此智能体详情。",
    "experts.deleteFailed": "删除失败",
    "experts.tools": "工具：{tools}",
    "experts.risk": "风险：{risk}",
    "experts.connectors": " · 连接器",
    "experts.messaging": " · 消息通道",
    "experts.mcp": " · MCP：{mcp}",
    "experts.recommendedMode": "推荐模式：{mode}。在上方启用后即可使用。",
    "experts.chatWith": "与 {name} 畅谈",
    "experts.chatWith.chat": "有什么想问的？",
    "experts.choosePersona": "选择智能体（当前默认：{name}）",
    "experts.startAs": "选择对话智能体",
    "experts.managePersonas": "管理智能体…",
    "experts.systemPrompt": "系统提示词",
    "experts.defaultSkills": "默认技能",
    "experts.skillMissing": "未安装",
    "experts.installPath": "安装路径",
    "experts.openFolder": "打开文件夹",
    "experts.builtinReadonly": "内置智能体由产品维护，提示词只读。个性化请等待「另存为副本」（后续版本）。",
    "intro.lede":
      "选一个任务开始，或直接在下方描述你的化工研究/分析需求——我会完成工作并保存结果。",
    "intro.task.memo.title": "整理一份化工主题研究备忘录",
    "intro.task.memo.sub": "澄清范围后写出可交付 Markdown，并保存为产物",
    "intro.task.memo.prompt":
      "请围绕某个化工品或材料主题整理一份研究备忘录。请先问清主题、用途边界与期望的交付形式，再开始检索与写作；最终以 Markdown 产物交付。",
    "intro.task.price.title": "查某化工品近期价格与走势要点",
    "intro.task.price.sub": "有数据则给价格表、趋势图与要点，无数据标明暂无行情",
    "intro.task.price.prompt":
      "请查询某个化工品的近期价格与走势要点。请先确认品种与区域（或市场），用可用的价格技能/数据源取数，禁止编造；有数据则给出价格表、简要要点，以及一条 fenced ```chart`（ChartSpec v1、line）趋势图（时间序列至少 2 个点时必须出图，数值与表一致）；不要用 chart-image/shell/Node 仅为聊天出图；取不到则标明暂无行情。",
    "intro.task.folder.title": "阅读本地文件夹里的资料并提炼要点",
    "intro.task.folder.sub": "我会读取已共享文件夹并总结与化工问题相关的重点",
    "intro.task.folder.act": "选择文件夹 →",
    "intro.task.folder.prompt":
      "请阅读此文件夹中的资料，提炼与化工研究/分析相关的重点，并给出简明总结。",
    "intro.act.start": "开始 →",
    "intro.act.configure": "配置 ›",
    "gate.close": "关闭",
    "intro.code.hint": "此智能体需要项目文件夹才能读取、编辑和运行代码。",
    "intro.code.pickFolder": "选择文件夹",
    "intro.chat.lede": "直接提问即可——适合快速解释与梳理，不读写本地项目。",
    "intro.chat.task1.title": "用通俗话解释一个化工概念或缩写",
    "intro.chat.task1.sub": "先确认你指的是哪个含义再解释",
    "intro.chat.task1.prompt":
      "请用通俗话解释一个化工概念或缩写。请先确认我指的是哪一个含义（必要时列出常见歧义），再给出简明解释。",
    "intro.chat.task2.title": "对比两个相近材料或工艺差在哪",
    "intro.chat.task2.sub": "先对齐对比维度，再列要点",
    "intro.chat.task2.prompt":
      "请对比两个相近的材料或工艺。请先对齐我关心的对比维度，再列出主要差异与注意点，不要写成冗长报告。",
    "intro.chat.task3.title": "帮我把一个技术问题拆成可追问的清单",
    "intro.chat.task3.sub": "先问清目标，再给出问题清单",
    "intro.chat.task3.prompt":
      "请帮我把一个技术问题拆成可继续追问的清单。请先问清我的目标与已知信息，再给出条理清晰的问题清单。",
    "intro.chain.task1.title": "拆解某个化工品从原料到最终用途",
    "intro.chain.task1.sub": "说清上下游怎么连、相关企业；需要时画出关系图",
    "intro.chain.task1.prompt":
      "请帮我拆解一个化工品从原料到最终用途的上下游关系，并说明相关企业；需要时画出带关系标签的产业链图。请先问清楚品种、用途边界和范围。",
    "intro.chain.task2.title": "找出产业链里最稀缺的环节，并给证据定级",
    "intro.chain.task2.sub": "先划定看哪些范围，再区分事实和推测",
    "intro.chain.task2.prompt":
      "请帮我找出某条化工产业链里最稀缺的环节，并给证据定级。请先问清楚主题边界和范围，再区分事实与推测。",
    "intro.chain.task3.title": "从稀缺环节看看可能对应哪些上市公司机会",
    "intro.chain.task3.sub": "先把产业环节说清楚，再对应到公司和行情",
    "intro.chain.task3.prompt":
      "请从化工产业链的稀缺环节出发，分析可能对应哪些上市公司机会。请先把产业环节说清楚，再映射到公司和行情，并标明不确定处。",
    "intro.export.lede":
      "围绕具体 SKU 与目标市场，找出有证据的候选客户，给出双评分与下一步——不是研究报告。",
    "intro.export.task1.title": "按产品 + 目标国找进口商/买家清单",
    "intro.export.task1.sub": "先问清 SKU、市场与客户类型，再检索与核验",
    "intro.export.task1.prompt":
      "请围绕某个化工产品/SKU 和目标国家，找有证据的进口商或买家清单。请先问清产品规格、目标市场、客户类型与排除条件，再开始检索；每个强结论须可追溯证据，不编造企业或联系人。",
    "intro.export.task2.title": "用海关/提单文件筛真实进口商",
    "intro.export.task2.sub": "排除货代噪声，交叉核验后再写入清单",
    "intro.export.task2.prompt":
      "请用工作区里的海关或提单文件（CSV/XLSX）筛真实进口商。请先确认产品/HS 与目标市场，过滤货代等噪声，交叉核验后再写入候选清单；收货方不等于终端买家。",
    "intro.export.task3.title": "对候选做双评分并输出可联系/待补查清单",
    "intro.export.task3.sub": "Lead Fit 与证据置信度分开；不自动外发",
    "intro.export.task3.prompt":
      "请对已收集的候选客户做 Lead Fit 与 Evidence Confidence 双评分，输出可联系、待补查与已排除清单及下一步动作。禁止把低置信候选包装成合格 Lead；不自动外发。",
    "intro.domestic.lede":
      "围绕具体 SKU 与国内区域，用园区/工商公开证据找下游客户。",
    "intro.domestic.task1.title": "按产品 + 省市/园区找国内下游客户",
    "intro.domestic.task1.sub": "先对齐产品、区域与 ICP，再拓客",
    "intro.domestic.task1.prompt":
      "请围绕某个化工产品/SKU 和国内目标区域（省/市/园区可选），找有证据的下游客户。请先问清产品、区域、客户类型与排除条件，再开始检索；不编造企业或联系方式。",
    "intro.domestic.task2.title": "核验主体与应用证据",
    "intro.domestic.task2.sub": "统一社会信用代码优先；百科不是采购证据",
    "intro.domestic.task2.prompt":
      "请对国内候选企业核验主体与应用相关证据，优先统一社会信用代码与园区/工商公开信息。证据不足标为待核验；百科或目录条目不能单独支撑合格 Lead。",
    "intro.domestic.task3.title": "输出双评分客户清单与下一步动作",
    "intro.domestic.task3.sub": "可联系 / 待补查 / 已排除；不自动外发",
    "intro.domestic.task3.prompt":
      "请对国内候选做 Lead Fit 与 Evidence Confidence 双评分，输出可联系、待补查与已排除清单及下一步动作。不自动外发或写 CRM。",
    "intro.radar.lede":
      "把有来源的招标、询盘、扩产等信号整理成可跟进商机——不是拓客名单。",
    "intro.radar.task1.title": "按产品搜近期招标/采购商机",
    "intro.radar.task1.sub": "优先可回溯来源；不伪造公告号",
    "intro.radar.task1.prompt":
      "请围绕某个化工产品/SKU 搜索近期招标或采购商机。请先问清产品与市场约束，优先使用有来源的招标检索；不得伪造公告号；无命中则如实说明。",
    "intro.radar.task2.title": "把询盘或扩产新闻整理成商机清单",
    "intro.radar.task2.sub": "信号须可回溯；口述无来源保持待审阅",
    "intro.radar.task2.prompt":
      "请把询盘、扩产或其他有来源事件整理成可跟进商机清单。请先确认产品与市场边界；每个信号保留来源定位；无 URL/文件/登记号时只请求补证，不编造。",
    "intro.radar.task3.title": "给商机打分并标出待补证项",
    "intro.radar.task3.sub": "商机分与证据置信度分开；不自动外发",
    "intro.radar.task3.prompt":
      "请对已收集商机评分，区分商机分与证据置信度，标出风险与待补证项及建议动作。不得把搜索摘要包装成可行动商机；不自动外发。",
    "intro.engagement.lede":
      "对已核验 Lead/商机产出联系策略、开发信或询盘报价草稿；发送须人工审批。",
    "intro.engagement.task1.title": "给已核验客户写开发信草稿",
    "intro.engagement.task1.sub": "草稿 ≠ 发送；无可靠邮箱只给岗位策略",
    "intro.engagement.task1.prompt":
      "请为已核验的外贸客户写一封开发信或跟进消息草稿，并给出联系策略与跟进节拍。请先确认客户、产品卖点与语言；无可靠个人邮箱时只给岗位策略与补证项。绝不自动发送。",
    "intro.engagement.task2.title": "把询盘整理成报价草稿",
    "intro.engagement.task2.sub": "走计算器，不编造单价或缺量",
    "intro.engagement.task2.prompt":
      "请把一份外贸询盘整理成报价草稿。请先对齐规格、数量、币种与交期；单价与合计必须用报价计算器，缺数量或单价则标为待审阅，绝不编造价格。最多到人工审阅，不为报价单独外发。",
    "intro.engagement.task3.title": "跑质量门禁并判断可否提交发送/CRM 审批",
    "intro.engagement.task3.sub": "门禁未通过只给修订清单；须用户明确要求才发送",
    "intro.engagement.task3.prompt":
      "请对已写好的开发信或报价草稿跑销售质量门禁，说明是否可通过并能否进入发送或 CRM 审批。门禁未通过只给修订/补证清单；发送与 CRM 写入须用户明确要求且走现有审批，绝不自动外发。",
    "experts.persona.cowork.name": "ChemClaw",
    "experts.persona.cowork.tagline": "产出可交付成果——研究、分析、脚本",
    "experts.persona.code.name": "代码",
    "experts.persona.code.tagline": "在代码库中工作——文件、git、shell",
    "experts.persona.chat.name": "问答",
    "experts.persona.chat.tagline": "快速提问——无需工作区",
    "experts.persona.ops.name": "运维龙虾",
    "experts.persona.ops.tagline": "运维与排查——手册、日志、基础设施",
    "experts.persona.chain-lobster.name": "产业链龙虾",
    "experts.persona.chain-lobster.tagline": "化工产业链拆解 · 稀缺环节 · 证据与标的映射",
    "experts.persona.export-sales-lobster.name": "外贸拓客龙虾",
    "experts.persona.export-sales-lobster.tagline":
      "化工外贸拓客 · 证据核验 · 双评分与下一步动作",
    "experts.persona.domestic-sales-lobster.name": "内贸拓客龙虾",
    "experts.persona.domestic-sales-lobster.tagline":
      "化工内贸拓客 · 园区工商证据 · 双评分与下一步动作",
    "experts.persona.opportunity-radar-lobster.name": "商机雷达龙虾",
    "experts.persona.opportunity-radar-lobster.tagline":
      "化工信号进 · 商机出 · 证据评分与下一步",
    "experts.persona.export-engagement-lobster.name": "外贸转化龙虾",
    "experts.persona.export-engagement-lobster.tagline":
      "化工外贸转化 · 草稿跟进 · 询盘报价与人工发送",
    "experts.persona.platform-rewrite-lobster.name": "化工内容重构龙虾",
    "experts.persona.platform-rewrite-lobster.tagline":
      "化工内容重构 · 多平台适配 · 事实保持 · 合规质检",
    "intro.rewrite.lede":
      "把化工素材改成适合平台发布的成稿——保留事实、区分语气、扫敏感词；不自动发帖。",
    "intro.rewrite.task1.title": "改成小红书配文",
    "intro.rewrite.task1.sub": "标题/封面字/正文/标签，保留规格事实",
    "intro.rewrite.task1.prompt":
      "请把下面化工素材改写成小红书图文（含标题、封面字、正文、标签与改写说明）。不要新增原文没有的 CAS、纯度、认证或安全承诺：\n\n",
    "intro.rewrite.task2.title": "改成抖音口播稿",
    "intro.rewrite.task2.sub": "口语短句 + 画面提示 + 话题",
    "intro.rewrite.task2.prompt":
      "请把下面化工素材改写成抖音口播稿（含口播稿、画面提示、话题与改写说明）。事实锚点保持不变，语气要口语化：\n\n",
    "intro.rewrite.task3.title": "合规过稿（扫敏感词）",
    "intro.rewrite.task3.sub": "先出简报再改写，门禁不过则修订",
    "intro.rewrite.task3.prompt":
      "请对下面文案做化工内容合规过稿：先 RewriteBrief，再按目标平台改写，运行敏感词扫描与质量门禁；未通过则修订。目标平台：小红书。原文：\n\n",
    "boot.starting": "正在启动 ChemClaw…",
    "boot.restoring": "正在恢复你的对话…",
    "sidebar.newConversation": "新建对话",
    "sidebar.recent": "最近对话",
    "sidebar.pinned": "已置顶",
    "sidebar.empty": "还没有对话。",
    "sidebar.settings": "设置",
    "composer.placeholder": "向 ChemClaw 提问…（可拖放或粘贴文件）",
    "composer.placeholder.code": "让 ChemClaw 编写、修复或解释…（可拖放或粘贴文件）",
    "composer.placeholder.chat": "想问什么都可以…（可拖放或粘贴文件）",
    "composer.placeholder.cowork": "向 ChemClaw 提问…（可拖放或粘贴文件）",
    "composer.send": "发送",
    "composer.stop": "停止",
    "composer.attach": "添加附件",
    "composer.mode": "模式",
    "composer.attach.photo": "图片或照片",
    "composer.attach.pdf": "PDF",
    "composer.attach.other": "其他文件",
    "composer.mode.discuss.label": "讨论",
    "composer.mode.discuss.description": "聊天和探索，不编辑文件或执行命令",
    "composer.mode.interactive.label": "请求批准",
    "composer.mode.interactive.description": "编辑或执行命令前先请求批准",
    "composer.mode.auto.label": "完全访问",
    "composer.mode.auto.description": "无需询问即可执行所有操作",
    "composer.mode.inbox": "将批准请求发送到收件箱",
    "composer.mode.inboxHelp": "批准和问题将进入收件箱，Agent 会继续工作。",
    "sidebar.emptyProject": "这个项目还没有对话。",
    "sidebar.emptySearch": "没有匹配的对话。",
    "sidebar.cloud.notice": "未登录 — 一键连接需要 ChemClaw 云连接服务",
    "sidebar.cloud.signIn": "登录 ChemClaw 云连接服务",
    "sidebar.cloud.signedIn": "已登录 ChemClaw 云连接服务",
    "sidebar.cloud.comingSoon": "ChemClaw 云连接即将上线",
    "cloud.oneClickUnavailable": "一键连接暂不可用，请使用手动添加 Token",
    "sidebar.localUser": "本机用户",
    "sidebar.editProfile": "编辑资料",
    "settings.localProfile.title": "本机资料",
    "settings.localProfile.sub": "显示在左下角，仅保存在这台电脑，与云登录无关。",
    "settings.localProfile.name": "显示名称",
    "settings.localProfile.nameHelp": "留空则显示「本机用户」。",
    "settings.localProfile.saveName": "保存名称",
    "settings.localProfile.avatar": "头像",
    "settings.localProfile.choose": "选择图片",
    "settings.localProfile.clear": "清除头像",
    "settings.localProfile.avatarHelp": "支持 JPEG / PNG / WebP，最大 2MB。",
    "settings.localProfile.saved": "已保存",
    "settings.localProfile.error": "保存失败",
    "settings.title": "设置",
    "settings.general": "通用",
    "settings.language": "语言",
    "settings.language.zh": "简体中文",
    "settings.language.en": "English",
    "settings.runSetup": "重新运行设置",
    "settings.voiceDesktop": "语音输入设置仅在 ChemClaw 桌面应用中可用。",
    "settings.gallery": "ChemClaw 团队精选的协作助手，可在安装前查看其能力。",
    "memory.title": "记忆",
    "memory.subtitle":
      "ChemClaw 可在对话之间记住对你有用的长期偏好。下面列出它目前了解的全部内容。",
    "memory.rememberNew": "记住新的长期偏好",
    "memory.rememberHelp":
      "你在对话中提到的长期偏好会被保存并用于之后的对话——每次保存都会出现一条可撤销的提示。关闭后不再保存新的长期记忆；下方已有内容仍会继续使用，直到你删除。",
    "memory.enabledMessage": "之后对话里分享的细节会被记住，以便长期更好地协助你。",
    "memory.disabledMessage":
      "已停止保存新的长期记忆。已有内容仍会用于新对话——如需忘记，请在下方删除。",
    "memory.learnedTitle": "已记住的内容",
    "memory.learnedHelp":
      "自动从对话中保存。可修正错误或删除。编辑与删除只影响新对话；已打开的对话仍保留启动时的知识。",
    "memory.forgetAll": "忘记全部…",
    "memory.empty": "暂无内容。当你在对话中提到长期偏好，或说「记住…」时，会出现在这里。",
    "memory.userRulesTitle": "你的长期指令",
    "memory.userRulesHelp":
      "你主动设置的指令在每次对话中都会遵循，且优先于自动学到的记忆。",
    "memory.userRulesPlaceholder":
      "我使用读屏软件——不要用表格，并描述图片\n日期请使用 YYYY-MM-DD",
    "memory.save": "保存",
    "memory.savedForNewChats": "已保存——仅对新对话生效。已打开的对话仍使用启动时的指令。",
    "memory.loading": "加载中…",
    "memory.fix": "修改",
    "memory.delete": "删除",
    "memory.cancel": "取消",
    "memory.confirmDeleteAll":
      "删除全部已记住的内容？\n\n此操作无法撤销。已打开的对话仍保留启动时的知识；新对话将从空白开始。",
    "memory.deleteAllDone":
      "已删除全部记忆。新对话将从空白开始；已打开的对话仍保留启动时的知识。",
    "memory.toastSaved": "我会记住",
    "memory.toastUpdated": "我更新了记忆",
    "memory.toastUndo": "撤销",
    "memory.toastForgotten": "已忘记",
    "memory.toastRestored": "已恢复之前内容",
    "settings.autoStart": "登录后自动启动 ChemClaw。",
    "onboarding.welcome": "欢迎使用 ChemClaw",
    "onboarding.model": "选择模型提供商即可开始 — ChemClaw 使用你自己的密钥，并将其保留在这台设备上。",
    "onboarding.oauth": "ChemClaw 为 20 多种工具处理 OAuth — 无需开发者控制台，也无需粘贴密钥。",
    "update.available": "有可用更新",
    "update.ready": "ChemClaw v{version} 已准备好安装。",
    "stage.install": "安装",
    "stage.mount": "挂载",
    "stage.mermaid": "Mermaid 图表",
    "mermaid.diagram": "图形",
    "mermaid.source": "源码",
    "mermaid.fullscreen": "全屏",
    "mermaid.exportSvg": "导出 SVG",
    "mermaid.exportPng": "导出 PNG",
    "mermaid.renderError": "无法渲染此图表",
    "mermaid.tooLong": "图表源码过长，无法渲染",
    "mermaid.pngTooLarge": "图片尺寸过大，无法导出 PNG",
    "mermaid.exportFailed": "导出失败",
    "mermaid.loading": "正在渲染图表…",
    "mermaid.repairing": "正在修正图表…",
    "mermaid.repair": "修复图表",
    "mermaid.repairFailed": "无法自动修复此图表",
    "mermaid.loadFailed": "图表库加载失败",
    "mermaid.retryLoad": "重新加载",
    "chart.fullscreen": "全屏",
    "chart.renderError": "无法渲染此图表",
    "chart.ohlc.open": "开盘",
    "chart.ohlc.high": "最高",
    "chart.ohlc.low": "最低",
    "chart.ohlc.close": "收盘",
    "chart.stage.interval": "价格区间",
    "chart.stage.drivers": "行情驱动因素",
    "chart.stage.tone.up": "阶段性上涨区间",
    "chart.stage.tone.down": "阶段性下跌区间",
    "chart.stage.tone.side": "阶段性横盘区间",
    "chart.candle.hint": "拖动平移 · 滚轮缩放",
    "chart.candle.pinHint": "单击固定详情 · Esc 取消",
    "chart.series.hint": "十字线定位最近日期",
    "chart.series.pinHint": "单击固定详情 · Esc 取消",
    "ask.recommended": "推荐",
    "ask.previous": "上一个问题",
    "ask.question": "问题",
    "ask.progress": "第 {current}/{total} 个",
    "ask.typeOwn": "或输入自己的答案…",
    "ask.yourAnswer": "请输入答案…",
  },
  "en-US": {
    "nav.conversations": "Conversations",
    "nav.skills": "Skills",
    "nav.experts": "Agents",
    "nav.leads": "Leads",
    "leads.title": "Lead list",
    "leads.subtitle": "Import prospecting JSON, export CSV, mark status locally. No auto-email or CRM.",
    "leads.importJson": "Import JSON",
    "leads.exportCsv": "Export CSV",
    "leads.importInvalid": "Invalid lead-list JSON (needs a leads array with company and sales_status).",
    "leads.counts": "Contactable {contactable} · Needs review {needsReview} · Excluded {excluded} · Total {total}",
    "leads.filterAll": "All",
    "leads.filterContactable": "Contactable",
    "leads.filterNeedsReview": "Needs review",
    "leads.filterExcluded": "Excluded",
    "leads.empty": "No leads yet. Generate a list with a prospecting lobster and import the JSON.",
    "leads.col.company": "Company",
    "leads.col.type": "Type",
    "leads.col.fit": "Fit",
    "leads.col.conf": "Evidence",
    "leads.col.next": "Next action",
    "leads.col.status": "Status",
    "leads.col.notes": "Notes",
    "leads.col.actions": "Actions",
    "leads.markContactable": "Contactable",
    "leads.markNeedsReview": "Needs review",
    "leads.markExcluded": "Exclude",
    "leads.defaultExcludeReason": "Excluded by user",
    "leads.footer": "Status is stored in this browser. No send/CRM on this page; research/rescore only inject chat intents.",
    "leads.showDetail": "Details",
    "leads.hideDetail": "Hide",
    "leads.continueResearch": "Continue research",
    "leads.researchHint": "Injects a research request into the current chat; no auto-send.",
    "leads.rescore": "Adjust ICP & rescore",
    "leads.rescoreHint": "Injects a rescore request; the workbench never changes scores silently.",
    "leads.runSummary": "Prospecting checkpoint: run {runId} · stage {stage} · budget {budget}",
    "leads.detail.match": "Match reason",
    "leads.detail.evidence": "Key evidence",
    "leads.detail.next": "Next action",
    "leads.detail.exclude": "Exclude reason",
    "sendApproval.submit": "Submit send for approval",
    "sendApproval.hint": "Asks the assistant to call email_send; you still confirm on the approval card. No auto-send.",
    "crmWriteApproval.submit": "Submit CRM write for approval",
    "crmWriteApproval.hint":
      "Asks the assistant to call hubspot_log_note; you still confirm on the approval card. No auto CRM write.",
    "crmCreateContact.submit": "Submit create-contact for approval",
    "crmCreateContact.hint":
      "Asks the assistant to call hubspot_create_contact; you still confirm on the approval card. No auto create.",
    "crmUpdateObject.submit": "Submit CRM field update for approval",
    "crmUpdateObject.hint":
      "Asks the assistant to call hubspot_update_object; you still confirm on the approval card. No auto field update.",
    "crmCreateTask.submit": "Submit CRM create-task for approval",
    "crmCreateTask.hint":
      "Asks the assistant to call hubspot_create_task; you still confirm on the approval card. No auto create task.",
    "nav.scheduled": "Automations",
    "nav.connections": "Connectors",
    "nav.settings": "Settings",
    "skills.pageTitle": "Skills",
    "skills.pageIntro": "Reusable workflows and instructions. Skills turned off here stay off in every conversation.",
    "skills.title": "Skills",
    "skills.subtitle": "Reusable instructions the worker can follow in every conversation. Off here means off everywhere.",
    "skills.add": "Add skill",
    "skills.writeMyself": "Write it myself",
    "skills.writeMyselfHint": "A name, a description, and the instructions",
    "skills.importFile": "Import a file",
    "skills.importFileHint": "A .zip or SKILL.md someone shared — you review before it installs",
    "skills.createWithChemClaw": "Create with ChemClaw",
    "skills.createWithChemClawHint": "Starts a conversation — the worker builds it and asks before adding it to your skills",
    "skills.reviewTitle": "Review before installing",
    "skills.reviewIntro": "Read the instructions — installing a skill means the worker will follow them.",
    "skills.install": "Install skill",
    "skills.bundledFiles": "Bundled files",
    "skills.noSkills": "No skills yet. Use Add skill to create or import one.",
    "skills.confirmDelete": "Confirm delete",
    "skills.enabled": "On",
    "skills.showFolder": "Show folder",
    "skills.files": "{count} files",
    "skills.confirmReady": "— the worker can now use it in every conversation.",
    "skills.confirmOff": "turned off everywhere. If a conversation already used it, start a new one for a completely clean slate.",
    "skills.confirmDeleted": "removed. If a conversation already used it, start a new one for a completely clean slate.",
    "skills.errorGeneric": "Something went wrong.",
    "skills.loading": "Loading skills…",
    "skills.noMatch": "No matching skills.",
    "skills.slashTitle": "Skills",
    "skills.noDescription": "no description",
    "skills.newSkill": "New skill",
    "skills.fieldName": "Name",
    "skills.fieldDescription": "Description",
    "skills.fieldDescriptionHint": "One line the worker uses to decide when this applies",
    "skills.fieldInstructions": "Instructions",
    "skills.saveSkill": "Save skill",
    "experts.pageIntro":
      "Agents combine prompts, tools, and default skills. Enable one to use it for new chats — the primary button uses the starred default; ▾ lets you pick another.",
    "experts.enableHint":
      "After enabling, choose whether it appears in the new-chat ▾ list. The starred agent is the default for new conversations (changing the star does not rebind an open session).",
    "experts.enabled": "Enabled",
    "experts.inPicker": "In picker",
    "experts.setDefault": "Set default",
    "experts.builtin": "built-in",
    "experts.defaultTitle": "Default agent for new chats",
    "experts.configure": "View {name}",
    "experts.view": "View",
    "experts.delete": "Delete",
    "experts.keep": "Keep",
    "experts.deleteTitle": "Delete this agent",
    "experts.disableWarning": "Disabling archives its {count} conversation(s) — they stay available under “Show archived”.",
    "experts.disable": "Disable",
    "experts.keepEnabled": "Keep enabled",
    "experts.add": "Add agents",
    "experts.addHint":
      "GitHub URL, local directory, or upload a zip / .md. Folders with SKILL.md install into Skills (full tree). OpenClaw IDENTITY/SOUL are composed into the agent prompt. Preview conflicts and apply overwrite/skip in bulk. Runtime dependencies are not auto-installed.",
    "experts.sourceGit": "GitHub URL",
    "experts.sourceDir": "Local directory",
    "experts.sourceZip": "Upload zip / md",
    "experts.placeholderGit": "https://github.com/acme/ops-persona",
    "experts.placeholderDir": "/path/to/personas",
    "experts.install": "Install",
    "experts.installing": "Installing…",
    "experts.installed": "Installed {count} agent(s) — review and enable below.",
    "experts.installFailed": "install failed",
    "experts.packageAgents": "Agents: {list}",
    "experts.packageSkills": "Skills: {list}",
    "experts.packageIgnored": "Ignored: {list}",
    "experts.packageEmpty": "none",
    "experts.decisionOverwrite": "Overwrite",
    "experts.decisionSkip": "Skip",
    "experts.overwriteAll": "Overwrite all",
    "experts.skipAll": "Skip all",
    "experts.composedFrom": "Agent prompt composed from {list} (applied on install; not OpenClaw live files)",
    "experts.ignoredHint":
      "Workspace files folded into the prompt are omitted from Ignored; the memory/ directory is not imported as a tree.",
    "experts.zipUnsupported":
      "This server build does not support zip install. Fully quit and restart ChemClaw so the zip co-install backend is loaded.",
    "experts.detailBack": "Back",
    "experts.detailLoading": "Loading…",
    "experts.detailLoadFailed": "Could not load this agent.",
    "experts.deleteFailed": "delete failed",
    "experts.tools": "Tools: {tools}",
    "experts.risk": "Risk: {risk}",
    "experts.connectors": " · connectors",
    "experts.messaging": " · messaging",
    "experts.mcp": " · mcp: {mcp}",
    "experts.recommendedMode": "Recommended mode: {mode}. Enable it above to use it.",
    "experts.chatWith": "Chatting with {name}",
    "experts.chatWith.chat": "What can I answer?",
    "experts.choosePersona": "Choose agent (default: {name})",
    "experts.startAs": "Start a conversation as",
    "experts.managePersonas": "Manage agents…",
    "experts.systemPrompt": "System prompt",
    "experts.defaultSkills": "Default skills",
    "experts.skillMissing": "Not installed",
    "experts.installPath": "Install path",
    "experts.openFolder": "Open folder",
    "experts.builtinReadonly":
      "Built-in agents are product-maintained and read-only. Personalize later via “Save as copy”.",
    "intro.lede":
      "Pick a task to start, or describe your chemical research or analysis below — I'll do the work and save the result.",
    "intro.task.memo.title": "Draft a chemical-topic research memo",
    "intro.task.memo.sub": "Clarify scope, then write a deliverable Markdown and save it as an artifact",
    "intro.task.memo.prompt":
      "Please prepare a research memo on a chemical product or material topic. First clarify the topic, end-use boundary, and desired deliverable format, then research and write; deliver as a Markdown artifact.",
    "intro.task.price.title": "Look up recent prices and trend highlights for a chemical",
    "intro.task.price.sub": "Include a price table, trend chart, and highlights when data exists; otherwise say no market data",
    "intro.task.price.prompt":
      "Please look up recent prices and trend highlights for a chemical. First confirm the product and region (or market), use available price skills/data sources, and never invent numbers; if data exists, give a price table, brief highlights, and one fenced ```chart` (ChartSpec v1, line) trend chart whenever the time series has at least 2 points (numbers must match the table); do not use chart-image/shell/Node merely to visualize in chat; otherwise say no market data is available.",
    "intro.task.folder.title": "Read a local folder and extract the key points",
    "intro.task.folder.sub": "I'll read shared folders and summarize what matters for chemical questions",
    "intro.task.folder.act": "Pick a folder →",
    "intro.task.folder.prompt":
      "Please read the materials in this folder, extract the points most relevant to chemical research or analysis, and give a concise summary.",
    "intro.act.start": "Start →",
    "intro.act.configure": "Configure ›",
    "gate.close": "Close",
    "intro.code.hint": "This agent needs a project folder to read, edit, and run code.",
    "intro.code.pickFolder": "Choose folder",
    "intro.chat.lede": "Just ask — quick explanations and clarifications, no local project.",
    "intro.chat.task1.title": "Explain a chemical concept or abbreviation in plain language",
    "intro.chat.task1.sub": "Confirm which meaning you intend, then explain",
    "intro.chat.task1.prompt":
      "Please explain a chemical concept or abbreviation in plain language. First confirm which meaning I intend (list common ambiguities if needed), then give a concise explanation.",
    "intro.chat.task2.title": "Compare two similar materials or processes",
    "intro.chat.task2.sub": "Align comparison dimensions first, then list the points",
    "intro.chat.task2.prompt":
      "Please compare two similar materials or processes. First align the dimensions I care about, then list the main differences and caveats — keep it short, not a long report.",
    "intro.chat.task3.title": "Turn a technical issue into a follow-up question list",
    "intro.chat.task3.sub": "Clarify the goal first, then give a question list",
    "intro.chat.task3.prompt":
      "Please turn a technical issue into a list of follow-up questions. First clarify my goal and what I already know, then give a clear question list.",
    "intro.chain.task1.title": "Map a chemical from feedstock to end use",
    "intro.chain.task1.sub": "Clarify upstream/downstream links and firms; draw a diagram when useful",
    "intro.chain.task1.prompt":
      "Please map a chemical from feedstock to end use, including relevant firms; draw a value-chain diagram with edge labels when useful. First clarify the product, end-use boundary, and scope.",
    "intro.chain.task2.title": "Find the scarcest link and grade the evidence",
    "intro.chain.task2.sub": "Set scope first, then separate facts from guesses",
    "intro.chain.task2.prompt":
      "Please find the scarcest link in a chemical value chain and grade the evidence. First clarify the topic boundary and scope, then separate facts from speculation.",
    "intro.chain.task3.title": "From scarce links to listed-company opportunities",
    "intro.chain.task3.sub": "Ground the chain first, then map to companies and markets",
    "intro.chain.task3.prompt":
      "Starting from scarce links in a chemical value chain, analyze possible listed-company opportunities. Ground the industrial links first, then map to companies and markets, and mark uncertainties.",
    "intro.export.lede":
      "From a concrete SKU and target market, find evidenced buyer candidates with dual scores and next actions — not a research report.",
    "intro.export.task1.title": "Find importers/buyers by product + country",
    "intro.export.task1.sub": "Clarify SKU, market, and ICP first, then research and verify",
    "intro.export.task1.prompt":
      "Please find evidenced importers or buyers for a chemical product/SKU and target country. First clarify specs, market, customer type, and exclusions; every strong claim needs evidence — never invent companies or contacts.",
    "intro.export.task2.title": "Filter real importers from customs/BOL files",
    "intro.export.task2.sub": "Drop forwarder noise; cross-check before listing",
    "intro.export.task2.prompt":
      "Please filter real importers from customs or bill-of-lading files (CSV/XLSX) in the workspace. Confirm product/HS and market first, exclude freight-forwarder noise, and cross-check before listing — consignee ≠ end buyer.",
    "intro.export.task3.title": "Dual-score candidates into contactable / needs-research lists",
    "intro.export.task3.sub": "Separate Lead Fit from evidence confidence; never auto-send",
    "intro.export.task3.prompt":
      "Please dual-score collected candidates with Lead Fit and Evidence Confidence, and output contactable, needs-research, and excluded lists plus next actions. Do not package low-confidence hits as qualified leads; never auto-send.",
    "intro.domestic.lede":
      "From a concrete SKU and China region, find downstream buyers with park/registry public evidence.",
    "intro.domestic.task1.title": "Find domestic buyers by product + province/park",
    "intro.domestic.task1.sub": "Align product, region, and ICP before prospecting",
    "intro.domestic.task1.prompt":
      "Please find evidenced downstream buyers for a chemical product/SKU and a China target region (province/city/park optional). First clarify product, region, customer type, and exclusions; never invent companies or contacts.",
    "intro.domestic.task2.title": "Verify entity and application evidence",
    "intro.domestic.task2.sub": "Prefer Unified Social Credit Code; encyclopedia ≠ purchase proof",
    "intro.domestic.task2.prompt":
      "Please verify entity and application evidence for domestic candidates, preferring Unified Social Credit Code and park/registry public records. Mark weak evidence as needs review; encyclopedia or directory hits alone cannot support a qualified lead.",
    "intro.domestic.task3.title": "Output dual-scored lists and next actions",
    "intro.domestic.task3.sub": "Contactable / needs-research / excluded; never auto-send",
    "intro.domestic.task3.prompt":
      "Please dual-score domestic candidates with Lead Fit and Evidence Confidence, and output contactable, needs-research, and excluded lists plus next actions. Never auto-send or write CRM.",
    "intro.radar.lede":
      "Turn sourced tenders, inquiries, and expansion signals into followable opportunities — not a prospecting list.",
    "intro.radar.task1.title": "Search recent tenders/procurement by product",
    "intro.radar.task1.sub": "Prefer traceable sources; never invent notice IDs",
    "intro.radar.task1.prompt":
      "Please search recent tenders or procurement opportunities for a chemical product/SKU. First clarify product and market constraints; prefer sourced tender search; never invent notice IDs; say empty honestly if none.",
    "intro.radar.task2.title": "Turn inquiries or expansion news into an opportunity list",
    "intro.radar.task2.sub": "Signals must be traceable; unsourced hearsay stays NeedsReview",
    "intro.radar.task2.prompt":
      "Please turn inquiries, expansions, or other sourced events into a followable opportunity list. Confirm product and market first; keep locators for every signal; if no URL/file/registry id, only ask for more evidence — never invent.",
    "intro.radar.task3.title": "Score opportunities and flag evidence gaps",
    "intro.radar.task3.sub": "Separate opportunity score from evidence confidence; never auto-send",
    "intro.radar.task3.prompt":
      "Please score collected opportunities, separate opportunity score from evidence confidence, and flag risks, gaps, and next actions. Do not package search snippets as actionable opportunities; never auto-send.",
    "intro.engagement.lede":
      "For verified leads/opportunities, draft outreach or inquiry quotes; sending requires human approval.",
    "intro.engagement.task1.title": "Draft outreach for a verified buyer",
    "intro.engagement.task1.sub": "Draft ≠ send; without a reliable email, give role strategy only",
    "intro.engagement.task1.prompt":
      "Please draft an outreach or follow-up message for a verified export buyer, plus contact strategy and follow-up cadence. First confirm the account, product angles, and language; without a reliable personal email, give role strategy and evidence gaps only. Never auto-send.",
    "intro.engagement.task2.title": "Turn an inquiry into a quote draft",
    "intro.engagement.task2.sub": "Use the calculator; never invent unit prices or quantities",
    "intro.engagement.task2.prompt":
      "Please turn an export inquiry into a quote draft. First align specs, quantity, currency, and lead time; totals must use the quote calculator — missing quantity or unit price means NeedsReview, never invent prices. Stop at human review; do not send quotes automatically.",
    "intro.engagement.task3.title": "Run quality gate and check send/CRM approval readiness",
    "intro.engagement.task3.sub": "If gate fails, only revise; send only on explicit user request",
    "intro.engagement.task3.prompt":
      "Please run the sales quality gate on a finished outreach or quote draft and say whether it can enter send or CRM approval. If it fails, only give revision/evidence gaps; send and CRM writes need an explicit user request plus existing approvals — never auto-send.",
    "experts.persona.cowork.name": "ChemClaw",
    "experts.persona.cowork.tagline": "Produce a deliverable — research, analysis, scripts.",
    "experts.persona.code.name": "Code",
    "experts.persona.code.tagline": "Work in a codebase — files, git, shell.",
    "experts.persona.chat.name": "Chat",
    "experts.persona.chat.tagline": "Quick questions — no workspace.",
    "experts.persona.ops.name": "Ops Lobster",
    "experts.persona.ops.tagline": "Operate and investigate — runbooks, logs, infrastructure.",
    "experts.persona.chain-lobster.name": "Chain Lobster",
    "experts.persona.chain-lobster.tagline":
      "Chemical value-chain mapping · scarce links · evidence and equity mapping",
    "experts.persona.export-sales-lobster.name": "Export Sales Lobster",
    "experts.persona.export-sales-lobster.tagline":
      "Chemical prospecting · evidence qualification · dual scores and next actions",
    "experts.persona.domestic-sales-lobster.name": "Domestic Sales Lobster",
    "experts.persona.domestic-sales-lobster.tagline":
      "China domestic prospecting · park/registry evidence · dual scores and next actions",
    "experts.persona.opportunity-radar-lobster.name": "Opportunity Radar Lobster",
    "experts.persona.opportunity-radar-lobster.tagline":
      "Signals in · opportunities out · scored evidence and next actions",
    "experts.persona.export-engagement-lobster.name": "Export Engagement Lobster",
    "experts.persona.export-engagement-lobster.tagline":
      "Export conversion · drafts, inquiry quotes · human send after review",
    "experts.persona.platform-rewrite-lobster.name": "Chem Content Rewrite Lobster",
    "experts.persona.platform-rewrite-lobster.tagline":
      "Chem content rewrite · multi-platform fit · fact lock · policy gate",
    "intro.rewrite.lede":
      "Rewrite chem copy for platforms—keep facts, shift tone, scan risky claims; never auto-post.",
    "intro.rewrite.task1.title": "Rewrite for Xiaohongshu",
    "intro.rewrite.task1.sub": "Title / cover / body / tags; keep spec facts",
    "intro.rewrite.task1.prompt":
      "Rewrite the following chemical copy for Xiaohongshu (title, cover line, body, tags, rewrite notes). Do not invent CAS, purity, certifications, or safety guarantees absent from the source:\n\n",
    "intro.rewrite.task2.title": "Rewrite as Douyin script",
    "intro.rewrite.task2.sub": "Spoken short lines + shot hints + topics",
    "intro.rewrite.task2.prompt":
      "Rewrite the following chemical copy as a Douyin spoken script (script, shot hints, topics, rewrite notes). Keep fact anchors; make the tone conversational:\n\n",
    "intro.rewrite.task3.title": "Compliance pass (scan claims)",
    "intro.rewrite.task3.sub": "Brief → rewrite → gate; revise if not pass",
    "intro.rewrite.task3.prompt":
      "Run a chem content compliance pass: RewriteBrief, platform rewrite, lexicon scan, and quality gate; revise until pass. Target platform: Xiaohongshu. Source:\n\n",
    "boot.starting": "Starting ChemClaw…",
    "boot.restoring": "Restoring your conversation…",
    "sidebar.newConversation": "New conversation",
    "sidebar.recent": "Recent",
    "sidebar.pinned": "Pinned",
    "sidebar.empty": "No conversations yet.",
    "sidebar.settings": "Settings",
    "composer.placeholder": "Ask ChemClaw… (drop or paste files)",
    "composer.placeholder.code": "Ask ChemClaw to build, fix, or explain… (drop or paste files)",
    "composer.placeholder.chat": "Ask anything… (drop or paste files)",
    "composer.placeholder.cowork": "Ask the coworker… (drop or paste files)",
    "composer.send": "Send",
    "composer.stop": "Stop",
    "composer.attach": "Attach",
    "composer.mode": "Mode",
    "composer.attach.photo": "Photo or image",
    "composer.attach.pdf": "PDF",
    "composer.attach.other": "Other files",
    "composer.mode.discuss.label": "Discuss",
    "composer.mode.discuss.description": "Chat and explore — no edits or commands",
    "composer.mode.interactive.label": "Ask for approval",
    "composer.mode.interactive.description": "Ask before edits and commands",
    "composer.mode.auto.label": "Full access",
    "composer.mode.auto.description": "Run everything without asking",
    "composer.mode.inbox": "Send approvals to Inbox",
    "composer.mode.inboxHelp": "Approvals and questions go to the Inbox; the agent keeps working.",
    "sidebar.emptyProject": "No conversations in this project yet.",
    "sidebar.emptySearch": "No matching conversations.",
    "sidebar.cloud.notice": "Not signed in — one-click connections need ChemClaw cloud connection service",
    "sidebar.cloud.signIn": "Sign in to ChemClaw cloud connection service",
    "sidebar.cloud.signedIn": "Signed in to ChemClaw cloud connection service",
    "sidebar.cloud.comingSoon": "ChemClaw cloud connection is coming soon",
    "cloud.oneClickUnavailable": "One-click connect is unavailable — add a token manually",
    "sidebar.localUser": "Local user",
    "sidebar.editProfile": "Edit profile",
    "settings.localProfile.title": "Local profile",
    "settings.localProfile.sub": "Shown in the bottom-left corner. Stored only on this computer — not linked to cloud sign-in.",
    "settings.localProfile.name": "Display name",
    "settings.localProfile.nameHelp": "Leave blank to show “Local user”.",
    "settings.localProfile.saveName": "Save name",
    "settings.localProfile.avatar": "Avatar",
    "settings.localProfile.choose": "Choose image",
    "settings.localProfile.clear": "Clear avatar",
    "settings.localProfile.avatarHelp": "JPEG, PNG, or WebP — max 2MB.",
    "settings.localProfile.saved": "Saved",
    "settings.localProfile.error": "Could not save",
    "settings.title": "Settings",
    "settings.general": "General",
    "settings.language": "Language",
    "settings.language.zh": "Simplified Chinese",
    "settings.language.en": "English",
    "settings.runSetup": "Run setup again",
    "settings.voiceDesktop": "Voice Input setup is available in the ChemClaw desktop app.",
    "settings.gallery": "Curated coworkers from the ChemClaw team — see what each can do before installing.",
    "memory.title": "Memory",
    "memory.subtitle":
      "ChemClaw can remember useful long-term preferences between conversations. Everything it knows is listed here.",
    "memory.rememberNew": "Remember new long-term preferences",
    "memory.rememberHelp":
      "Lasting preferences you mention in chat are saved and used in future conversations — you'll see a small note each time, with one-tap Undo. Turning this off stops saving NEW long-term memory; anything already below is still used until you delete it.",
    "memory.enabledMessage":
      "Details you share from future conversations will be remembered, so ChemClaw can be more helpful over time.",
    "memory.disabledMessage":
      "I'll stop saving new long-term memory. What I already know is kept and still used — delete anything below you'd rather I forget.",
    "memory.learnedTitle": "What I've learned about you",
    "memory.learnedHelp":
      "Saved automatically from your conversations. Fix anything that's wrong — or delete it. Edits and deletions apply to new conversations; ones you already have open keep what they knew when they started.",
    "memory.forgetAll": "Forget everything…",
    "memory.empty":
      "Nothing yet. When you mention a lasting preference in chat — or say “remember that…” — it will show up here.",
    "memory.userRulesTitle": "Your long-term instructions",
    "memory.userRulesHelp":
      "Instructions you set yourself are followed in every conversation and outrank automatically learned memories.",
    "memory.userRulesPlaceholder":
      "I use a screen reader — no tables, describe any image\nUse YYYY-MM-DD for dates",
    "memory.save": "Save",
    "memory.savedForNewChats":
      "Saved — applies to new conversations. Ones you already have open keep the instructions they started with.",
    "memory.loading": "Loading…",
    "memory.fix": "Edit",
    "memory.delete": "Delete",
    "memory.cancel": "Cancel",
    "memory.confirmDeleteAll":
      "Delete everything that's been remembered about you?\n\nThis can't be undone. Conversations you already have open still know what they knew — new conversations start with a clean slate.",
    "memory.deleteAllDone":
      "Everything I remembered has been deleted. New conversations start fresh; ones you already have open still know what they knew when they started.",
    "memory.toastSaved": "I'll remember that",
    "memory.toastUpdated": "I've updated what I remember",
    "memory.toastUndo": "Undo",
    "memory.toastForgotten": "Okay — forgotten.",
    "memory.toastRestored": "Okay — put back the way it was.",
    "settings.autoStart": "Launch ChemClaw automatically when you sign in.",
    "onboarding.welcome": "Welcome to ChemClaw",
    "onboarding.model": "Pick a model provider to get started — ChemClaw runs on your own key and keeps it on this computer.",
    "onboarding.oauth": "ChemClaw handles OAuth for 20+ tools — no developer consoles and no pasted keys.",
    "update.available": "Update available",
    "update.ready": "ChemClaw v{version} is ready to install.",
    "stage.install": "Install",
    "stage.mount": "Mount",
    "stage.mermaid": "Mermaid diagram",
    "mermaid.diagram": "Diagram",
    "mermaid.source": "Source",
    "mermaid.fullscreen": "Fullscreen",
    "mermaid.exportSvg": "Export SVG",
    "mermaid.exportPng": "Export PNG",
    "mermaid.renderError": "Could not render this diagram",
    "mermaid.tooLong": "Diagram source is too long to render",
    "mermaid.pngTooLarge": "Image is too large to export as PNG",
    "mermaid.exportFailed": "Export failed",
    "mermaid.loading": "Rendering diagram…",
    "mermaid.repairing": "Fixing diagram…",
    "mermaid.repair": "Fix diagram",
    "mermaid.repairFailed": "Could not automatically fix this diagram",
    "mermaid.loadFailed": "Could not load the diagram library",
    "mermaid.retryLoad": "Retry load",
    "chart.fullscreen": "Fullscreen",
    "chart.renderError": "Unable to render chart",
    "chart.ohlc.open": "Open",
    "chart.ohlc.high": "High",
    "chart.ohlc.low": "Low",
    "chart.ohlc.close": "Close",
    "chart.stage.interval": "Price period",
    "chart.stage.drivers": "Market drivers",
    "chart.stage.tone.up": "Phased uptrend interval",
    "chart.stage.tone.down": "Phased downtrend interval",
    "chart.stage.tone.side": "Phased sideways interval",
    "chart.candle.hint": "Drag to pan · scroll to zoom",
    "chart.candle.pinHint": "Click to pin · Esc to clear",
    "chart.series.hint": "Crosshair snaps to nearest date",
    "chart.series.pinHint": "Click to pin · Esc to clear",
    "ask.recommended": "Recommended",
    "ask.previous": "Previous question",
    "ask.question": "Question",
    "ask.progress": "{current} of {total}",
    "ask.typeOwn": "Or type your own answer…",
    "ask.yourAnswer": "Your answer…",
  },
} as const;

type ExistingMessageKey = keyof (typeof messages)["zh-CN"];
export type MessageKey = ExistingMessageKey | InterfaceMessageKey;
export type MessageValues = Record<string, string | number>;

function interpolate(message: string, values?: MessageValues): string {
  if (!values) return message;
  return message.replace(/\{(\w+)\}/g, (match, name: string) =>
    Object.prototype.hasOwnProperty.call(values, name) ? String(values[name]) : match,
  );
}

function translate(locale: Locale, key: MessageKey, values?: MessageValues): string {
  const existing = messages[locale] as Partial<Record<MessageKey, string>>;
  const message =
    existing[key] ??
    (locale === "zh-CN"
      ? interfaceMessagesZh[key as InterfaceMessageKey] ?? String(key)
      : String(key));
  return interpolate(message, values);
}

export interface I18nValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey, values?: MessageValues) => string;
}

// D-008: ChemClaw defaults to Simplified Chinese — including the context fallback used when a
// component renders outside LocaleProvider (or briefly during HMR). Never fall back to English.
const fallbackLocale: I18nValue = {
  locale: "zh-CN",
  setLocale: () => {},
  t: (key, values) => translate("zh-CN", key, values),
};

const LocaleContext = createContext<I18nValue>(fallbackLocale);

function initialLocale(): Locale {
  try {
    // One-time restore to zh-CN (D-008). English fallback / HMR had left some installs on
    // en-US; users who want English can switch again under 设置 → 语言.
    if (localStorage.getItem("chemclaw.locale.zh-restore") !== "1") {
      localStorage.setItem("chemclaw.locale.zh-restore", "1");
      localStorage.setItem("chemclaw.locale", "zh-CN");
      return "zh-CN";
    }
    // Only honor an explicit English preference; anything else (missing/corrupt) → zh-CN.
    return localStorage.getItem("chemclaw.locale") === "en-US" ? "en-US" : "zh-CN";
  } catch {
    return "zh-CN";
  }
}

export function LocaleProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [locale, setLocaleState] = useState<Locale>(() => initialLocale());
  const setLocale = (next: Locale) => {
    setLocaleState(next);
    try {
      localStorage.setItem("chemclaw.locale", next);
    } catch {
      /* best effort */
    }
  };
  useEffect(() => {
    document.documentElement.lang = locale;
    try {
      localStorage.setItem("chemclaw.locale", locale);
    } catch {
      /* best effort */
    }
  }, [locale]);
  const value = useMemo<I18nValue>(
    () => ({ locale, setLocale, t: (key, values) => translate(locale, key, values) }),
    [locale],
  );
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useI18n(): I18nValue {
  return useContext(LocaleContext);
}

export function localized(value: Record<Locale, string>, locale: Locale): string {
  return value[locale];
}
