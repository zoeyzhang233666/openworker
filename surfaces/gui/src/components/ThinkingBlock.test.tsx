import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ThinkingBlock } from "./Transcript";
import { LocaleProvider } from "../i18n";

afterEach(cleanup);

function renderThinking(props: { text: string; live?: boolean; defaultOpen?: boolean }) {
  return render(
    <LocaleProvider>
      <ThinkingBlock {...props} />
    </LocaleProvider>,
  );
}

describe("ThinkingBlock first-token defaultOpen", () => {
  it("keeps body collapsed by default", () => {
    renderThinking({ text: "step one", live: true });
    expect(screen.queryByTestId("thinking-body")).toBeNull();
  });

  it("shows body when defaultOpen is true", () => {
    renderThinking({ text: "step one", live: true, defaultOpen: true });
    expect(screen.getByTestId("thinking-body").textContent).toBe("step one");
  });

  it("lets the user collapse and keeps that override", () => {
    renderThinking({ text: "step one", live: true, defaultOpen: true });
    fireEvent.click(screen.getByTestId("thinking-toggle"));
    expect(screen.queryByTestId("thinking-body")).toBeNull();
    fireEvent.click(screen.getByTestId("thinking-toggle"));
    expect(screen.getByTestId("thinking-body")).toBeTruthy();
  });
});
