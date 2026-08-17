import { useEffect, useMemo, useRef, useState } from "react";
import {
  Chart,
  LineController,
  BarController,
  ScatterController,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Filler,
  Legend,
  Title,
  Tooltip,
  type ChartConfiguration,
  type ChartType as ChartJsType,
} from "chart.js";
import { CandlestickController, CandlestickElement } from "chartjs-chart-financial";
import { resolveChartSource, type ChartSpec, type ChartToolResult } from "../chartSpec";
import { useI18n } from "../i18n";

// Tree-shaken chart.js requires controllers + elements; missing LineController
// surfaces as: "line" is not a registered controller.
Chart.register(
  LineController,
  BarController,
  ScatterController,
  CandlestickController,
  CandlestickElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Filler,
  Legend,
  Title,
  Tooltip,
);

type ViewMode = "chart" | "source";

function isDarkTheme(): boolean {
  const attr = document.documentElement.getAttribute("data-theme");
  if (attr === "dark") return true;
  if (attr === "light") return false;
  return window.matchMedia?.("(prefers-color-scheme: dark)")?.matches ?? false;
}

function themeColors() {
  const dark = isDarkTheme();
  return {
    text: dark ? "#e8eaed" : "#1f2937",
    muted: dark ? "#9aa0a6" : "#6b7280",
    grid: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
  };
}

/**
 * Fixed series palette — Chart.js v4 does not auto-color tree-shaken builds.
 * Okabe–Ito qualitative order (colorblind-friendly / journal-style), with slot 0
 * kept as ChemClaw cobalt (#2563eb).
 */
const SERIES_PALETTE = [
  { border: "#2563eb", fill: "rgba(37, 99, 235, 0.15)" }, // ChemClaw cobalt
  { border: "#D55E00", fill: "rgba(213, 94, 0, 0.15)" }, // vermillion
  { border: "#009E73", fill: "rgba(0, 158, 115, 0.15)" }, // bluish green
  { border: "#CC79A7", fill: "rgba(204, 121, 167, 0.15)" }, // reddish purple
  { border: "#E69F00", fill: "rgba(230, 159, 0, 0.15)" }, // amber
  { border: "#56B4E9", fill: "rgba(86, 180, 233, 0.15)" }, // sky blue
  { border: "#7A5195", fill: "rgba(122, 81, 149, 0.15)" }, // muted violet
  { border: "#4D4D4D", fill: "rgba(77, 77, 77, 0.15)" }, // charcoal
] as const;

function seriesPaint(index: number) {
  return SERIES_PALETTE[index % SERIES_PALETTE.length]!;
}

/** 国内行情习惯（同花顺/文华）：红涨绿跌。 */
export const CN_CANDLE_COLORS = {
  border: {
    up: "#E53935",
    down: "#1B9E5A",
    unchanged: "#9E9E9E",
  },
  background: {
    up: "rgba(229, 57, 53, 0.75)",
    down: "rgba(27, 158, 90, 0.75)",
    unchanged: "rgba(158, 158, 158, 0.45)",
  },
} as const;

/** Format chart prices for tooltips — at most two decimal places. */
export function formatChartPrice(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return value.toFixed(2);
}

export type ChartTooltipUi = {
  open: string;
  high: string;
  low: string;
  close: string;
};

const DEFAULT_OHLC_UI: ChartTooltipUi = {
  open: "开盘",
  high: "最高",
  low: "最低",
  close: "收盘",
};

function candlestickIndex(ctx: {
  dataIndex?: number;
  parsed?: unknown;
  raw?: unknown;
}): number {
  if (typeof ctx.dataIndex === "number" && Number.isFinite(ctx.dataIndex)) return ctx.dataIndex;
  const parsed = ctx.parsed;
  if (typeof parsed === "object" && parsed && "x" in parsed) {
    const x = Number((parsed as { x: unknown }).x);
    if (Number.isFinite(x)) return Math.round(x);
  }
  const raw = ctx.raw;
  if (typeof raw === "object" && raw && "x" in raw) {
    const x = Number((raw as { x: unknown }).x);
    if (Number.isFinite(x)) return Math.round(x);
  }
  return -1;
}

/** Build Chart.js config from a validated ChartSpec (never from raw model options). */
export function chartJsConfigFromSpec(
  spec: ChartSpec,
  ui: ChartTooltipUi = DEFAULT_OHLC_UI,
): ChartConfiguration {
  const colors = themeColors();
  const yTitle = spec.yTitle || (spec.unit ? spec.unit : undefined);
  const unitSuffix = spec.unit ? ` ${spec.unit}` : yTitle && !spec.unit ? ` ${yTitle}` : "";

  if (spec.type === "candlestick") {
    const bars = spec.ohlc ?? [];
    return {
      type: "candlestick",
      data: {
        datasets: [
          {
            label: spec.title || "OHLC",
            data: bars.map((bar, i) => ({ x: i, o: bar.o, h: bar.h, l: bar.l, c: bar.c })),
            borderColors: { ...CN_CANDLE_COLORS.border },
            backgroundColors: { ...CN_CANDLE_COLORS.background },
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: spec.showLegend === true,
            labels: { color: colors.text },
          },
          title: {
            display: !!spec.title,
            text: spec.subtitle ? [spec.title!, spec.subtitle] : spec.title,
            color: colors.text,
          },
          tooltip: {
            callbacks: {
              title(items) {
                const item = items[0];
                if (!item) return "";
                const i = candlestickIndex(item);
                return i >= 0 && spec.labels[i] != null ? String(spec.labels[i]) : "";
              },
              label(ctx) {
                const raw = ctx.raw as { o?: number; h?: number; l?: number; c?: number } | undefined;
                if (!raw) return "";
                return [
                  `${ui.open} ${formatChartPrice(raw.o)}${unitSuffix}`,
                  `${ui.high} ${formatChartPrice(raw.h)}${unitSuffix}`,
                  `${ui.low} ${formatChartPrice(raw.l)}${unitSuffix}`,
                  `${ui.close} ${formatChartPrice(raw.c)}${unitSuffix}`,
                ];
              },
            },
          },
        },
        scales: {
          x: {
            type: "linear",
            offset: true,
            title: spec.xTitle
              ? { display: true, text: spec.xTitle, color: colors.muted }
              : undefined,
            ticks: {
              color: colors.muted,
              callback(value) {
                const i = Number(value);
                return Number.isInteger(i) && spec.labels[i] != null ? spec.labels[i] : "";
              },
            },
            grid: { color: colors.grid },
          },
          y: {
            min: spec.yMin,
            max: spec.yMax,
            title: yTitle
              ? { display: true, text: yTitle, color: colors.muted }
              : undefined,
            ticks: { color: colors.muted },
            grid: { color: colors.grid },
          },
        },
      },
    };
  }

  const fill = spec.type === "area";
  const chartType: ChartJsType =
    spec.type === "area" ? "line" : spec.type === "scatter" ? "scatter" : spec.type;

  const datasets = spec.series.map((s, i) => {
    const paint = seriesPaint(i);
    if (spec.type === "scatter") {
      return {
        label: s.name,
        data: s.values.map((y, idx) =>
          y === null ? { x: Number.NaN, y: Number.NaN } : { x: idx, y },
        ),
        showLine: false,
        borderColor: paint.border,
        backgroundColor: paint.border,
        pointBackgroundColor: paint.border,
        pointBorderColor: paint.border,
      };
    }
    return {
      label: s.name,
      data: s.values,
      fill,
      tension: spec.type === "line" || spec.type === "area" ? 0.25 : 0,
      borderColor: paint.border,
      backgroundColor: fill || spec.type === "bar" ? paint.fill : paint.border,
      pointBackgroundColor: paint.border,
      pointBorderColor: paint.border,
      borderWidth: 2,
      pointRadius: spec.type === "bar" ? 0 : 3,
      pointHoverRadius: spec.type === "bar" ? 0 : 5,
    };
  });

  return {
    type: chartType,
    data: {
      labels: spec.type === "scatter" ? undefined : spec.labels,
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: spec.showLegend !== false,
          labels: { color: colors.text },
        },
        title: {
          display: !!spec.title,
          text: spec.subtitle ? [spec.title!, spec.subtitle] : spec.title,
          color: colors.text,
        },
        tooltip: {
          callbacks: {
            label(ctx) {
              const raw = ctx.parsed;
              const y =
                typeof raw === "object" && raw && "y" in raw
                  ? (raw as { y: number }).y
                  : typeof ctx.parsed === "number"
                    ? ctx.parsed
                    : NaN;
              const base = `${ctx.dataset.label ?? ""}: ${formatChartPrice(y)}`;
              return spec.unit ? `${base} ${spec.unit}` : base;
            },
          },
        },
      },
      scales: {
        x: {
          title: spec.xTitle
            ? { display: true, text: spec.xTitle, color: colors.muted }
            : undefined,
          ticks: { color: colors.muted },
          grid: { color: colors.grid },
          ...(spec.type === "scatter"
            ? {
                type: "linear" as const,
                ticks: {
                  color: colors.muted,
                  callback(value) {
                    const i = Number(value);
                    return Number.isInteger(i) && spec.labels[i] != null
                      ? spec.labels[i]
                      : "";
                  },
                },
              }
            : {}),
        },
        y: {
          min: spec.yMin,
          max: spec.yMax,
          title: yTitle
            ? { display: true, text: yTitle, color: colors.muted }
            : undefined,
          ticks: { color: colors.muted },
          grid: { color: colors.grid },
        },
      },
    },
  };
}

export function ChartBlock({
  source,
  chartToolResults,
}: {
  source: string;
  chartToolResults?: ChartToolResult[];
}): JSX.Element {
  const { t, locale } = useI18n();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);
  const [view, setView] = useState<ViewMode>("chart");
  const [error, setError] = useState<string | null>(null);

  // Stable signature so parent re-renders with a new array identity do not rebuild Chart.js.
  const toolsSig = (chartToolResults || [])
    .filter((t) => t.name === "lookup_yahoo_ohlc" && t.preview)
    .map((t) => t.preview!)
    .join("\0");

  const parsed = useMemo(
    () => resolveChartSource(source, chartToolResults),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- toolsSig stands in for chartToolResults
    [source, toolsSig],
  );

  const tooltipUi = useMemo(
    (): ChartTooltipUi => ({
      open: t("chart.ohlc.open"),
      high: t("chart.ohlc.high"),
      low: t("chart.ohlc.low"),
      close: t("chart.ohlc.close"),
    }),
    [t, locale],
  );

  useEffect(() => {
    function releaseCanvas(canvas: HTMLCanvasElement | null) {
      if (!canvas) {
        chartRef.current = null;
        return;
      }
      // Chart.js keeps a global registry on the canvas; chartRef alone is not enough
      // under React StrictMode (mount → cleanup → remount) or remount races.
      const existing = Chart.getChart(canvas);
      if (existing) existing.destroy();
      if (chartRef.current && chartRef.current !== existing) {
        try {
          chartRef.current.destroy();
        } catch {
          /* already destroyed via getChart */
        }
      }
      chartRef.current = null;
    }

    if (!parsed.ok) {
      releaseCanvas(canvasRef.current);
      setError(parsed.error);
      setView("source");
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;

    releaseCanvas(canvas);

    try {
      chartRef.current = new Chart(canvas, chartJsConfigFromSpec(parsed.spec, tooltipUi));
      setError(null);
      setView("chart");
    } catch (err) {
      releaseCanvas(canvas);
      setError(err instanceof Error ? err.message : String(err || ""));
      setView("source");
    }

    return () => {
      releaseCanvas(canvasRef.current);
    };
  }, [source, parsed, tooltipUi]);

  const showChart = view === "chart" && parsed.ok && !error;
  const showSource = view === "source" || !!error || !parsed.ok;

  return (
    <div
      className={`chart-block${error || !parsed.ok ? " is-error" : ""}`}
      data-testid="chart-block"
    >
      <div className="chart-block-toolbar">
        <button
          type="button"
          disabled={!parsed.ok || !!error}
          aria-pressed={view === "chart"}
          onClick={() => setView("chart")}
        >
          {t("chart.chart")}
        </button>
        <button
          type="button"
          aria-pressed={showSource}
          onClick={() => setView("source")}
        >
          {t("chart.source")}
        </button>
      </div>
      {(error || !parsed.ok) && (
        <div className="chart-block-error" data-testid="chart-error">
          {(!parsed.ok ? parsed.error : error) || t("chart.renderError")}
        </div>
      )}
      <div
        className="chart-block-canvas-wrap"
        data-testid="chart-canvas-wrap"
        hidden={!showChart}
      >
        <canvas ref={canvasRef} data-testid="chart-canvas" />
      </div>
      {showSource && (
        <pre className="chart-block-source" data-testid="chart-source">
          {source}
        </pre>
      )}
    </div>
  );
}
