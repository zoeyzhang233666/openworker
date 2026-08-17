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
import { parseChartSpec, type ChartSpec } from "../chartSpec";
import { useI18n } from "../i18n";

// Tree-shaken chart.js requires controllers + elements; missing LineController
// surfaces as: "line" is not a registered controller.
Chart.register(
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

/** Build Chart.js config from a validated ChartSpec (never from raw model options). */
export function chartJsConfigFromSpec(spec: ChartSpec): ChartConfiguration {
  const colors = themeColors();
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

  const yTitle = spec.yTitle || (spec.unit ? spec.unit : undefined);

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
              const base = `${ctx.dataset.label ?? ""}: ${Number.isFinite(y) ? y : "—"}`;
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

export function ChartBlock({ source }: { source: string }): JSX.Element {
  const { t } = useI18n();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);
  const [view, setView] = useState<ViewMode>("chart");
  const [error, setError] = useState<string | null>(null);

  const parsed = useMemo(() => parseChartSpec(source), [source]);

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
      chartRef.current = new Chart(canvas, chartJsConfigFromSpec(parsed.spec));
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
  }, [source, parsed]);

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
