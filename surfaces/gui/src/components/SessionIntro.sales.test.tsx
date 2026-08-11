import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SessionIntro, introVariantForAgent } from "./SessionIntro";
import { LocaleProvider } from "../i18n";

vi.mock("../useRoots", () => ({
  useRoots: () => ({ roots: [], busy: false, error: null, addRoot: vi.fn() }),
}));

afterEach(() => cleanup());

describe("introVariantForAgent (D-122)", () => {
  it("maps sales lobsters to SessionIntro variants", () => {
    expect(introVariantForAgent("export-sales-lobster")).toBe("export-sales");
    expect(introVariantForAgent("domestic-sales-lobster")).toBe("domestic-sales");
    expect(introVariantForAgent("opportunity-radar-lobster")).toBe("opportunity-radar");
    expect(introVariantForAgent("export-engagement-lobster")).toBe("export-engagement");
    expect(introVariantForAgent("code")).toBeNull();
  });
});

describe("SessionIntro sales variants (D-122)", () => {
  it("export-sales renders three prospecting cards and prefills", () => {
    const onPrefill = vi.fn();
    render(
      <LocaleProvider>
        <SessionIntro
          hideGreeting
          variant="export-sales"
          sessionId="s1"
          onOpenSessionSettings={() => {}}
          onPrefill={onPrefill}
        />
      </LocaleProvider>,
    );

    expect(screen.getByTestId("intro-tasks-export-sales")).toBeTruthy();
    expect(screen.getByTestId("intro-task-export-sales-prospect")).toBeTruthy();
    expect(screen.getByTestId("intro-task-export-sales-customs")).toBeTruthy();
    expect(screen.getByTestId("intro-task-export-sales-score")).toBeTruthy();
    expect(screen.queryByTestId("intro-tasks-cowork")).toBeNull();
    expect(screen.getAllByText(/进口商|importers/i).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByTestId("intro-task-export-sales-prospect"));
    expect(onPrefill).toHaveBeenCalled();
    expect(String(onPrefill.mock.calls[0][0])).toMatch(/买家|buyers|进口商|importers/i);
    expect(String(onPrefill.mock.calls[0][0])).not.toMatch(/test suite|失败构建|failing build/i);
  });

  it("domestic-sales renders three domestic prospecting cards", () => {
    const onPrefill = vi.fn();
    render(
      <LocaleProvider>
        <SessionIntro
          hideGreeting
          variant="domestic-sales"
          sessionId="s1"
          onOpenSessionSettings={() => {}}
          onPrefill={onPrefill}
        />
      </LocaleProvider>,
    );

    expect(screen.getByTestId("intro-tasks-domestic-sales")).toBeTruthy();
    expect(screen.getByTestId("intro-task-domestic-sales-prospect")).toBeTruthy();
    expect(screen.getByTestId("intro-task-domestic-sales-verify")).toBeTruthy();
    expect(screen.getByTestId("intro-task-domestic-sales-list")).toBeTruthy();

    fireEvent.click(screen.getByTestId("intro-task-domestic-sales-prospect"));
    expect(String(onPrefill.mock.calls[0][0])).toMatch(/国内|domestic|下游|下游客户/i);
  });

  it("opportunity-radar renders three radar cards", () => {
    const onPrefill = vi.fn();
    render(
      <LocaleProvider>
        <SessionIntro
          hideGreeting
          variant="opportunity-radar"
          sessionId="s1"
          onOpenSessionSettings={() => {}}
          onPrefill={onPrefill}
        />
      </LocaleProvider>,
    );

    expect(screen.getByTestId("intro-tasks-opportunity-radar")).toBeTruthy();
    expect(screen.getByTestId("intro-task-radar-tenders")).toBeTruthy();
    expect(screen.getByTestId("intro-task-radar-signals")).toBeTruthy();
    expect(screen.getByTestId("intro-task-radar-score")).toBeTruthy();

    fireEvent.click(screen.getByTestId("intro-task-radar-tenders"));
    expect(String(onPrefill.mock.calls[0][0])).toMatch(/招标|tender|采购|procurement/i);
  });

  it("export-engagement renders three conversion cards", () => {
    const onPrefill = vi.fn();
    render(
      <LocaleProvider>
        <SessionIntro
          hideGreeting
          variant="export-engagement"
          sessionId="s1"
          onOpenSessionSettings={() => {}}
          onPrefill={onPrefill}
        />
      </LocaleProvider>,
    );

    expect(screen.getByTestId("intro-tasks-export-engagement")).toBeTruthy();
    expect(screen.getByTestId("intro-task-engagement-outreach")).toBeTruthy();
    expect(screen.getByTestId("intro-task-engagement-quote")).toBeTruthy();
    expect(screen.getByTestId("intro-task-engagement-gate")).toBeTruthy();

    fireEvent.click(screen.getByTestId("intro-task-engagement-outreach"));
    expect(String(onPrefill.mock.calls[0][0])).toMatch(/开发信|outreach|不自动发送|Never auto-send/i);
  });
});
