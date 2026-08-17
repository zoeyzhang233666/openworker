import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ChartBlock, chartJsConfigFromSpec, formatChartPrice, CN_CANDLE_COLORS } from "./ChartBlock";
import { parseChartSpec } from "../chartSpec";

const destroyMock = vi.fn();
const getChartDestroyMock = vi.fn();
const getChartMock = vi.fn((): { destroy: typeof getChartDestroyMock } | undefined => undefined);
const ChartMock = vi.fn().mockImplementation(() => ({ destroy: destroyMock }));

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
  Tooltip: {},
}));

vi.mock("chartjs-chart-financial", () => ({
  CandlestickController: {},
  CandlestickElement: {},
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
    fireEvent.click(screen.getByRole("button", { name: /源码|Source/i }));
    expect(screen.getByTestId("chart-source").textContent).toContain('"labels"');
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

  it("candlestick tooltip title uses date label and Chinese OHLC lines", () => {
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
    const title = cfg.options?.plugins?.tooltip?.callbacks?.title as
      | ((items: { dataIndex: number }[]) => string)
      | undefined;
    const label = cfg.options?.plugins?.tooltip?.callbacks?.label as
      | ((ctx: { raw: { o: number; h: number; l: number; c: number } }) => string | string[])
      | undefined;
    expect(title?.([{ dataIndex: 0 }])).toBe("2026-05-18");
    const lines = label?.({
      raw: {
        o: 93.44999694824219,
        h: 97,
        l: 93.44999694824219,
        c: 96.0199966430664,
      },
    });
    expect(Array.isArray(lines)).toBe(true);
    expect(lines).toEqual([
      "开盘 93.45 USD",
      "最高 97.00 USD",
      "最低 93.45 USD",
      "收盘 96.02 USD",
    ]);
    expect(JSON.stringify(lines)).not.toMatch(/\bO \d/);
  });

  it("line tooltip formats y to two decimals", () => {
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
    const label = cfg.options?.plugins?.tooltip?.callbacks?.label as
      | ((ctx: { parsed: number; dataset: { label?: string } }) => string)
      | undefined;
    expect(label?.({ parsed: 6100.129, dataset: { label: "价" } })).toBe("价: 6100.13");
  });
});
