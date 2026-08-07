import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SessionIntro } from "./SessionIntro";
import { LocaleProvider } from "../i18n";

vi.mock("../useRoots", () => ({
  useRoots: () => ({ roots: [], busy: false, error: null, addRoot: vi.fn() }),
}));

afterEach(() => cleanup());

describe("SessionIntro chat variant (D-083)", () => {
  it("renders three Q&A starter cards and prefills on click", () => {
    const onPrefill = vi.fn();
    render(
      <LocaleProvider>
        <SessionIntro
          hideGreeting
          variant="chat"
          sessionId="s1"
          onOpenSessionSettings={() => {}}
          onPrefill={onPrefill}
        />
      </LocaleProvider>,
    );

    expect(screen.getByTestId("intro-tasks-chat")).toBeTruthy();
    expect(screen.getByTestId("intro-task-chat-explain")).toBeTruthy();
    expect(screen.getByTestId("intro-task-chat-compare")).toBeTruthy();
    expect(screen.getByTestId("intro-task-chat-checklist")).toBeTruthy();
    expect(screen.queryByTestId("intro-tasks-cowork")).toBeNull();

    fireEvent.click(screen.getByTestId("intro-task-chat-explain"));
    expect(onPrefill).toHaveBeenCalled();
    expect(String(onPrefill.mock.calls[0][0])).toMatch(/通俗话解释|plain language/i);
  });
});
