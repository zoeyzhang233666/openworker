import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type React from "react";
import { interfaceMessagesZh, type InterfaceMessageKey } from "./interfaceMessages";

export type Locale = "zh-CN" | "en-US";

const messages = {
  "zh-CN": {
    "nav.conversations": "对话",
    "nav.skills": "技能",
    "nav.experts": "智能体",
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
    "intro.task.price.sub": "有数据则给价格表与要点，无数据标明暂无行情",
    "intro.task.price.prompt":
      "请查询某个化工品的近期价格与走势要点。请先确认品种与区域（或市场），用可用的价格技能/数据源取数，禁止编造；有数据则给出价格表与简要要点，取不到则标明暂无行情。",
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
      "化工外贸转化 · 草稿跟进 · 质量门禁与人工发送",
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
  },
  "en-US": {
    "nav.conversations": "Conversations",
    "nav.skills": "Skills",
    "nav.experts": "Agents",
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
    "intro.task.price.sub": "Include a price table and highlights when data exists; otherwise say no market data",
    "intro.task.price.prompt":
      "Please look up recent prices and trend highlights for a chemical. First confirm the product and region (or market), use available price skills/data sources, and never invent numbers; if data exists, give a price table and brief highlights, otherwise say no market data is available.",
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
      "Export conversion · drafts and follow-ups · quality gate before human send",
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
