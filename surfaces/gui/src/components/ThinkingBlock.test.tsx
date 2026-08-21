import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ThinkingBlock } from "./Transcript";
import { LocaleProvider } from "../i18n";

vi.mock("chart.js", () => ({
  Chart: Object.assign(
    function Chart() {
      return { destroy: vi.fn() };
    },
    { register: vi.fn(), getChart: vi.fn() },
  ),
  LineController: {},
  BarController: {},
  ScatterController: {},
  CategoryScale: {},
  LinearScale: {},
  PointElement: {},
  LineElement: {},
  BarElement: {},
  Filler: {},
  Legend: {},
  Title: {},
  Tooltip: { positioners: {} as Record<string, unknown> },
}));

vi.mock("chartjs-chart-financial", () => ({
  CandlestickController: {},
  CandlestickElement: {},
}));

vi.mock("chartjs-plugin-annotation", () => ({
  default: {},
}));

vi.mock("chartjs-plugin-zoom", () => ({
  default: {},
}));

afterEach(cleanup);

function renderThinking(props: {
  text: string;
  live?: boolean;
  defaultOpen?: boolean;
  forceOpen?: boolean;
}) {
  return render(
    <LocaleProvider>
      <ThinkingBlock {...props} />
    </LocaleProvider>,
  );
}

function stubScrollMetrics(
  el: HTMLElement,
  metrics: { scrollHeight: number; clientHeight: number; scrollTop: number },
) {
  let scrollTop = metrics.scrollTop;
  Object.defineProperty(el, "scrollHeight", {
    configurable: true,
    get: () => metrics.scrollHeight,
  });
  Object.defineProperty(el, "clientHeight", {
    configurable: true,
    get: () => metrics.clientHeight,
  });
  Object.defineProperty(el, "scrollTop", {
    configurable: true,
    get: () => scrollTop,
    set: (v: number) => {
      scrollTop = v;
    },
  });
  return {
    get scrollTop() {
      return scrollTop;
    },
    setScrollHeight(n: number) {
      metrics.scrollHeight = n;
    },
  };
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

describe("ThinkingBlock D-176 forceOpen + body stick-scroll", () => {
  it("keeps body open when forceOpen even if the user clicks the toggle", () => {
    renderThinking({ text: "step one", live: true, defaultOpen: true, forceOpen: true });
    fireEvent.click(screen.getByTestId("thinking-toggle"));
    expect(screen.getByTestId("thinking-body").textContent).toBe("step one");
  });

  it("scrolls the body to the bottom when live text grows while at bottom", () => {
    const { rerender } = renderThinking({
      text: "line1\n",
      live: true,
      defaultOpen: true,
    });
    const body = screen.getByTestId("thinking-body");
    const stub = stubScrollMetrics(body, {
      scrollHeight: 400,
      clientHeight: 100,
      scrollTop: 300,
    });

    stub.setScrollHeight(800);
    rerender(
      <LocaleProvider>
        <ThinkingBlock text={"line1\n".repeat(21)} live defaultOpen />
      </LocaleProvider>,
    );
    expect(stub.scrollTop).toBe(800);
  });

  it("does not force scroll when the user has scrolled up in the body", () => {
    const { rerender } = renderThinking({
      text: "a\n".repeat(30),
      live: true,
      defaultOpen: true,
    });
    const body = screen.getByTestId("thinking-body");
    const stub = stubScrollMetrics(body, {
      scrollHeight: 500,
      clientHeight: 100,
      scrollTop: 10,
    });
    fireEvent.scroll(body);

    stub.setScrollHeight(900);
    rerender(
      <LocaleProvider>
        <ThinkingBlock text={"a\n".repeat(40)} live defaultOpen />
      </LocaleProvider>,
    );
    expect(stub.scrollTop).toBe(10);
  });
});

describe("ThinkingBlock D-178 live remount after steps", () => {
  it("shows body when remounted with forceOpen after tools already ran", () => {
    // Simulates: assistant_message cleared reasoningStream → unmount; next reasoning_delta
    // remounts while TurnGroup already has tools (isFirstTokenThinkingOpen would be false).
    const { unmount } = renderThinking({ text: "early", live: true, defaultOpen: true, forceOpen: true });
    unmount();
    renderThinking({ text: "after tools", live: true, defaultOpen: true, forceOpen: true });
    expect(screen.getByTestId("thinking-body").textContent).toBe("after tools");
    fireEvent.click(screen.getByTestId("thinking-toggle"));
    expect(screen.getByTestId("thinking-body").textContent).toBe("after tools");
  });

  it("stick-scrolls growing live text after a post-steps remount with forceOpen", () => {
    const { rerender } = renderThinking({
      text: "line1\n",
      live: true,
      defaultOpen: true,
      forceOpen: true,
    });
    const body = screen.getByTestId("thinking-body");
    const stub = stubScrollMetrics(body, {
      scrollHeight: 400,
      clientHeight: 100,
      scrollTop: 300,
    });

    stub.setScrollHeight(800);
    rerender(
      <LocaleProvider>
        <ThinkingBlock text={"line1\n".repeat(21)} live defaultOpen forceOpen />
      </LocaleProvider>,
    );
    expect(stub.scrollTop).toBe(800);
  });
});
