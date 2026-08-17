import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ChartBlock } from "./ChartBlock";

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
