import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { RightRail } from "./RightRail";
import { LocaleProvider } from "../i18n";

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

function stubFetch(routes: { match: string; method?: string; json: any }[]) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    const method = (init?.method || "GET").toUpperCase();
    for (const r of routes) {
      if (url.includes(r.match) && (!r.method || r.method === method)) {
        return { ok: true, json: async () => r.json } as Response;
      }
    }
    return { ok: true, json: async () => ({}) } as Response;
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("RightRail artifacts panel", () => {
  it("shows empty state when there are no previewable artifacts", async () => {
    const sessionId = "s-absent";
    stubFetch([
      {
        match: `/v1/sessions/${sessionId}/artifacts`,
        method: "GET",
        json: { artifacts: [] },
      },
      {
        match: `/v1/sessions/${sessionId}/roots`,
        method: "GET",
        json: { roots: [] },
      },
      {
        match: `/v1/sessions/${sessionId}/connections`,
        method: "GET",
        json: { connected: [], recommended: [], attention: 0 },
      },
      {
        match: `/v1/connectors`,
        method: "GET",
        json: [],
      },
    ]);

    render(
      <LocaleProvider>
        <RightRail
          active={true}
          sessionId={sessionId}
          refreshKey={0}
          toolNames={[]}
          todo={[]}
          running={false}
          onPreviewChange={() => {}}
        />
      </LocaleProvider>,
    );

    await screen.findByText("暂无可预览文件。");
    expect(screen.queryByText("查看任务进度")).toBeNull();
  });

  it("filters internal ._chemclaw artifacts and lists normal deliverables", async () => {
    const sessionId = "s-1";
    stubFetch([
      {
        match: `/v1/sessions/${sessionId}/artifacts`,
        method: "GET",
        json: {
          artifacts: [
            {
              path: "._chemclaw/outbound-clip/clip-1.txt",
              name: "clip-1.txt",
              kind: "text",
              size: 10,
              modified_at: 1,
            },
            {
              path: "normal.md",
              name: "normal.md",
              kind: "markdown",
              size: 10,
              modified_at: 1,
            },
          ],
        },
      },
      {
        match: `/v1/sessions/${sessionId}/roots`,
        method: "GET",
        json: { roots: [] },
      },
      {
        match: `/v1/sessions/${sessionId}/connections`,
        method: "GET",
        json: { connected: [], recommended: [], attention: 0 },
      },
      {
        match: `/v1/connectors`,
        method: "GET",
        json: [],
      },
    ]);

    render(
      <LocaleProvider>
        <RightRail
          active={true}
          sessionId={sessionId}
          refreshKey={0}
          toolNames={[]}
          todo={[]}
          running={false}
          onPreviewChange={() => {}}
        />
      </LocaleProvider>,
    );

    await screen.findByText("normal.md");
    expect(screen.queryByText("clip-1.txt")).toBeNull();
    expect(screen.queryByText("查看任务进度")).toBeNull();
  });

  it("lists more than 16 deliverables instead of silently truncating", async () => {
    const sessionId = "s-many";
    const artifacts = Array.from({ length: 20 }, (_, i) => ({
      path: `report-${String(i + 1).padStart(2, "0")}.md`,
      name: `report-${String(i + 1).padStart(2, "0")}.md`,
      kind: "markdown",
      size: 10,
      modified_at: 20 - i,
    }));
    stubFetch([
      {
        match: `/v1/sessions/${sessionId}/artifacts`,
        method: "GET",
        json: { artifacts },
      },
      {
        match: `/v1/sessions/${sessionId}/roots`,
        method: "GET",
        json: { roots: [] },
      },
      {
        match: `/v1/sessions/${sessionId}/connections`,
        method: "GET",
        json: { connected: [], recommended: [], attention: 0 },
      },
      {
        match: `/v1/connectors`,
        method: "GET",
        json: [],
      },
    ]);

    render(
      <LocaleProvider>
        <RightRail
          active={true}
          sessionId={sessionId}
          refreshKey={0}
          toolNames={[]}
          todo={[]}
          running={false}
          onPreviewChange={() => {}}
        />
      </LocaleProvider>,
    );

    await screen.findByText("report-01.md");
    expect(screen.getByText("report-17.md")).toBeTruthy();
    expect(screen.getByText("report-18.md")).toBeTruthy();
    expect(screen.getByText("report-19.md")).toBeTruthy();
    expect(screen.getByText("report-20.md")).toBeTruthy();
  });

  it("resolves CN futures short-ref in markdown artifact preview from session tools", async () => {
    const sessionId = "s-chart";
    const ref = JSON.stringify({
      version: 1,
      type: "candlestick",
      from_tool: "lookup_cn_futures_ohlc",
      symbol: "PG",
    });
    const preview = JSON.stringify({
      status: "ok",
      symbol: "PG2610.DCE",
      chart_spec: {
        version: 1,
        type: "candlestick",
        title: "液化气主力",
        labels: ["D1", "D2"],
        ohlc: [
          { o: 4000, h: 4100, l: 3900, c: 4050 },
          { o: 4050, h: 4200, l: 4000, c: 4180 },
        ],
      },
    });
    stubFetch([
      {
        match: `/v1/sessions/${sessionId}/artifacts/read`,
        method: "GET",
        json: {
          path: "液化气期现基差.md",
          name: "液化气期现基差.md",
          kind: "markdown",
          content: `## 走势\n\n\`\`\`chart\n${ref}\n\`\`\`\n`,
        },
      },
      {
        match: `/v1/sessions/${sessionId}/artifacts`,
        method: "GET",
        json: {
          artifacts: [
            {
              path: "液化气期现基差.md",
              name: "液化气期现基差.md",
              kind: "markdown",
              size: 80,
              modified_at: 1,
            },
          ],
        },
      },
      {
        match: `/v1/sessions/${sessionId}/roots`,
        method: "GET",
        json: { roots: [] },
      },
      {
        match: `/v1/sessions/${sessionId}/connections`,
        method: "GET",
        json: { connected: [], recommended: [], attention: 0 },
      },
      {
        match: `/v1/connectors`,
        method: "GET",
        json: [],
      },
    ]);

    render(
      <LocaleProvider>
        <RightRail
          active={true}
          sessionId={sessionId}
          refreshKey={0}
          toolNames={["lookup_cn_futures_ohlc"]}
          chartToolResults={[{ name: "lookup_cn_futures_ohlc", preview }]}
          todo={[]}
          running={false}
          onPreviewChange={() => {}}
        />
      </LocaleProvider>,
    );

    fireEvent.click(await screen.findByText("液化气期现基差.md"));
    await waitFor(() => expect(screen.getByTestId("chart-block")).toBeTruthy());
    expect(screen.queryByTestId("chart-error")).toBeNull();
    expect(screen.queryByText(/no lookup_cn_futures_ohlc result in this session/)).toBeNull();
  });
});
