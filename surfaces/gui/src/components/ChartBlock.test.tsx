import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ChartBlock, chartJsConfigFromSpec, formatChartPrice, CN_CANDLE_COLORS, STAGE_TONE_COLORS, buildStageAnnotations, buildSeriesStageAnnotations, findStageAtIndex, resolveChartStages, overlayComputedStageTones, exclusiveStageRanges, classifyStageTones, stageReturnPct, sanitizeStageReason, defaultCandleXWindow, yRangeForVisibleBars, yRangeForVisibleSeries, DEFAULT_CANDLE_WINDOW, DENSE_POINT_THRESHOLD, CHART_PAD_TOP, AXIS_PANEL_RAIL, AXIS_PANEL_RAIL_LIGHTBOX, LIGHTBOX_CANDLE_WINDOW } from "./ChartBlock";
import { parseChartSpec } from "../chartSpec";

const destroyMock = vi.fn();
const getChartDestroyMock = vi.fn();
const getChartMock = vi.fn((): { destroy: typeof getChartDestroyMock } | undefined => undefined);
const getValueForPixelMock = vi.fn((): number => Number.NaN);
const ChartMock = vi.fn().mockImplementation(() => ({
  destroy: destroyMock,
  draw: vi.fn(),
  scales: { x: { getValueForPixel: getValueForPixelMock } },
  chartArea: { left: 188, right: 400, top: 0, bottom: 300 },
  getDatasetMeta: () => ({ data: [] }),
  data: { datasets: [{ data: [] }] },
}));

vi.mock("chart.js", () => ({
  Chart: Object.assign(
    function Chart(...args: unknown[]) {
      return ChartMock(...args);
    },
    {
      register: vi.fn(),
      getChart: (canvas: unknown) => getChartMock(canvas),
    },
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

const validLine = JSON.stringify({
  version: 1,
  type: "line",
  title: "甲醇",
  unit: "元/吨",
  labels: ["D1", "D2"],
  series: [{ name: "陕西", values: [6100, 6035] }],
});

const validBar = JSON.stringify({
  version: 1,
  type: "bar",
  labels: ["陕", "鲁"],
  series: [{ name: "价", values: [6100, 6200] }],
});

afterEach(() => {
  cleanup();
  ChartMock.mockClear();
  destroyMock.mockClear();
  getChartDestroyMock.mockClear();
  getChartMock.mockReset();
  getChartMock.mockReturnValue(undefined);
  getValueForPixelMock.mockReset();
  getValueForPixelMock.mockReturnValue(Number.NaN);
});

describe("ChartBlock", () => {
  it("renders a valid line chart", async () => {
    render(<ChartBlock source={validLine} />);
    await waitFor(() => expect(screen.getByTestId("chart-canvas")).toBeTruthy());
    expect(ChartMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("chart-error")).toBeNull();
  });

  it("renders a valid bar chart", async () => {
    render(<ChartBlock source={validBar} />);
    await waitFor(() => expect(screen.getByTestId("chart-canvas")).toBeTruthy());
    expect(ChartMock).toHaveBeenCalledTimes(1);
    const cfg = ChartMock.mock.calls[0][1];
    expect(cfg.type).toBe("bar");
  });

  it("assigns a non-gray palette color to each series", async () => {
    const multi = JSON.stringify({
      version: 1,
      type: "line",
      labels: ["A", "B"],
      series: [
        { name: "陕", values: [1, 2] },
        { name: "鲁", values: [3, 4] },
      ],
    });
    render(<ChartBlock source={multi} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    const cfg = ChartMock.mock.calls[0][1];
    expect(cfg.data.datasets[0].borderColor).toBe("#2563eb");
    expect(cfg.data.datasets[1].borderColor).toBe("#D55E00");
    expect(cfg.data.datasets[0].borderWidth).toBe(2);
  });

  it("renders candlestick from ohlc without requiring version", async () => {
    const candle = JSON.stringify({
      type: "candlestick",
      title: "WTI",
      labels: ["D1", "D2"],
      ohlc: [
        { o: 70, h: 72, l: 69, c: 71 },
        { o: 71, h: 73, l: 70, c: 72 },
      ],
    });
    render(<ChartBlock source={candle} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    const cfg = ChartMock.mock.calls[0][1];
    expect(cfg.type).toBe("candlestick");
    expect(cfg.data.datasets[0].data[0]).toEqual({ x: 0, o: 70, h: 72, l: 69, c: 71 });
    // 国内习惯：红涨绿跌
    expect(cfg.data.datasets[0].borderColors.up).toBe(CN_CANDLE_COLORS.border.up);
    expect(cfg.data.datasets[0].borderColors.down).toBe(CN_CANDLE_COLORS.border.down);
    expect(cfg.data.datasets[0].backgroundColors.up).toBe(CN_CANDLE_COLORS.background.up);
    expect(cfg.data.datasets[0].backgroundColors.down).toBe(CN_CANDLE_COLORS.background.down);
  });

  it("resolves Yahoo short-ref from chartToolResults", async () => {
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
        title: "Crude",
        labels: ["D1", "D2"],
        ohlc: [
          { o: 70, h: 72, l: 69, c: 71 },
          { o: 71, h: 73, l: 70, c: 72 },
        ],
      },
    });
    render(
      <ChartBlock
        source={ref}
        chartToolResults={[{ name: "lookup_yahoo_ohlc", preview }]}
      />,
    );
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    expect(screen.queryByTestId("chart-error")).toBeNull();
  });

  it("resolves CN futures short-ref from chartToolResults", async () => {
    const ref = JSON.stringify({
      version: 1,
      type: "candlestick",
      from_tool: "lookup_cn_futures_ohlc",
      symbol: "PG",
    });
    const preview = JSON.stringify({
      status: "ok",
      symbol: "PG2609.DCE",
      chart_spec: {
        version: 1,
        type: "candlestick",
        title: "液化气",
        labels: ["D1", "D2"],
        ohlc: [
          { o: 4000, h: 4100, l: 3900, c: 4050 },
          { o: 4050, h: 4200, l: 4000, c: 4180 },
        ],
      },
    });
    render(
      <ChartBlock
        source={ref}
        chartToolResults={[{ name: "lookup_cn_futures_ohlc", preview }]}
      />,
    );
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    expect(screen.queryByTestId("chart-error")).toBeNull();
  });

  it("shows error when series length mismatches labels", async () => {
    const bad = JSON.stringify({
      version: 1,
      type: "line",
      labels: ["A", "B"],
      series: [{ name: "s", values: [1] }],
    });
    render(<ChartBlock source={bad} />);
    await waitFor(() => expect(screen.getByTestId("chart-error")).toBeTruthy());
    expect(ChartMock).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /图表|Chart/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /源码|Source/i })).toBeNull();
    expect(screen.getByTestId("chart-source").textContent).toContain('"labels"');
  });

  it("success chart has no chart/source toggle and blends chrome", async () => {
    render(<ChartBlock source={validLine} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: /图表|Chart$/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /源码|Source/i })).toBeNull();
    expect(screen.getByTestId("chart-block").className).toMatch(/chart-block--blend/);
    expect(screen.getByTestId("chart-fullscreen").getAttribute("aria-label")).toMatch(/全屏|Fullscreen/);
  });

  it("shows error on invalid JSON without crashing", async () => {
    render(<ChartBlock source="{not-json" />);
    await waitFor(() => expect(screen.getByTestId("chart-error")).toBeTruthy());
    expect(ChartMock).not.toHaveBeenCalled();
  });

  it("rejects string values", async () => {
    const bad = JSON.stringify({
      version: 1,
      type: "line",
      labels: ["A"],
      series: [{ name: "s", values: ["x"] }],
    });
    render(<ChartBlock source={bad} />);
    await waitFor(() => expect(screen.getByTestId("chart-error")).toBeTruthy());
    expect(ChartMock).not.toHaveBeenCalled();
  });

  it("destroys and recreates Chart only when source changes", async () => {
    const { rerender } = render(<ChartBlock source={validLine} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalledTimes(1));

    rerender(<ChartBlock source={validLine} />);
    rerender(<ChartBlock source={validLine} />);
    await new Promise((r) => setTimeout(r, 40));
    expect(ChartMock).toHaveBeenCalledTimes(1);

    rerender(<ChartBlock source={validBar} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalledTimes(2));
    expect(destroyMock).toHaveBeenCalled();
  });

  it("destroys any Chart.js registry instance on the canvas before creating", async () => {
    getChartMock.mockReturnValue({ destroy: getChartDestroyMock });
    render(<ChartBlock source={validLine} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    expect(getChartMock).toHaveBeenCalled();
    expect(getChartDestroyMock).toHaveBeenCalled();
    expect(screen.queryByTestId("chart-error")).toBeNull();
    expect(screen.getByTestId("chart-canvas")).toBeTruthy();
  });

  it("unmount and remount does not surface canvas-already-in-use", async () => {
    const { unmount } = render(<ChartBlock source={validLine} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalledTimes(1));
    unmount();

    // Simulate leftover registry entry after a flaky destroy (StrictMode race).
    getChartMock.mockReturnValue({ destroy: getChartDestroyMock });
    ChartMock.mockClear();
    render(<ChartBlock source={validLine} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalledTimes(1));
    expect(getChartDestroyMock).toHaveBeenCalled();
    expect(screen.queryByTestId("chart-error")).toBeNull();
    expect(screen.queryByText(/Canvas is already in use/i)).toBeNull();
  });
});

describe("chart tooltip formatting", () => {
  it("formatChartPrice keeps at most two decimals", () => {
    expect(formatChartPrice(93.44999694824219)).toBe("93.45");
    expect(formatChartPrice(97)).toBe("97.00");
    expect(formatChartPrice(Number.NaN)).toBe("—");
  });

  it("candlestick uses CN red-up green-down colors", () => {
    const parsed = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["D1"],
        ohlc: [{ o: 1, h: 2, l: 0.5, c: 1.5 }],
      }),
    );
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec);
    const ds = cfg.data.datasets[0] as {
      borderColors: { up: string; down: string };
      backgroundColors: { up: string; down: string };
    };
    expect(ds.borderColors.up).toBe("#E53935");
    expect(ds.borderColors.down).toBe("#1B9E5A");
    expect(ds.backgroundColors.up).toContain("229, 57, 53");
    expect(ds.backgroundColors.down).toContain("27, 158, 90");
  });

  it("candlestick disables floating OHLC tooltip (axis panel owns details)", () => {
    const parsed = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["2026-05-18", "2026-06-03"],
        ohlc: [
          { o: 93.44999694824219, h: 97, l: 93.44999694824219, c: 96.0199966430664 },
          { o: 70, h: 72, l: 69, c: 71 },
        ],
        yLabel: "USD",
      }),
    );
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec);
    expect((cfg.options?.plugins?.tooltip as { enabled?: boolean } | undefined)?.enabled).toBe(false);
    expect(cfg.options?.plugins?.tooltip?.callbacks?.title).toBeUndefined();
    expect(cfg.options?.plugins?.tooltip?.callbacks?.label).toBeUndefined();
  });

  it("line axis chart disables tooltip and reserves left rail", () => {
    const parsed = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "line",
        labels: ["A", "B"],
        series: [{ name: "价", values: [6100.129, 6035] }],
      }),
    );
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec);
    expect((cfg.options?.plugins?.tooltip as { enabled?: boolean } | undefined)?.enabled).toBe(false);
    expect((cfg.options as { layout?: { padding?: { left?: number } } })?.layout?.padding?.left).toBe(
      AXIS_PANEL_RAIL,
    );
    expect(cfg.plugins?.some((p) => (p as { id?: string }).id === "axisCrosshair")).toBe(true);
  });
});

function extremeContents(anns: Record<string, unknown>): string[] {
  return Object.entries(anns)
    .filter(([k]) => k.startsWith("extreme"))
    .map(([, v]) => (v as { content: string }).content);
}

describe("candlestick stage annotations", () => {
  it("buildStageAnnotations emits bands without extremes by default", () => {
    const labels = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"];
    const ohlc = [
      { o: 70, h: 72, l: 69, c: 71 },
      { o: 71, h: 80, l: 70, c: 79 },
      { o: 79, h: 79, l: 60, c: 61 },
      { o: 61, h: 62, l: 55, c: 56 },
    ];
    const anns = buildStageAnnotations(
      labels,
      ohlc,
      [
        { start: "2026-01-01", end: "2026-01-02", tone: "up", reason: "地缘溢价" },
        { start: "2026-01-03", end: "2026-01-04", tone: "down", reason: "供应宽松" },
      ],
      false,
    );
    expect(anns.stageBand0).toMatchObject({
      type: "box",
      backgroundColor: STAGE_TONE_COLORS.up.band,
    });
    expect(anns.stageBand1).toMatchObject({
      type: "box",
      backgroundColor: STAGE_TONE_COLORS.down.band,
    });
    expect(anns.stageReason0).toBeUndefined();
    expect(anns.stageArrow0).toBeUndefined();
    expect(extremeContents(anns)).toEqual([]);
  });

  it("showExtremes paints only visible-window global high and low", () => {
    const labels = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"];
    const ohlc = [
      { o: 90, h: 100, l: 89, c: 91 },
      { o: 70, h: 72, l: 69, c: 71 },
      { o: 71, h: 80, l: 70, c: 79 },
      { o: 79, h: 79, l: 60, c: 61 },
      { o: 61, h: 62, l: 55, c: 56 },
    ];
    const anns = buildStageAnnotations(
      labels,
      ohlc,
      [
        { start: "2026-01-02", end: "2026-01-03", tone: "up", reason: "地缘溢价" },
        { start: "2026-01-04", end: "2026-01-05", tone: "down", reason: "供应宽松" },
      ],
      false,
      { showExtremes: true, xMin: 1, xMax: 4 },
    );
    const contents = extremeContents(anns);
    expect(contents).toHaveLength(2);
    expect(contents).toContain("80.00");
    expect(contents).toContain("55.00");
    expect(contents).not.toContain("100.00");
  });

  it("showExtremes without stages still paints two global extremes", () => {
    const labels = ["D1", "D2", "D3"];
    const ohlc = [
      { o: 1, h: 9, l: 1, c: 2 },
      { o: 2, h: 3, l: 0.5, c: 1 },
      { o: 1, h: 2, l: 1, c: 1.5 },
    ];
    const anns = buildStageAnnotations(labels, ohlc, undefined, false, { showExtremes: true });
    const contents = extremeContents(anns);
    expect(contents).toHaveLength(2);
    expect(contents).toContain("9.00");
    expect(contents).toContain("0.50");
    expect(anns.stageBand0).toBeUndefined();
  });

  it("findStageAtIndex prefers last overlapping stage", () => {
    const stages = resolveChartStages(
      ["A", "B", "C", "D"],
      [
        { start: "A", end: "C", tone: "up", reason: "一" },
        { start: "B", end: "D", tone: "down", reason: "二" },
      ],
    );
    expect(findStageAtIndex(stages, 1)?.reason).toBe("二");
    expect(findStageAtIndex(stages, 0)?.reason).toBe("一");
    expect(findStageAtIndex(stages, 9)).toBeNull();
  });

  function bandRanges(anns: Record<string, unknown>): Array<{ xMin: number; xMax: number; color: string }> {
    return Object.entries(anns)
      .filter(([k]) => k.startsWith("stageBand"))
      .map(([, v]) => {
        const box = v as { xMin: number; xMax: number; backgroundColor: string };
        return { xMin: box.xMin, xMax: box.xMax, color: box.backgroundColor };
      })
      .sort((a, b) => a.xMin - b.xMin);
  }

  it("exclusiveStageRanges last-wins shared endpoint so later stage owns the boundary bar", () => {
    const raw = resolveChartStages(
      ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
      [
        { start: "2026-01-01", end: "2026-01-02", tone: "up", reason: "补库" },
        { start: "2026-01-02", end: "2026-01-04", tone: "down", reason: "获利了结" },
      ],
    );
    const clipped = exclusiveStageRanges(raw);
    expect(clipped).toHaveLength(2);
    expect(clipped[0]).toMatchObject({ startIndex: 0, endIndex: 0, reason: "补库" });
    expect(clipped[1]).toMatchObject({ startIndex: 1, endIndex: 3, reason: "获利了结" });
    expect(findStageAtIndex(clipped, 1)?.reason).toBe("获利了结");
  });

  it("buildStageAnnotations abut exclusive bands at shared daily endpoint", () => {
    const labels = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"];
    const ohlc = [
      { o: 100, h: 110, l: 99, c: 108 },
      { o: 108, h: 109, l: 90, c: 92 },
      { o: 92, h: 93, l: 80, c: 82 },
      { o: 82, h: 84, l: 70, c: 72 },
    ];
    const bands = bandRanges(
      buildStageAnnotations(
        labels,
        ohlc,
        [
          { start: "2026-01-01", end: "2026-01-02", tone: "up", reason: "补库" },
          { start: "2026-01-02", end: "2026-01-04", tone: "down", reason: "获利了结" },
        ],
        false,
      ),
    );
    expect(bands).toHaveLength(2);
    expect(bands[0]!.xMax).toBe(bands[1]!.xMin);
  });

  it("monthly labels with daily stages keep one tone per bar", () => {
    const labels = ["2026-05", "2026-06", "2026-07", "2026-08"];
    const ohlc = [
      { o: 100, h: 110, l: 99, c: 108 },
      { o: 108, h: 109, l: 100, c: 101 },
      { o: 101, h: 102, l: 80, c: 82 },
      { o: 82, h: 120, l: 80, c: 118 },
    ];
    const stages = [
      { start: "2026-07-31", end: "2026-08-04", tone: "down" as const, reason: "急跌" },
      { start: "2026-08-04", end: "2026-08-17", tone: "up" as const, reason: "反弹" },
    ];
    const clipped = exclusiveStageRanges(resolveChartStages(labels, stages));
    const august = clipped.filter((s) => s.startIndex <= 3 && s.endIndex >= 3);
    expect(august).toHaveLength(1);
    expect(august[0]?.reason).toBe("反弹");
    const bands = bandRanges(buildStageAnnotations(labels, ohlc, stages, false));
    for (let i = 1; i < bands.length; i++) {
      expect(bands[i - 1]!.xMax).toBeLessThanOrEqual(bands[i]!.xMin);
    }
  });

  it("shows left axis hover panel; click pins so rail move keeps date", async () => {
    getValueForPixelMock.mockReturnValue(1);
    const candle = JSON.stringify({
      version: 1,
      type: "candlestick",
      labels: ["2026-01-01", "2026-01-02", "2026-01-03"],
      ohlc: [
        { o: 1, h: 2, l: 0.5, c: 1.5 },
        { o: 2, h: 5, l: 1.5, c: 4 },
        { o: 4, h: 4.2, l: 1, c: 1.2 },
      ],
      stages: [{ start: "2026-01-01", end: "2026-01-02", tone: "up", reason: "地缘溢价抬升" }],
    });
    render(<ChartBlock source={candle} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    // Default latest on mount, crosshair follows cursor.
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/2026-01-03/));
    expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("false");
    expect(screen.getByTestId("chart-crosshair-status").textContent).toMatch(/跟随|follows/i);

    const wrap = screen.getByTestId("chart-canvas-wrap");
    const canvas = screen.getByTestId("chart-canvas");
    const rect = {
      left: 0,
      top: 0,
      right: 400,
      bottom: 300,
      width: 400,
      height: 300,
      x: 0,
      y: 0,
      toJSON() {},
    } as DOMRect;
    vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue(rect);

    fireEvent.mouseMove(wrap, { clientX: 200, clientY: 40 });
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/2026-01-02/));
    const panel = screen.getByTestId("chart-axis-panel");
    expect(screen.queryByTestId("chart-stage-card")).toBeNull();
    expect(panel.style.left).toBe("4px");
    expect(screen.getByTestId("chart-hint-row").textContent).toMatch(/拖动平移|Drag to pan/);
    expect(screen.getByTestId("chart-hint-row").textContent).toMatch(/单击固定|Click to pin/);
    expect(screen.getByTestId("chart-hint-row").textContent).toMatch(/双击取消|double-click/i);
    expect(screen.getByTestId("chart-hint-row").getAttribute("data-reveal")).toBe("hover");
    expect(screen.getByTestId("chart-hint-row").getAttribute("data-slot")).toBe("top");
    expect(
      screen.getByTestId("chart-hint-row").compareDocumentPosition(screen.getByTestId("chart-canvas-wrap")) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    const dateEl = screen.getByTestId("chart-axis-panel-date");
    const ohlcEl = screen.getByTestId("chart-axis-panel-ohlc");
    const stageEl = screen.getByTestId("chart-axis-panel-stage");
    expect(dateEl.compareDocumentPosition(ohlcEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(ohlcEl.compareDocumentPosition(stageEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(ohlcEl.textContent).toMatch(/收盘|Close/);
    expect(ohlcEl.textContent).toMatch(/4\.00/);

    // Without pin, leaving plot reverts to latest (not empty).
    fireEvent.mouseMove(wrap, { clientX: 40, clientY: 40 });
    await waitFor(() =>
      expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/2026-01-03/),
    );

    // Hover + click pins; sweeping other bars / rail keeps date.
    getValueForPixelMock.mockReturnValue(1);
    fireEvent.mouseMove(wrap, { clientX: 200, clientY: 40 });
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/2026-01-02/));
    fireEvent.mouseDown(wrap, { clientX: 200, clientY: 40, button: 0 });
    fireEvent.click(wrap, { clientX: 200, clientY: 40, button: 0 });
    await waitFor(() =>
      expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("true"),
    );
    getValueForPixelMock.mockReturnValue(0);
    fireEvent.mouseMove(wrap, { clientX: 180, clientY: 80 });
    fireEvent.mouseMove(wrap, { clientX: 40, clientY: 40 });
    expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/2026-01-02/);

    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => {
      expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("false");
      expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/2026-01-03/);
    });

    getValueForPixelMock.mockReturnValue(1);
    fireEvent.mouseMove(wrap, { clientX: 200, clientY: 40 });
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/2026-01-02/));
    fireEvent.mouseDown(wrap, { clientX: 200, clientY: 40, button: 0 });
    fireEvent.click(wrap, { clientX: 200, clientY: 40, button: 0 });
    await waitFor(() =>
      expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("true"),
    );
    fireEvent.doubleClick(wrap, { clientX: 200, clientY: 40 });
    await waitFor(() =>
      expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("false"),
    );
  });

  it("line chart defaults to latest with crosshair following and centers short panel", async () => {
    render(<ChartBlock source={validLine} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel")).toBeTruthy());
    expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/D2/);
    expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("false");
    expect(screen.getByTestId("chart-crosshair-status").textContent).toMatch(/跟随|follows/i);
    expect(screen.getByTestId("chart-axis-panel").getAttribute("data-centered")).toBe("true");
    expect(screen.getByTestId("chart-axis-panel-series").textContent).toMatch(/6035\.00/);
    expect(screen.getByTestId("chart-hint-row").textContent).toMatch(/拖动平移|Drag to pan/);
    expect(screen.getByTestId("chart-hint-row").textContent).toMatch(/双击取消|double-click/i);
    expect(screen.getByTestId("chart-hint-row").getAttribute("data-reveal")).toBe("hover");
    expect(screen.getByTestId("chart-hint-row").getAttribute("data-slot")).toBe("top");
    expect(
      screen.getByTestId("chart-hint-row").compareDocumentPosition(screen.getByTestId("chart-canvas-wrap")) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();

    const wrap = screen.getByTestId("chart-canvas-wrap");
    const canvas = screen.getByTestId("chart-canvas");
    vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue({
      left: 0,
      top: 0,
      right: 400,
      bottom: 300,
      width: 400,
      height: 300,
      x: 0,
      y: 0,
      toJSON() {},
    } as DOMRect);
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() =>
      expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("false"),
    );
    getValueForPixelMock.mockReturnValue(0);
    fireEvent.mouseMove(wrap, { clientX: 200, clientY: 40 });
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/D1/));
    expect(screen.getByTestId("chart-axis-panel-series").textContent).toMatch(/6100\.00/);

    fireEvent.mouseDown(wrap, { clientX: 200, clientY: 40, button: 0 });
    fireEvent.click(wrap, { clientX: 200, clientY: 40, button: 0 });
    await waitFor(() =>
      expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("true"),
    );
    fireEvent.doubleClick(wrap, { clientX: 200, clientY: 40 });
    await waitFor(() =>
      expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("false"),
    );
  });

  it("focusLabel highlights that date on mount without pinning", async () => {
    const withFocus = JSON.stringify({
      version: 1,
      type: "line",
      labels: ["D1", "D2", "D3"],
      series: [{ name: "价", values: [1, 2, 3] }],
      focusLabel: "D1",
    });
    render(<ChartBlock source={withFocus} />);
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/D1/));
    expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("false");
  });

  it("line stages paint annotations and show in panel", async () => {
    const withStages = JSON.stringify({
      version: 1,
      type: "line",
      labels: ["D1", "D2", "D3"],
      series: [{ name: "价", values: [10, 20, 15] }],
      stages: [{ start: "D1", end: "D2", tone: "up", reason: "需求回暖" }],
      focusLabel: "D2",
    });
    const parsed = parseChartSpec(withStages);
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec);
    const annotation = (cfg.options?.plugins as { annotation?: { annotations: Record<string, unknown> } })
      ?.annotation;
    expect(annotation?.annotations?.stageBand0).toBeTruthy();

    render(<ChartBlock source={withStages} />);
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/D2/));
    expect(screen.getByTestId("chart-axis-panel-stage")).toBeTruthy();
    expect(screen.getByTestId("chart-axis-panel").getAttribute("data-centered")).toBe("true");
  });

  it("long series name keeps full four-digit price in axis panel", async () => {
    const longName = JSON.stringify({
      version: 1,
      type: "line",
      labels: ["07-23"],
      series: [
        { name: "黄埔区·聚合级均价", values: [8350.5] },
        { name: "西北·均价", values: [8219] },
      ],
    });
    render(<ChartBlock source={longName} />);
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-series")).toBeTruthy());
    const seriesEl = screen.getByTestId("chart-axis-panel-series");
    expect(seriesEl.textContent).toMatch(/8350\.50/);
    expect(seriesEl.textContent).toMatch(/8219\.00/);
    expect(seriesEl.textContent).toContain("黄埔区·聚合级均价");
    const kv = seriesEl.querySelector(".chart-axis-panel-kv");
    expect(kv).toBeTruthy();
    expect(kv!.className).toMatch(/chart-axis-panel-kv--stack/);
    const nameEl = kv!.querySelector(".chart-axis-panel-k");
    const priceEl = kv!.querySelector(".chart-axis-panel-v");
    expect(nameEl?.textContent).toContain("黄埔区·聚合级均价");
    expect(priceEl?.textContent).toMatch(/8350\.50/);
    expect(nameEl!.compareDocumentPosition(priceEl!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("axis panel shows OHLC without stage section when no stages", async () => {
    getValueForPixelMock.mockReturnValue(0);
    const candle = JSON.stringify({
      version: 1,
      type: "candlestick",
      labels: ["2026-01-01"],
      ohlc: [{ o: 1, h: 2, l: 0.5, c: 1.5 }],
    });
    render(<ChartBlock source={candle} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    const wrap = screen.getByTestId("chart-canvas-wrap");
    const canvas = screen.getByTestId("chart-canvas");
    vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue({
      left: 0,
      top: 0,
      right: 400,
      bottom: 300,
      width: 400,
      height: 300,
      x: 0,
      y: 0,
      toJSON() {},
    } as DOMRect);
    fireEvent.mouseMove(wrap, { clientX: 200, clientY: 40 });
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel")).toBeTruthy());
    expect(screen.queryByTestId("chart-axis-panel-stage")).toBeNull();
    expect(screen.getByTestId("chart-axis-panel-ohlc").textContent).toMatch(/开盘|Open/);
    expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/2026-01-01/);
    expect(screen.getByTestId("chart-axis-panel").getAttribute("data-centered")).toBe("true");
    const ohlcKv = screen.getByTestId("chart-axis-panel-ohlc").querySelector(".chart-axis-panel-kv");
    expect(ohlcKv?.className).toMatch(/chart-axis-panel-kv--row/);
    expect(ohlcKv?.className).not.toMatch(/chart-axis-panel-kv--stack/);
  });

  it("opens chart lightbox from fullscreen and closes on Escape", async () => {
    render(<ChartBlock source={validLine} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("chart-fullscreen"));
    await waitFor(() => expect(screen.getByTestId("chart-lightbox")).toBeTruthy());
    expect(
      screen.getByTestId("chart-lightbox").querySelector("[data-testid='chart-hint-row']")?.getAttribute("data-reveal"),
    ).toBe("always");
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByTestId("chart-lightbox")).toBeNull());
  });

  it("chartJsConfigFromSpec disables OHLC tooltip, adds crosshair, no arrows", () => {
    const parsed = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["D1", "D2", "D3"],
        ohlc: [
          { o: 1, h: 2, l: 0.5, c: 1.5 },
          { o: 2, h: 5, l: 1.5, c: 4 },
          { o: 4, h: 4.2, l: 1, c: 1.2 },
        ],
        stages: [{ start: "D1", end: "D2", tone: "up", reason: "上涨" }],
      }),
    );
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec);
    const annotation = (cfg.options?.plugins as { annotation?: { annotations: Record<string, unknown> } })
      ?.annotation;
    expect(annotation?.annotations?.stageBand0).toBeTruthy();
    expect(annotation?.annotations?.stageArrow0).toBeUndefined();
    expect(annotation?.annotations?.stageReason0).toBeUndefined();
    expect(annotation?.annotations?.extreme0).toBeUndefined();
    expect((cfg.options?.plugins?.tooltip as { enabled?: boolean } | undefined)?.enabled).toBe(false);
    expect((cfg.options as { layout?: { padding?: { left?: number; top?: number } } })?.layout?.padding?.left).toBe(
      AXIS_PANEL_RAIL,
    );
    expect((cfg.options as { layout?: { padding?: { top?: number } } })?.layout?.padding?.top).toBeLessThan(
      CHART_PAD_TOP,
    );
    expect(AXIS_PANEL_RAIL).toBe(188);
    expect(cfg.plugins?.some((p) => (p as { id?: string }).id === "axisCrosshair")).toBe(true);
  });

  it("lightbox candle window is wider with larger rail", () => {
    const labels = Array.from({ length: 200 }, (_, i) => `D${i}`);
    const ohlc = labels.map((_, i) => ({ o: 1, h: 2, l: 0.5, c: 1.5 }));
    const parsed = parseChartSpec(
      JSON.stringify({ version: 1, type: "candlestick", labels, ohlc }),
    );
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec, undefined, {
      candleWindow: LIGHTBOX_CANDLE_WINDOW,
      axisPanelRail: AXIS_PANEL_RAIL_LIGHTBOX,
    });
    expect(LIGHTBOX_CANDLE_WINDOW).toBe(180);
    expect(AXIS_PANEL_RAIL_LIGHTBOX).toBe(208);
    expect((cfg.options as { layout?: { padding?: { left?: number } } })?.layout?.padding?.left).toBe(208);
    expect((cfg.options as { scales?: { x?: { min?: number; max?: number } } })?.scales?.x?.min).toBe(20);
    expect((cfg.options as { scales?: { x?: { max?: number } } })?.scales?.x?.max).toBe(199);
  });

  it("candlestick without stages has no annotation plugin bag", () => {
    const parsed = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["D1"],
        ohlc: [{ o: 1, h: 2, l: 0.5, c: 1.5 }],
      }),
    );
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec);
    expect((cfg.options?.plugins as { annotation?: unknown })?.annotation).toBeUndefined();
    expect((cfg.options?.plugins?.tooltip as { enabled?: boolean } | undefined)?.enabled).toBe(false);
    expect(cfg.plugins?.some((p) => (p as { id?: string }).id === "axisCrosshair")).toBe(true);
  });

  it("lightbox showExtremes paints two extremes even without stages", () => {
    const parsed = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["D1", "D2"],
        ohlc: [
          { o: 1, h: 4, l: 1, c: 2 },
          { o: 2, h: 3, l: 0.5, c: 1 },
        ],
      }),
    );
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec, undefined, { showExtremes: true });
    const anns = (cfg.options?.plugins as { annotation?: { annotations: Record<string, unknown> } })
      ?.annotation?.annotations;
    expect(anns).toBeTruthy();
    const contents = extremeContents(anns ?? {});
    expect(contents).toHaveLength(2);
    expect(contents).toContain("4.00");
    expect(contents).toContain("0.50");
    expect(
      (cfg.options as { layout?: { padding?: { top?: number } } })?.layout?.padding?.top,
    ).toBe(CHART_PAD_TOP);
  });
});

describe("candlestick default window and zoom", () => {
  it("defaultCandleXWindow shows latest 90 when N > 90", () => {
    expect(DEFAULT_CANDLE_WINDOW).toBe(90);
    expect(defaultCandleXWindow(200)).toEqual({ min: 110, max: 199 });
    expect(defaultCandleXWindow(50)).toEqual({ min: 0, max: 49 });
    expect(defaultCandleXWindow(0)).toEqual({ min: 0, max: 0 });
  });

  it("yRangeForVisibleBars uses highs/lows in slice with padding", () => {
    const ohlc = [
      { o: 10, h: 12, l: 9, c: 11 },
      { o: 20, h: 50, l: 18, c: 40 },
      { o: 5, h: 6, l: 1, c: 2 },
    ];
    const range = yRangeForVisibleBars(ohlc, 1, 1, 0);
    expect(range).toEqual({ min: 18, max: 50 });
    const padded = yRangeForVisibleBars(ohlc, 1, 1, 0.05);
    expect(padded!.min).toBeLessThan(18);
    expect(padded!.max).toBeGreaterThan(50);
  });

  it("chartJsConfigFromSpec applies latest window, zoom plugin, and visible Y", () => {
    const labels = Array.from({ length: 100 }, (_, i) => `D${i}`);
    const ohlc = labels.map((_, i) => ({
      o: 100 + i,
      h: 110 + i,
      l: 90 + i,
      c: 105 + i,
    }));
    const parsed = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels,
        ohlc,
      }),
    );
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec);
    const x = cfg.options?.scales?.x as { min?: number; max?: number; offset?: boolean } | undefined;
    expect(x?.min).toBe(10);
    expect(x?.max).toBe(99);
    expect(x?.offset).toBe(false);
    const y = cfg.options?.scales?.y as { min?: number; max?: number } | undefined;
    expect(y?.min).toBeDefined();
    expect(y?.max).toBeDefined();
    // Visible slice highs/lows roughly 100..209 with pad — not full-series floor 90.
    expect(y!.min!).toBeGreaterThan(85);
    const zoom = (cfg.options?.plugins as { zoom?: { pan?: { enabled?: boolean }; zoom?: { wheel?: { enabled?: boolean } } } })
      ?.zoom;
    expect(zoom?.pan?.enabled).toBe(true);
    expect(zoom?.zoom?.wheel?.enabled).toBe(true);
  });
});

describe("spot line default window, zoom, density, and label room", () => {
  function lineSpec(n: number, values?: number[]) {
    const labels = Array.from({ length: n }, (_, i) => `2026-01-${String(i + 1).padStart(2, "0")}`);
    const seriesValues = values ?? labels.map((_, i) => 2000 + i);
    return JSON.stringify({
      version: 1,
      type: "line",
      title: "甲醇现货均价",
      labels,
      series: [{ name: "现货均价", values: seriesValues }],
    });
  }

  it("yRangeForVisibleSeries pads visible slice", () => {
    const values = [10, 50, 1];
    const range = yRangeForVisibleSeries(values, 1, 1, 0);
    expect(range).toEqual({ min: 50, max: 50 });
    const padded = yRangeForVisibleSeries(values, 1, 1, 0.08);
    expect(padded!.min).toBeLessThan(50);
    expect(padded!.max).toBeGreaterThan(50);
  });

  it("chartJsConfigFromSpec enables pan/zoom and latest window for long line series", () => {
    const parsed = parseChartSpec(lineSpec(120));
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec);
    const x = cfg.options?.scales?.x as {
      min?: number;
      max?: number;
      ticks?: { maxTicksLimit?: number; autoSkip?: boolean };
    } | undefined;
    expect(x?.min).toBe(30);
    expect(x?.max).toBe(119);
    expect(x?.ticks?.maxTicksLimit).toBe(8);
    expect(x?.ticks?.autoSkip).toBe(true);
    const y = cfg.options?.scales?.y as { min?: number; max?: number } | undefined;
    expect(y?.min).toBeDefined();
    expect(y?.max).toBeDefined();
    // Visible window starts at 2030, not full-series floor 2000.
    expect(y!.min!).toBeGreaterThan(2015);
    const zoom = (cfg.options?.plugins as { zoom?: { pan?: { enabled?: boolean }; zoom?: { wheel?: { enabled?: boolean } } } })
      ?.zoom;
    expect(zoom?.pan?.enabled).toBe(true);
    expect(zoom?.zoom?.wheel?.enabled).toBe(true);
    const pad = (cfg.options as { layout?: { padding?: { right?: number; bottom?: number; top?: number } } })
      ?.layout?.padding;
    expect(pad?.right ?? 0).toBe(0);
    expect(pad?.bottom).toBeLessThan(16);
    expect(pad?.top).toBeLessThan(28);
  });

  it("hides point markers when many points are visible, shows them when zoomed in", () => {
    const parsed = parseChartSpec(lineSpec(60));
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec);
    const ds = cfg.data?.datasets?.[0] as {
      pointRadius?: number | ((ctx: { chart: { scales: { x?: { min: number; max: number } } } }) => number);
    };
    expect(DENSE_POINT_THRESHOLD).toBeLessThanOrEqual(24);
    expect(typeof ds.pointRadius).toBe("function");
    const dense = ds.pointRadius as (ctx: {
      chart: { scales: { x?: { min: number; max: number } } };
    }) => number;
    expect(dense({ chart: { scales: { x: { min: 0, max: 59 } } } })).toBe(0);
    expect(dense({ chart: { scales: { x: { min: 50, max: 59 } } } })).toBeGreaterThan(0);
  });

  it("shifts right-edge extreme labels left so last price is not clipped", () => {
    const labels = Array.from({ length: 10 }, (_, i) => `D${i}`);
    const values = [10, 11, 12, 13, 14, 15, 16, 17, 18, 50];
    const anns = buildSeriesStageAnnotations(
      labels,
      values,
      [{ start: "D0", end: "D9", tone: "up", reason: "尾盘走强" }],
      false,
      { showExtremes: true },
    );
    const high = Object.values(anns).find(
      (v) => (v as { content?: string }).content === "50.00",
    ) as { xAdjust?: number; yAdjust?: number } | undefined;
    expect(high).toBeTruthy();
    expect(high!.xAdjust!).toBeLessThan(0);
  });

  it("places high labels above and low labels below the point", () => {
    const labels = ["D0", "D1", "D2", "D3"];
    const values = [50, 40, 10, 30];
    const anns = buildSeriesStageAnnotations(
      labels,
      values,
      [{ start: "D0", end: "D3", tone: "down", reason: "探底" }],
      false,
      { showExtremes: true },
    );
    const high = Object.values(anns).find(
      (v) => (v as { content?: string }).content === "50.00",
    ) as { yAdjust?: number } | undefined;
    const low = Object.values(anns).find(
      (v) => (v as { content?: string }).content === "10.00",
    ) as { yAdjust?: number } | undefined;
    expect(high).toBeTruthy();
    expect(low).toBeTruthy();
    expect(high!.yAdjust!).toBeLessThan(0);
    expect(low!.yAdjust!).toBeGreaterThan(0);
  });

  it("fullscreen extremes keep only global high and low, not nearby stage lows", () => {
    const labels = ["D0", "D1", "D2", "D3", "D4", "D5"];
    const values = [3000, 2900, 2374, 2348, 2500, 2600];
    const anns = buildSeriesStageAnnotations(
      labels,
      values,
      [
        { start: "D0", end: "D2", tone: "down", reason: "探底一" },
        { start: "D3", end: "D5", tone: "up", reason: "反弹" },
      ],
      false,
      { showExtremes: true },
    );
    const contents = extremeContents(anns);
    expect(contents).toHaveLength(2);
    expect(contents).toContain("3000.00");
    expect(contents).toContain("2348.00");
    expect(contents).not.toContain("2374.00");
  });

  it("candlestick and line reserve top pad for high labels only when showing extremes", () => {
    expect(CHART_PAD_TOP).toBeGreaterThanOrEqual(28);
    const candle = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["A", "B"],
        ohlc: [
          { o: 1, h: 2, l: 0.5, c: 1.5 },
          { o: 2, h: 3, l: 1, c: 2.5 },
        ],
      }),
    );
    expect(candle.ok).toBe(true);
    if (!candle.ok) return;
    const inlinePad = (chartJsConfigFromSpec(candle.spec).options as {
      layout?: { padding?: { top?: number; bottom?: number } };
    })?.layout?.padding;
    expect(inlinePad?.top).toBeLessThan(28);
    const lightboxPad = (chartJsConfigFromSpec(candle.spec, undefined, { showExtremes: true })
      .options as { layout?: { padding?: { top?: number; bottom?: number } } })?.layout?.padding;
    expect(lightboxPad?.top).toBeGreaterThanOrEqual(28);
    expect(lightboxPad?.bottom).toBeGreaterThanOrEqual(16);

    const line = parseChartSpec(lineSpec(5));
    expect(line.ok).toBe(true);
    if (!line.ok) return;
    const linePad = (chartJsConfigFromSpec(line.spec).options as {
      layout?: { padding?: { top?: number } };
    })?.layout?.padding;
    expect(linePad?.top).toBeLessThan(28);
  });

  it("bar charts stay without zoom pan", () => {
    const parsed = parseChartSpec(validBar);
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const cfg = chartJsConfigFromSpec(parsed.spec);
    const zoom = (cfg.options?.plugins as { zoom?: { pan?: { enabled?: boolean } } } | undefined)?.zoom;
    expect(zoom?.pan?.enabled).not.toBe(true);
  });
});

describe("stage tone recompute and driver sanitization", () => {
  it("classifyStageTones maps relative returns to up/down/side", () => {
    expect(classifyStageTones([0.08, -0.06, 0.012, 0.07])).toEqual(["up", "down", "side", "up"]);
  });

  it("does not keep a larger-move interval as side versus a smaller up/down", () => {
    const tones = classifyStageTones([0.05, 0.03]);
    expect(tones[0]).not.toBe("side");
    const sideAbs = tones
      .map((tone, i) => (tone === "side" ? Math.abs([0.05, 0.03][i]!) : null))
      .filter((v): v is number => v != null);
    const dirAbs = tones
      .map((tone, i) => (tone === "up" || tone === "down" ? Math.abs([0.05, 0.03][i]!) : null))
      .filter((v): v is number => v != null);
    for (const s of sideAbs) {
      for (const d of dirAbs) expect(s).toBeLessThan(d);
    }
  });

  it("treats a nearly flat set as all side", () => {
    expect(classifyStageTones([0.001, -0.002, 0.0015])).toEqual(["side", "side", "side"]);
  });

  it("stageReturnPct is null when start is zero or non-finite", () => {
    expect(stageReturnPct(0, 10)).toBeNull();
    expect(stageReturnPct(Number.NaN, 10)).toBeNull();
    expect(stageReturnPct(100, 108)).toBeCloseTo(0.08);
  });

  it("overlayComputedStageTones overrides a mistaken LLM side label", () => {
    const stages = resolveChartStages(
      ["A", "B", "C", "D"],
      [
        { start: "A", end: "B", tone: "side", reason: "横盘" },
        { start: "C", end: "D", tone: "up", reason: "反弹" },
      ],
    );
    const closes = [100, 105, 103, 106];
    const painted = overlayComputedStageTones(stages, (i) => closes[i] ?? null);
    expect(painted[0]?.tone).not.toBe("side");
    expect(painted[0]?.tone).toBe("up");
  });

  it("buildStageAnnotations uses recomputed tone for band color", () => {
    const labels = ["D1", "D2"];
    const ohlc = [
      { o: 100, h: 101, l: 99, c: 100 },
      { o: 100, h: 110, l: 100, c: 108 },
    ];
    const anns = buildStageAnnotations(
      labels,
      ohlc,
      [{ start: "D1", end: "D2", tone: "side", reason: "横盘整理" }],
      false,
    );
    expect(anns.stageBand0).toMatchObject({
      type: "box",
      backgroundColor: STAGE_TONE_COLORS.up.band,
    });
  });

  it("sanitizeStageReason strips specific prices", () => {
    expect(sanitizeStageReason("回落到 2374.00 附近，需求回暖")).not.toMatch(/2374/);
    expect(sanitizeStageReason("装置检修收紧供应")).toBe("装置检修收紧供应");
  });

  it("axis panel hides drivers when reason is only a price, and strips prices otherwise", async () => {
    const withPrice = JSON.stringify({
      version: 1,
      type: "candlestick",
      labels: ["D1", "D2"],
      ohlc: [
        { o: 100, h: 110, l: 99, c: 100 },
        { o: 100, h: 120, l: 100, c: 118 },
      ],
      stages: [{ start: "D1", end: "D2", tone: "up", reason: "回落到 2374.00 附近，需求回暖" }],
      focusLabel: "D2",
    });
    render(<ChartBlock source={withPrice} />);
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-stage")).toBeTruthy());
    const reason = screen.getByTestId("chart-axis-panel-reason");
    expect(reason.textContent).not.toMatch(/2374/);
    expect(reason.textContent).toMatch(/需求回暖/);

    cleanup();
    const onlyPrice = JSON.stringify({
      version: 1,
      type: "candlestick",
      labels: ["D1", "D2"],
      ohlc: [
        { o: 100, h: 110, l: 99, c: 100 },
        { o: 100, h: 120, l: 100, c: 118 },
      ],
      stages: [{ start: "D1", end: "D2", tone: "up", reason: "2374.00" }],
      focusLabel: "D2",
    });
    render(<ChartBlock source={onlyPrice} />);
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-stage")).toBeTruthy());
    expect(screen.queryByTestId("chart-axis-panel-reason")).toBeNull();
  });
});
