import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ChartBlock, chartJsConfigFromSpec, formatChartPrice, CN_CANDLE_COLORS, STAGE_TONE_COLORS, buildStageAnnotations, findStageAtIndex, resolveChartStages, defaultCandleXWindow, yRangeForVisibleBars, DEFAULT_CANDLE_WINDOW, AXIS_PANEL_RAIL, AXIS_PANEL_RAIL_LIGHTBOX, LIGHTBOX_CANDLE_WINDOW } from "./ChartBlock";
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

describe("candlestick stage annotations", () => {
  it("buildStageAnnotations emits bands and extremes without arrows or reason text", () => {
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
    const extremeContents = Object.entries(anns)
      .filter(([k]) => k.startsWith("extreme"))
      .map(([, v]) => (v as { content: string }).content);
    expect(extremeContents).toContain("80.00");
    expect(extremeContents).toContain("55.00");
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
    // Default latest on mount, pinned.
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/2026-01-03/));
    expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("true");

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

    // Unpin so hover can snap.
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() =>
      expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("false"),
    );

    fireEvent.mouseMove(wrap, { clientX: 200, clientY: 40 });
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/2026-01-02/));
    const panel = screen.getByTestId("chart-axis-panel");
    expect(screen.queryByTestId("chart-stage-card")).toBeNull();
    expect(panel.style.left).toBe("4px");
    expect(screen.getByTestId("chart-hint-row").textContent).toMatch(/拖动平移|Drag to pan/);
    expect(screen.getByTestId("chart-hint-row").textContent).toMatch(/单击固定|Click to pin/);
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
  });

  it("line chart defaults to latest pinned and centers short panel", async () => {
    render(<ChartBlock source={validLine} />);
    await waitFor(() => expect(ChartMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel")).toBeTruthy());
    expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/D2/);
    expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("true");
    expect(screen.getByTestId("chart-axis-panel").getAttribute("data-centered")).toBe("true");
    expect(screen.getByTestId("chart-axis-panel-series").textContent).toMatch(/6035\.00/);
    expect(screen.getByTestId("chart-hint-row").textContent).toMatch(/十字线|Crosshair/);
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
  });

  it("focusLabel pins that date on mount", async () => {
    const withFocus = JSON.stringify({
      version: 1,
      type: "line",
      labels: ["D1", "D2", "D3"],
      series: [{ name: "价", values: [1, 2, 3] }],
      focusLabel: "D1",
    });
    render(<ChartBlock source={withFocus} />);
    await waitFor(() => expect(screen.getByTestId("chart-axis-panel-date").textContent).toMatch(/D1/));
    expect(screen.getByTestId("chart-axis-panel").getAttribute("data-pinned")).toBe("true");
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
    expect(annotation?.annotations?.extreme0).toBeTruthy();
    expect((cfg.options?.plugins?.tooltip as { enabled?: boolean } | undefined)?.enabled).toBe(false);
    expect((cfg.options as { layout?: { padding?: { left?: number; top?: number } } })?.layout?.padding?.left).toBe(
      AXIS_PANEL_RAIL,
    );
    expect((cfg.options as { layout?: { padding?: { top?: number } } })?.layout?.padding?.top).toBe(18);
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
