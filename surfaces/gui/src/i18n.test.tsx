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
