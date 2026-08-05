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
    "experts.choosePersona": "选择智能体（当前默认：{name}）",
    "experts.startAs": "选择对话智能体",
    "experts.managePersonas": "管理智能体…",
    "experts.systemPrompt": "系统提示词",
    "experts.defaultSkills": "默认技能",
    "experts.skillMissing": "未安装",
    "experts.installPath": "安装路径",
    "experts.openFolder": "打开文件夹",
    "experts.builtinReadonly": "内置智能体由产品维护，提示词只读。个性化请等待「另存为副本」（后续版本）。",
    "intro.lede": "选择一个任务开始——我会完成工作并保存结果。你也可以直接在下方输入需求。",
    "intro.task.folder.title": "分析文件夹中的文件",
    "intro.task.folder.sub": "我会读取文件并总结重点",
    "intro.task.folder.act": "选择文件夹 →",
    "intro.task.hubspot.title": "根据我的 HubSpot 线索创建报告",
    "intro.task.hubspot.sub": "来源、阶段以及需要跟进的对象",
    "intro.task.github.title": "自动生成每周 GitHub 进展报告并发送到 Slack",
    "intro.task.github.sub": "汇总仓库活动，并在每周五发送",
    "intro.act.start": "开始 →",
    "intro.act.configure": "配置 ›",
    "experts.persona.cowork.name": "ChemClaw",
    "experts.persona.cowork.tagline": "产出可交付成果——研究、分析、脚本",
    "experts.persona.code.name": "代码",
    "experts.persona.code.tagline": "在代码库中工作——文件、git、shell",
    "experts.persona.chat.name": "问答",
    "experts.persona.chat.tagline": "快速提问——无需工作区",
    "experts.persona.ops.name": "运维龙虾",
    "experts.persona.ops.tagline": "运维与排查——手册、日志、基础设施",
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
      "Pick a task to start — I'll do the work and save the result. Or just type what you need below.",
    "intro.task.folder.title": "Analyze the files in a directory",
    "intro.task.folder.sub": "I'll read them and summarize what matters",
    "intro.task.folder.act": "Pick a folder →",
    "intro.task.hubspot.title": "Create a report from my HubSpot leads",
    "intro.task.hubspot.sub": "Sources, stages, and who needs follow-up",
    "intro.task.github.title": "Automate a weekly GitHub progress report to Slack",
    "intro.task.github.sub": "Repo activity, summarized and posted every Friday",
    "intro.act.start": "Start →",
    "intro.act.configure": "Configure ›",
    "experts.persona.cowork.name": "ChemClaw",
    "experts.persona.cowork.tagline": "Produce a deliverable — research, analysis, scripts.",
    "experts.persona.code.name": "Code",
    "experts.persona.code.tagline": "Work in a codebase — files, git, shell.",
    "experts.persona.chat.name": "Chat",
    "experts.persona.chat.tagline": "Quick questions — no workspace.",
    "experts.persona.ops.name": "Ops Lobster",
    "experts.persona.ops.tagline": "Operate and investigate — runbooks, logs, infrastructure.",
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
