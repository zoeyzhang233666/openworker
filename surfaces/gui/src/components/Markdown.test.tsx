import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Markdown, OPEN_ARTIFACT_EVENT } from "./Markdown";

vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(async () => ({
      svg: '<svg data-testid="fake-svg"></svg>',
    })),
  },
}));

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

// §34 (UX-016): [Title](artifact:path) renders as a chip that opens the artifact viewer via
// a window event; ordinary links keep the open-externally treatment.
describe("Markdown artifact links", () => {
  it("renders an artifact: link as a chip and dispatches the open event with the path", () => {
    const seen: string[] = [];
    const listener = (e: Event) => seen.push((e as CustomEvent).detail.path);
    window.addEventListener(OPEN_ARTIFACT_EVENT, listener);

    render(<Markdown text="Done — [Semiconductor dashboard](artifact:reports/semi.html)" />);
    const chip = screen.getByTestId("artifact-chip");
    expect(chip.textContent).toContain("Semiconductor dashboard");
    expect(chip.textContent).toContain("semi.html"); // filename shown under the title
    fireEvent.click(chip);
    expect(seen).toEqual(["reports/semi.html"]);

    window.removeEventListener(OPEN_ARTIFACT_EVENT, listener);
  });

  it("ordinary links stay external and never become chips", () => {
    const { container } = render(<Markdown text="see [the docs](https://example.com)" />);
    expect(screen.queryByTestId("artifact-chip")).toBeNull();
    const a = container.querySelector("a")!;
    expect(a.getAttribute("target")).toBe("_blank");
    expect(a.getAttribute("href")).toBe("https://example.com");
  });

  it("chip title falls back to the filename when the link text is empty", () => {
    vi.spyOn(window, "dispatchEvent");
    render(<Markdown text="[](artifact:out/report.pdf)" />);
    expect(screen.getByTestId("artifact-chip").textContent).toContain("report.pdf");
  });

  // react-markdown percent-encodes non-ASCII in hrefs; the chip must decode so
  // readArtifact looks up the real workspace-relative filename.
  it("decodes percent-encoded non-ASCII artifact paths before opening", () => {
    const seen: string[] = [];
    const listener = (e: Event) => seen.push((e as CustomEvent).detail.path);
    window.addEventListener(OPEN_ARTIFACT_EVENT, listener);

    render(<Markdown text="[丙烯产业链研究报告](artifact:丙烯产业链研究报告.md)" />);
    fireEvent.click(screen.getByTestId("artifact-chip"));
    expect(seen).toEqual(["丙烯产业链研究报告.md"]);

    window.removeEventListener(OPEN_ARTIFACT_EVENT, listener);
  });

  it("shows Make webpage edition next to Markdown deliverables and dispatches request event", () => {
    const seen: Array<{ title: string; path: string }> = [];
    const listener = (e: Event) =>
      seen.push((e as CustomEvent<{ title: string; path: string }>).detail);
    window.addEventListener("ocw-request-webpage", listener);

    render(<Markdown text="[丙烯产业链研究报告](artifact:丙烯产业链研究报告.md)" />);
    const btn = screen.getByTestId("artifact-make-webpage");
    expect(btn.textContent).toMatch(/做网页版|Make webpage/);
    fireEvent.click(btn);
    expect(seen).toEqual([
      { title: "丙烯产业链研究报告", path: "丙烯产业链研究报告.md" },
    ]);

    window.removeEventListener("ocw-request-webpage", listener);
  });

  it("does not show Make webpage edition for non-Markdown artifacts", () => {
    render(<Markdown text="Done — [dashboard](artifact:reports/semi.html)" />);
    expect(screen.queryByTestId("artifact-make-webpage")).toBeNull();
  });

  it("renders relative workspace .md links as chips (not blue external anchors)", () => {
    const seen: string[] = [];
    const listener = (e: Event) => seen.push((e as CustomEvent).detail.path);
    window.addEventListener(OPEN_ARTIFACT_EVENT, listener);

    const { container } = render(<Markdown text="见 [产业链分析](产业链分析.md)" />);
    expect(container.querySelector("a")).toBeNull();
    fireEvent.click(screen.getByTestId("artifact-chip"));
    expect(seen).toEqual(["产业链分析.md"]);

    window.removeEventListener(OPEN_ARTIFACT_EVENT, listener);
  });
});

describe("Markdown mermaid fence", () => {
  it("renders MermaidBlock for ```mermaid when enabled", async () => {
    const text = "见下图\n\n```mermaid\ngraph TD; A-->B\n```\n";
    render(<Markdown text={text} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-block")).toBeTruthy());
  });

  it("keeps ordinary code as pre/code", () => {
    render(<Markdown text={"```js\nconsole.log(1)\n```"} />);
    expect(screen.queryByTestId("mermaid-block")).toBeNull();
    expect(document.querySelector("pre code")?.textContent).toContain("console.log");
  });

  it("skips MermaidBlock when renderMermaid is false", () => {
    const text = "```mermaid\ngraph TD; A-->B\n```";
    render(<Markdown text={text} renderMermaid={false} />);
    expect(screen.queryByTestId("mermaid-block")).toBeNull();
    expect(document.querySelector("pre code")?.className || "").toMatch(/language-mermaid/);
  });

  // Parent re-renders (scroll follow, inbox poll, etc.) must not tear down MermaidBlock
  // or mermaid.render runs again → svg cleared → scrollHeight collapses → page jitter.
  it("does not re-render mermaid when Markdown rerenders with the same text", async () => {
    const mermaid = await import("mermaid");
    const renderFn = mermaid.default.render as ReturnType<typeof vi.fn>;
    const text = "```mermaid\ngraph TD; A-->B\n```";
    const { rerender } = render(<Markdown text={text} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-diagram")).toBeTruthy());
    const callsAfterFirst = renderFn.mock.calls.length;
    expect(callsAfterFirst).toBeGreaterThanOrEqual(1);

    rerender(<Markdown text={text} />);
    rerender(<Markdown text={text} />);
    rerender(<Markdown text={text} />);
    await new Promise((r) => setTimeout(r, 80));

    expect(renderFn.mock.calls.length).toBe(callsAfterFirst);
    expect(screen.getByTestId("mermaid-diagram")).toBeTruthy();
    expect(screen.queryByText(/正在渲染|Rendering/i)).toBeNull();
  });
});

const chartFixture = JSON.stringify({
  version: 1,
  type: "line",
  labels: ["A", "B"],
  series: [{ name: "s", values: [1, 2] }],
});

describe("Markdown chart fence", () => {
  it("renders ChartBlock for ```chart when enabled", async () => {
    const text = `见下图\n\n\`\`\`chart\n${chartFixture}\n\`\`\`\n`;
    render(<Markdown text={text} />);
    await waitFor(() => expect(screen.getByTestId("chart-block")).toBeTruthy());
  });

  it("keeps ordinary ```json as pre/code", () => {
    render(<Markdown text={"```json\n{}\n```"} />);
    expect(screen.queryByTestId("chart-block")).toBeNull();
    expect(document.querySelector("pre code")?.className || "").toMatch(/language-json/);
  });

  it("skips ChartBlock when renderCharts is false", () => {
    const text = `\`\`\`chart\n${chartFixture}\n\`\`\``;
    render(<Markdown text={text} renderCharts={false} />);
    expect(screen.queryByTestId("chart-block")).toBeNull();
    expect(document.querySelector("pre code")?.className || "").toMatch(/language-chart/);
  });

  it("resolves Yahoo short-ref via chartToolResults", async () => {
    const ref = JSON.stringify({
      version: 1,
      type: "candlestick",
      from_tool: "lookup_yahoo_ohlc",
      symbol: "CL=F",
    });
    const preview = JSON.stringify({
      status: "ok",
      symbol: "CL=F",
      chart_spec: {
        version: 1,
        type: "candlestick",
        labels: ["D1", "D2"],
        ohlc: [
          { o: 1, h: 2, l: 0.5, c: 1.5 },
          { o: 2, h: 3, l: 1, c: 2.5 },
        ],
      },
    });
    const text = `\`\`\`chart\n${ref}\n\`\`\``;
    render(
      <Markdown
        text={text}
        chartToolResults={[{ name: "lookup_yahoo_ohlc", preview }]}
      />,
    );
    await waitFor(() => expect(screen.getByTestId("chart-block")).toBeTruthy());
    expect(screen.queryByTestId("chart-error")).toBeNull();
  });
});
