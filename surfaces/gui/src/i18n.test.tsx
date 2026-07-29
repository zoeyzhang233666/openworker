import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { LocaleProvider, useI18n } from "./i18n";

function LocaleProbe() {
  const { locale, setLocale, t } = useI18n();
  return (
    <>
      <output data-testid="locale">{locale}</output>
      <output data-testid="skills">{t("nav.skills")}</output>
      <button onClick={() => setLocale("en-US")}>English</button>
    </>
  );
}

afterEach(() => {
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
    expect(document.documentElement.lang).toBe("zh-CN");

    fireEvent.click(screen.getByRole("button", { name: "English" }));

    expect(screen.getByTestId("locale").textContent).toBe("en-US");
    expect(screen.getByTestId("skills").textContent).toBe("Skills");
    expect(localStorage.getItem("chemclaw.locale")).toBe("en-US");
    expect(document.documentElement.lang).toBe("en-US");
  });
});
