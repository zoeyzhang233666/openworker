import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type React from "react";

export type Locale = "zh-CN" | "en-US";

const messages = {
  "zh-CN": {
    "nav.skills": "技能",
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
  },
  "en-US": {
    "nav.skills": "Skills",
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
  },
} as const;

export type MessageKey = keyof (typeof messages)["zh-CN"];

export interface I18nValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey) => string;
}

const fallbackLocale: I18nValue = {
  locale: "en-US",
  setLocale: () => {},
  t: (key) => messages["en-US"][key],
};

const LocaleContext = createContext<I18nValue>(fallbackLocale);

function initialLocale(): Locale {
  try {
    return localStorage.getItem("chemclaw.locale") === "en-US" ? "en-US" : "zh-CN";
  } catch {
    return "zh-CN";
  }
}

export function LocaleProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [locale, setLocale] = useState<Locale>(initialLocale);
  useEffect(() => {
    document.documentElement.lang = locale;
    try { localStorage.setItem("chemclaw.locale", locale); } catch { /* best effort */ }
  }, [locale]);
  const value = useMemo<I18nValue>(
    () => ({ locale, setLocale, t: (key) => messages[locale][key] }),
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
