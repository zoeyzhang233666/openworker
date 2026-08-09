import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { LocaleProvider, useI18n, type MessageKey } from "./i18n";

function LocaleProbe() {
  const { locale, setLocale, t } = useI18n();
  return (
    <>
      <output data-testid="locale">{locale}</output>
      <output data-testid="skills">{t("nav.skills")}</output>
      <output data-testid="home-title">{t("What should we produce?" as MessageKey)}</output>
      <output data-testid="search-placeholder">{t("Search chats" as MessageKey)}</output>
      <output data-testid="automations-title">{t("Automations" as MessageKey)}</output>
      <output data-testid="settings-theme">{t("Theme" as MessageKey)}</output>
      <output data-testid="inbox-title">{t("Inbox" as MessageKey)}</output>
      <output data-testid="connectors-title">{t("Connectors" as MessageKey)}</output>
      <output data-testid="activity-title">{t("Activity" as MessageKey)}</output>
      <output data-testid="approval-deny">{t("Deny" as MessageKey)}</output>
      <output data-testid="export-sales-name">
        {t("experts.persona.export-sales-lobster.name" as MessageKey)}
      </output>
      <output data-testid="export-sales-tagline">
        {t("experts.persona.export-sales-lobster.tagline" as MessageKey)}
      </output>
      <output data-testid="domestic-sales-name">
        {t("experts.persona.domestic-sales-lobster.name" as MessageKey)}
      </output>
      <output data-testid="domestic-sales-tagline">
        {t("experts.persona.domestic-sales-lobster.tagline" as MessageKey)}
      </output>
      <output data-testid="opportunity-radar-name">
        {t("experts.persona.opportunity-radar-lobster.name" as MessageKey)}
      </output>
      <output data-testid="opportunity-radar-tagline">
        {t("experts.persona.opportunity-radar-lobster.tagline" as MessageKey)}
      </output>
      <output data-testid="export-engagement-name">
        {t("experts.persona.export-engagement-lobster.name" as MessageKey)}
      </output>
      <output data-testid="export-engagement-tagline">
        {t("experts.persona.export-engagement-lobster.tagline" as MessageKey)}
      </output>
      <button onClick={() => setLocale("en-US")}>English</button>
    </>
  );
}

afterEach(() => {
  cleanup();
  localStorage.clear();
  document.documentElement.lang = "";
});

beforeEach(() => {
  localStorage.clear();
  document.documentElement.lang = "";
});

describe("LocaleProvider", () => {
  it("defaults to Chinese, persists English, and keeps the document language in sync", () => {
    render(
      <LocaleProvider>
        <LocaleProbe />
      </LocaleProvider>,
    );

    expect(screen.getByTestId("locale").textContent).toBe("zh-CN");
    expect(screen.getByTestId("skills").textContent).toBe("技能");
    expect(screen.getByTestId("home-title").textContent).toBe("我们要完成什么？");
    expect(screen.getByTestId("search-placeholder").textContent).toBe("搜索对话");
    expect(screen.getByTestId("automations-title").textContent).toBe("定时任务");
    expect(screen.getByTestId("settings-theme").textContent).toBe("主题");
    expect(screen.getByTestId("inbox-title").textContent).toBe("收件箱");
    expect(screen.getByTestId("connectors-title").textContent).toBe("连接");
    expect(screen.getByTestId("activity-title").textContent).toBe("活动");
    expect(screen.getByTestId("approval-deny").textContent).toBe("拒绝");
    expect(screen.getByTestId("export-sales-name").textContent).toBe("外贸拓客龙虾");
    expect(screen.getByTestId("export-sales-tagline").textContent).toBe(
      "化工外贸拓客 · 证据核验 · 双评分与下一步动作",
    );
    expect(screen.getByTestId("domestic-sales-name").textContent).toBe("内贸拓客龙虾");
    expect(screen.getByTestId("domestic-sales-tagline").textContent).toBe(
      "化工内贸拓客 · 园区工商证据 · 双评分与下一步动作",
    );
    expect(screen.getByTestId("opportunity-radar-name").textContent).toBe("商机雷达龙虾");
    expect(screen.getByTestId("opportunity-radar-tagline").textContent).toBe(
      "化工信号进 · 商机出 · 证据评分与下一步",
    );
    expect(screen.getByTestId("export-engagement-name").textContent).toBe("外贸转化龙虾");
    expect(screen.getByTestId("export-engagement-tagline").textContent).toBe(
      "化工外贸转化 · 草稿跟进 · 询盘报价与人工发送",
    );
    expect(document.documentElement.lang).toBe("zh-CN");

    fireEvent.click(screen.getByRole("button", { name: "English" }));

    expect(screen.getByTestId("locale").textContent).toBe("en-US");
    expect(screen.getByTestId("skills").textContent).toBe("Skills");
    expect(screen.getByTestId("home-title").textContent).toBe("What should we produce?");
    expect(screen.getByTestId("search-placeholder").textContent).toBe("Search chats");
    expect(screen.getByTestId("automations-title").textContent).toBe("Automations");
    expect(screen.getByTestId("settings-theme").textContent).toBe("Theme");
    expect(screen.getByTestId("inbox-title").textContent).toBe("Inbox");
    expect(screen.getByTestId("connectors-title").textContent).toBe("Connectors");
    expect(screen.getByTestId("activity-title").textContent).toBe("Activity");
    expect(screen.getByTestId("approval-deny").textContent).toBe("Deny");
    expect(screen.getByTestId("export-sales-name").textContent).toBe("Export Sales Lobster");
    expect(screen.getByTestId("export-sales-tagline").textContent).toBe(
      "Chemical prospecting · evidence qualification · dual scores and next actions",
    );
    expect(screen.getByTestId("domestic-sales-name").textContent).toBe("Domestic Sales Lobster");
    expect(screen.getByTestId("domestic-sales-tagline").textContent).toBe(
      "China domestic prospecting · park/registry evidence · dual scores and next actions",
    );
    expect(screen.getByTestId("opportunity-radar-name").textContent).toBe(
      "Opportunity Radar Lobster",
    );
    expect(screen.getByTestId("opportunity-radar-tagline").textContent).toBe(
      "Signals in · opportunities out · scored evidence and next actions",
    );
    expect(screen.getByTestId("export-engagement-name").textContent).toBe(
      "Export Engagement Lobster",
    );
    expect(screen.getByTestId("export-engagement-tagline").textContent).toBe(
      "Export conversion · drafts, inquiry quotes · human send after review",
    );
    expect(localStorage.getItem("chemclaw.locale")).toBe("en-US");
    expect(document.documentElement.lang).toBe("en-US");
  });

  it("restores the persisted English locale after a refresh", () => {
    // Skip the one-time zh-CN restore so an explicit English preference can round-trip.
    localStorage.setItem("chemclaw.locale.zh-restore", "1");
    localStorage.setItem("chemclaw.locale", "en-US");

    render(
      <LocaleProvider>
        <LocaleProbe />
      </LocaleProvider>,
    );

    expect(screen.getByTestId("locale").textContent).toBe("en-US");
    expect(screen.getByTestId("home-title").textContent).toBe("What should we produce?");
    expect(document.documentElement.lang).toBe("en-US");
  });

  it("one-time restore forces Simplified Chinese even if locale was English", () => {
    localStorage.setItem("chemclaw.locale", "en-US");
    // chemclaw.locale.zh-restore unset → migrate to zh-CN

    render(
      <LocaleProvider>
        <LocaleProbe />
      </LocaleProvider>,
    );

    expect(screen.getByTestId("locale").textContent).toBe("zh-CN");
    expect(screen.getByTestId("skills").textContent).toBe("技能");
    expect(localStorage.getItem("chemclaw.locale")).toBe("zh-CN");
    expect(localStorage.getItem("chemclaw.locale.zh-restore")).toBe("1");
  });
});
