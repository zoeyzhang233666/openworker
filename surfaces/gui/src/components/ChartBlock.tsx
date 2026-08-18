import { useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
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
import annotationPlugin from "chartjs-plugin-annotation";
import zoomPlugin from "chartjs-plugin-zoom";
import {
  findLabelIndex,
  resolveChartSource,
  type ChartOhlcBar,
  type ChartSpec,
  type ChartStage,
  type ChartToolResult,
} from "../chartSpec";
import { useI18n } from "../i18n";
import { ChartLightbox } from "./ChartLightbox";

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
  annotationPlugin,
  zoomPlugin,
);

/** Default visible bars for candlestick (latest window). */
export const DEFAULT_CANDLE_WINDOW = 90;

/** Fullscreen / lightbox default visible bars. */
export const LIGHTBOX_CANDLE_WINDOW = 180;

/** Left rail reserved for hover axis panel (outside chartArea). */
export const AXIS_PANEL_RAIL = 188;

/** Wider left rail in lightbox for larger detail panel. */
export const AXIS_PANEL_RAIL_LIGHTBOX = 208;

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

/** Stage band / arrow / reason colors (CN convention). */
export const STAGE_TONE_COLORS = {
  up: {
    band: "rgba(229, 57, 53, 0.12)",
    bandDark: "rgba(229, 57, 53, 0.22)",
    stroke: "#E53935",
    text: "#C62828",
  },
  down: {
    band: "rgba(27, 158, 90, 0.12)",
    bandDark: "rgba(27, 158, 90, 0.22)",
    stroke: "#1B9E5A",
    text: "#1B5E20",
  },
  side: {
    band: "rgba(37, 99, 235, 0.10)",
    bandDark: "rgba(37, 99, 235, 0.20)",
    stroke: "#2563eb",
    text: "#1565C0",
  },
} as const;

const MAX_EXTREME_LABELS = 8;

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

export type ResolvedStage = ChartStage & { startIndex: number; endIndex: number };

/** Resolve stage date strings to label indices (invalid stages dropped). */
export function resolveChartStages(
  labels: string[],
  stages: ChartStage[] | undefined,
): ResolvedStage[] {
  if (!stages?.length) return [];
  const out: ResolvedStage[] = [];
  for (const stage of stages) {
    let startIndex = findLabelIndex(labels, stage.start);
    let endIndex = findLabelIndex(labels, stage.end);
    if (startIndex < 0 || endIndex < 0) continue;
    if (startIndex > endIndex) {
      const tmp = startIndex;
      startIndex = endIndex;
      endIndex = tmp;
    }
    out.push({ ...stage, startIndex, endIndex });
  }
  return out;
}

/** Last matching stage wins when bands overlap (same as paint order). */
export function findStageAtIndex(stages: ResolvedStage[], index: number): ResolvedStage | null {
  if (!Number.isFinite(index)) return null;
  const i = Math.round(index);
  let found: ResolvedStage | null = null;
  for (const stage of stages) {
    if (i >= stage.startIndex && i <= stage.endIndex) found = stage;
  }
  return found;
}

function extremumInRange(
  bars: ChartOhlcBar[],
  startIndex: number,
  endIndex: number,
  kind: "high" | "low",
): { index: number; value: number } | null {
  let bestIdx = -1;
  let best = kind === "high" ? -Infinity : Infinity;
  for (let i = startIndex; i <= endIndex; i++) {
    const bar = bars[i];
    if (!bar) continue;
    const v = kind === "high" ? bar.h : bar.l;
    if (kind === "high" ? v > best : v < best) {
      best = v;
      bestIdx = i;
    }
  }
  if (bestIdx < 0 || !Number.isFinite(best)) return null;
  return { index: bestIdx, value: best };
}

function extremumInSeriesRange(
  values: Array<number | null>,
  startIndex: number,
  endIndex: number,
  kind: "high" | "low",
): { index: number; value: number } | null {
  let bestIdx = -1;
  let best = kind === "high" ? -Infinity : Infinity;
  for (let i = startIndex; i <= endIndex; i++) {
    const v = values[i];
    if (typeof v !== "number" || !Number.isFinite(v)) continue;
    if (kind === "high" ? v > best : v < best) {
      best = v;
      bestIdx = i;
    }
  }
  if (bestIdx < 0 || !Number.isFinite(best)) return null;
  return { index: bestIdx, value: best };
}

function paintStageBands(
  resolved: ResolvedStage[],
  dark: boolean,
): Record<string, unknown> {
  const annotations: Record<string, unknown> = {};
  for (let si = 0; si < resolved.length; si++) {
    const stage = resolved[si]!;
    const paint = STAGE_TONE_COLORS[stage.tone];
    annotations[`stageBand${si}`] = {
      type: "box",
      xMin: stage.startIndex - 0.45,
      xMax: stage.endIndex + 0.45,
      backgroundColor: dark ? paint.bandDark : paint.band,
      borderWidth: 0,
      drawTime: "beforeDatasetsDraw",
    };
  }
  return annotations;
}

function paintExtremeLabels(
  extremes: Array<{ index: number; value: number; kind: "high" | "low" }>,
): Record<string, unknown> {
  const annotations: Record<string, unknown> = {};
  for (let ei = 0; ei < extremes.length; ei++) {
    const ex = extremes[ei]!;
    const isHigh = ex.kind === "high";
    annotations[`extreme${ei}`] = {
      type: "label",
      xValue: ex.index,
      yValue: ex.value,
      yAdjust: isHigh ? -10 : 10,
      content: formatChartPrice(ex.value),
      color: isHigh ? STAGE_TONE_COLORS.up.text : STAGE_TONE_COLORS.down.text,
      font: { size: 11, weight: "600" },
      textAlign: "center",
      drawTime: "afterDatasetsDraw",
      clip: false,
    };
  }
  return annotations;
}

/**
 * Build chartjs-plugin-annotation config from stages + OHLC.
 * Bands + extreme labels only — no directional arrows; stage reasons via axis hover panel.
 * Deterministic — never forwards model-supplied Chart.js options.
 */
export function buildStageAnnotations(
  labels: string[],
  ohlc: ChartOhlcBar[],
  stages: ChartStage[] | undefined,
  dark: boolean,
): Record<string, unknown> {
  const resolved = resolveChartStages(labels, stages);
  if (!resolved.length || !ohlc.length) return {};

  const annotations = paintStageBands(resolved, dark);

  type Extreme = { index: number; value: number; kind: "high" | "low" };
  const extremes: Extreme[] = [];
  const seen = new Set<string>();
  const pushExtreme = (kind: "high" | "low", ex: { index: number; value: number } | null) => {
    if (!ex) return;
    const key = `${kind}:${ex.index}`;
    if (seen.has(key)) return;
    if (extremes.length >= MAX_EXTREME_LABELS) return;
    seen.add(key);
    extremes.push({ ...ex, kind });
  };

  pushExtreme("high", extremumInRange(ohlc, 0, ohlc.length - 1, "high"));
  pushExtreme("low", extremumInRange(ohlc, 0, ohlc.length - 1, "low"));
  for (const stage of resolved) {
    if (stage.tone === "up") {
      pushExtreme("high", extremumInRange(ohlc, stage.startIndex, stage.endIndex, "high"));
    } else if (stage.tone === "down") {
      pushExtreme("low", extremumInRange(ohlc, stage.startIndex, stage.endIndex, "low"));
    }
  }

  return { ...annotations, ...paintExtremeLabels(extremes) };
}

/**
 * Stage bands + extremes for line/area using the first series' numeric values.
 */
export function buildSeriesStageAnnotations(
  labels: string[],
  values: Array<number | null>,
  stages: ChartStage[] | undefined,
  dark: boolean,
): Record<string, unknown> {
  const resolved = resolveChartStages(labels, stages);
  if (!resolved.length || !values.length) return {};

  const annotations = paintStageBands(resolved, dark);

  type Extreme = { index: number; value: number; kind: "high" | "low" };
  const extremes: Extreme[] = [];
  const seen = new Set<string>();
  const pushExtreme = (kind: "high" | "low", ex: { index: number; value: number } | null) => {
    if (!ex) return;
    const key = `${kind}:${ex.index}`;
    if (seen.has(key)) return;
    if (extremes.length >= MAX_EXTREME_LABELS) return;
    seen.add(key);
    extremes.push({ ...ex, kind });
  };

  pushExtreme("high", extremumInSeriesRange(values, 0, values.length - 1, "high"));
  pushExtreme("low", extremumInSeriesRange(values, 0, values.length - 1, "low"));
  for (const stage of resolved) {
    if (stage.tone === "up") {
      pushExtreme("high", extremumInSeriesRange(values, stage.startIndex, stage.endIndex, "high"));
    } else if (stage.tone === "down") {
      pushExtreme("low", extremumInSeriesRange(values, stage.startIndex, stage.endIndex, "low"));
    }
  }

  return { ...annotations, ...paintExtremeLabels(extremes) };
}

type ChartWithHover = Chart & { $hoverIndex?: number | null };

/** Category charts that share left-rail + crosshair + click-pin (not scatter). */
export function isAxisChartType(type: ChartSpec["type"]): boolean {
  return type === "candlestick" || type === "line" || type === "area" || type === "bar";
}

/**
 * Dashed crosshair: vertical @ index; horizontal only for single-series
 * (candlestick close, or lone line/area/bar value).
 */
export const axisCrosshairPlugin = {
  id: "axisCrosshair",
  afterDraw(chart: Chart) {
    const hoverIndex = (chart as ChartWithHover).$hoverIndex;
    if (hoverIndex == null || !Number.isFinite(hoverIndex)) return;
    const index = Math.round(hoverIndex);
    const area = chart.chartArea;
    if (!area) return;
    const meta0 = chart.getDatasetMeta(0);
    const el0 = meta0?.data?.[index];
    if (!el0) return;
    const x = el0.x;
    if (!Number.isFinite(x)) return;

    const datasets = chart.data.datasets ?? [];
    const yScale = chart.scales.y;
    let y: number | undefined;
    const drawHorizontal = datasets.length === 1;
    if (drawHorizontal && yScale) {
      const raw = datasets[0]?.data?.[index] as
        | number
        | { c?: number; y?: number }
        | null
        | undefined;
      let value: number | undefined;
      if (typeof raw === "number" && Number.isFinite(raw)) {
        value = raw;
      } else if (raw && typeof raw === "object") {
        if (typeof raw.c === "number" && Number.isFinite(raw.c)) value = raw.c;
        else if (typeof raw.y === "number" && Number.isFinite(raw.y)) value = raw.y;
      }
      if (value != null) {
        y = yScale.getPixelForValue(value);
      } else if (Number.isFinite(el0.y)) {
        y = el0.y;
      }
    }

    const ctx = chart.ctx;
    const stroke = isDarkTheme() ? "rgba(255,255,255,0.35)" : "rgba(0,0,0,0.28)";
    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, area.top);
    ctx.lineTo(x, area.bottom);
    ctx.stroke();
    if (y != null && Number.isFinite(y)) {
      ctx.beginPath();
      ctx.moveTo(area.left, y);
      ctx.lineTo(area.right, y);
      ctx.stroke();
    }
    ctx.restore();
  },
};

/** @deprecated alias — use axisCrosshairPlugin */
export const candleCrosshairPlugin = axisCrosshairPlugin;

/** Latest-biased X window for candlestick (full range when N ≤ window). */
export function defaultCandleXWindow(
  barCount: number,
  windowSize: number = DEFAULT_CANDLE_WINDOW,
): { min: number; max: number } {
  if (barCount <= 0) return { min: 0, max: 0 };
  const max = barCount - 1;
  const min = Math.max(0, barCount - windowSize);
  return { min, max };
}

/** Y range from OHLC highs/lows inside [xMin, xMax], with padding. */
export function yRangeForVisibleBars(
  ohlc: ChartOhlcBar[],
  xMin: number,
  xMax: number,
  padRatio = 0.08,
): { min: number; max: number } | null {
  if (!ohlc.length) return null;
  const lo = Math.max(0, Math.floor(Math.min(xMin, xMax)));
  const hi = Math.min(ohlc.length - 1, Math.ceil(Math.max(xMin, xMax)));
  let yMin = Infinity;
  let yMax = -Infinity;
  for (let i = lo; i <= hi; i++) {
    const bar = ohlc[i];
    if (!bar) continue;
    if (bar.l < yMin) yMin = bar.l;
    if (bar.h > yMax) yMax = bar.h;
  }
  if (!Number.isFinite(yMin) || !Number.isFinite(yMax)) return null;
  const span = Math.max(yMax - yMin, Math.abs(yMax) * 0.01, 1e-6);
  const pad = span * padRatio;
  return { min: yMin - pad, max: yMax + pad };
}

/** Refit Y scale to bars currently visible on X (after zoom/pan). */
export function fitYToVisibleBars(chart: Chart, ohlc: ChartOhlcBar[]): void {
  const xScale = chart.scales.x;
  const yScale = chart.scales.y;
  if (!xScale || !yScale) return;
  const range = yRangeForVisibleBars(ohlc, xScale.min, xScale.max);
  if (!range) return;
  yScale.options.min = range.min;
  yScale.options.max = range.max;
  chart.update("none");
}

export type ChartJsConfigOpts = {
  candleWindow?: number;
  axisPanelRail?: number;
};

/** Build Chart.js config from a validated ChartSpec (never from raw model options). */
export function chartJsConfigFromSpec(
  spec: ChartSpec,
  _ui: ChartTooltipUi = DEFAULT_OHLC_UI,
  opts: ChartJsConfigOpts = {},
): ChartConfiguration {
  const colors = themeColors();
  const dark = isDarkTheme();
  const yTitle = spec.yTitle || (spec.unit ? spec.unit : undefined);

  if (spec.type === "candlestick") {
    const bars = spec.ohlc ?? [];
    const stageAnnotations = buildStageAnnotations(spec.labels, bars, spec.stages, dark);
    const candleWindow = opts.candleWindow ?? DEFAULT_CANDLE_WINDOW;
    const axisRail = opts.axisPanelRail ?? AXIS_PANEL_RAIL;
    const xWindow = defaultCandleXWindow(bars.length, candleWindow);
    const yWindow = yRangeForVisibleBars(bars, xWindow.min, xWindow.max);
    const xLimitMax = Math.max(0, bars.length - 1);

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
      plugins: [axisCrosshairPlugin],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { left: axisRail, top: 18, bottom: 8 } },
        interaction: { mode: "index", intersect: false },
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
            enabled: false,
          },
          zoom: {
            limits: {
              x: { min: 0, max: xLimitMax, minRange: Math.min(5, Math.max(1, bars.length)) },
            },
            pan: {
              enabled: true,
              mode: "x",
              onPanComplete({ chart }: { chart: Chart }) {
                fitYToVisibleBars(chart, bars);
              },
            },
            zoom: {
              wheel: { enabled: true },
              pinch: { enabled: true },
              mode: "x",
              onZoomComplete({ chart }: { chart: Chart }) {
                fitYToVisibleBars(chart, bars);
              },
            },
          },
          ...(Object.keys(stageAnnotations).length > 0
            ? { annotation: { annotations: stageAnnotations } }
            : {}),
        },
        scales: {
          x: {
            type: "linear",
            offset: false,
            min: xWindow.min,
            max: xWindow.max,
            bounds: "ticks",
            title: spec.xTitle
              ? { display: true, text: spec.xTitle, color: colors.muted }
              : undefined,
            ticks: {
              color: colors.muted,
              autoSkip: true,
              maxTicksLimit: 8,
              callback(value: string | number) {
                const i = Number(value);
                return Number.isInteger(i) && spec.labels[i] != null ? spec.labels[i] : "";
              },
            },
            grid: { color: colors.grid },
          },
          y: {
            // Fit visible window; ignore full-series yMin/yMax from spec.
            min: yWindow?.min,
            max: yWindow?.max,
            title: yTitle
              ? { display: true, text: yTitle, color: colors.muted }
              : undefined,
            ticks: { color: colors.muted },
            grid: { color: colors.grid },
          },
        },
      },
    } as ChartConfiguration;
  }

  const fill = spec.type === "area";
  const chartType: ChartJsType =
    spec.type === "area" ? "line" : spec.type === "scatter" ? "scatter" : spec.type;
  const axisChart = isAxisChartType(spec.type);
  const axisRail = opts.axisPanelRail ?? AXIS_PANEL_RAIL;

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

  const seriesStageAnnotations =
    (spec.type === "line" || spec.type === "area") && spec.stages?.length
      ? buildSeriesStageAnnotations(
          spec.labels,
          spec.series[0]?.values ?? [],
          spec.stages,
          dark,
        )
      : {};

  return {
    type: chartType,
    data: {
      labels: spec.type === "scatter" ? undefined : spec.labels,
      datasets,
    },
    plugins: axisChart ? [axisCrosshairPlugin] : undefined,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      ...(axisChart
        ? {
            layout: { padding: { left: axisRail, top: 8, bottom: 8 } },
            interaction: { mode: "index" as const, intersect: false },
          }
        : {}),
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
        tooltip: axisChart
          ? { enabled: false }
          : {
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
        ...(Object.keys(seriesStageAnnotations).length > 0
          ? { annotation: { annotations: seriesStageAnnotations } }
          : {}),
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

export type AxisSeriesRow = {
  name: string;
  value: number | null;
  color: string;
};

export type AxisHoverState = {
  index: number;
  label: string;
  kind: "ohlc" | "series";
  ohlc?: ChartOhlcBar;
  seriesRows?: AxisSeriesRow[];
  stage: ResolvedStage | null;
  panelLeft: number;
};

function FullscreenIcon(): JSX.Element {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function HintIconPan(): JSX.Element {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M8 12H4m16 0h-4M12 8V4m0 16v-4"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

function HintIconPin(): JSX.Element {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 17v4M9 3h6l-1 7h3l-5 6-5-6h3L9 3z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function HintIconCrosshair(): JSX.Element {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="7" stroke="currentColor" strokeWidth="2" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function ChartBlock({
  source,
  chartToolResults,
  variant = "inline",
}: {
  source: string;
  chartToolResults?: ChartToolResult[];
  /** lightbox: fill parent portal; hide nested fullscreen button. */
  variant?: "inline" | "lightbox";
}): JSX.Element {
  const { t, locale } = useI18n();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<Chart | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [axisHover, setAxisHover] = useState<AxisHoverState | null>(null);
  const [axisPinned, setAxisPinned] = useState(false);
  const pointerDownRef = useRef<{ x: number; y: number } | null>(null);
  const applyLatestRef = useRef<() => void>(() => {});
  const applyFocusPinnedRef = useRef<() => void>(() => {});

  // Stable signature so parent re-renders with a new array identity do not rebuild Chart.js.
  const toolsSig = (chartToolResults || [])
    .filter((tr) => tr.name === "lookup_yahoo_ohlc" && tr.preview)
    .map((tr) => tr.preview!)
    .join("\0");

  const parsed = useMemo(
    () => resolveChartSource(source, chartToolResults),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- toolsSig stands in for chartToolResults
    [source, toolsSig],
  );

  const isCandlestick = parsed.ok && parsed.spec.type === "candlestick";
  const isAxisChart = parsed.ok && isAxisChartType(parsed.spec.type);

  const resolvedStages = useMemo(() => {
    if (!parsed.ok) return [];
    if (
      parsed.spec.type !== "candlestick" &&
      parsed.spec.type !== "line" &&
      parsed.spec.type !== "area"
    ) {
      return [];
    }
    return resolveChartStages(parsed.spec.labels, parsed.spec.stages);
  }, [parsed]);

  const tooltipUi = useMemo(
    (): ChartTooltipUi => ({
      open: t("chart.ohlc.open"),
      high: t("chart.ohlc.high"),
      low: t("chart.ohlc.low"),
      close: t("chart.ohlc.close"),
    }),
    [t, locale],
  );

  function latestIndex(): number | null {
    if (!parsed.ok || !isAxisChartType(parsed.spec.type)) return null;
    if (parsed.spec.type === "candlestick") {
      const n = parsed.spec.ohlc?.length ?? 0;
      return n > 0 ? n - 1 : null;
    }
    const n = parsed.spec.labels.length;
    return n > 0 ? n - 1 : null;
  }

  function focusOrLatestIndex(): number | null {
    if (!parsed.ok || !isAxisChartType(parsed.spec.type)) return null;
    const focus = parsed.spec.focusLabel?.trim();
    if (focus) {
      const idx = findLabelIndex(parsed.spec.labels, focus);
      if (idx >= 0) return idx;
    }
    return latestIndex();
  }

  function applyAxisAtIndex(index: number, chartArg?: ChartWithHover | null): boolean {
    if (!parsed.ok || !isAxisChartType(parsed.spec.type)) return false;
    const chart = chartArg ?? (chartRef.current as ChartWithHover | null);
    if (!chart) return false;
    const labels = parsed.spec.labels;
    if (index < 0 || index >= labels.length) return false;
    const label = labels[index] != null ? String(labels[index]) : String(index);

    if (parsed.spec.type === "candlestick") {
      const bars = parsed.spec.ohlc ?? [];
      const bar = bars[index];
      if (!bar) return false;
      const stage = findStageAtIndex(resolvedStages, index);
      chart.$hoverIndex = index;
      try {
        chart.draw();
      } catch {
        /* ignore */
      }
      setAxisHover({
        index,
        label,
        kind: "ohlc",
        ohlc: bar,
        stage,
        panelLeft: 4,
      });
      return true;
    }

    const rows: AxisSeriesRow[] = parsed.spec.series.map((s, i) => {
      const paint = seriesPaint(i);
      const raw = s.values[index];
      return {
        name: s.name,
        value: typeof raw === "number" && Number.isFinite(raw) ? raw : null,
        color: paint.border,
      };
    });
    const stage =
      parsed.spec.type === "line" || parsed.spec.type === "area"
        ? findStageAtIndex(resolvedStages, index)
        : null;
    chart.$hoverIndex = index;
    try {
      chart.draw();
    } catch {
      /* ignore */
    }
    setAxisHover({
      index,
      label,
      kind: "series",
      seriesRows: rows,
      stage,
      panelLeft: 4,
    });
    return true;
  }

  function applyLatest() {
    const idx = latestIndex();
    if (idx == null) {
      setAxisHover(null);
      setAxisPinned(false);
      const chart = chartRef.current as ChartWithHover | null;
      if (chart) {
        chart.$hoverIndex = null;
        try {
          chart.draw();
        } catch {
          /* ignore */
        }
      }
      return;
    }
    setAxisPinned(false);
    applyAxisAtIndex(idx);
  }

  function applyFocusOrLatestPinned() {
    const idx = focusOrLatestIndex();
    if (idx == null) {
      setAxisHover(null);
      setAxisPinned(false);
      return;
    }
    if (applyAxisAtIndex(idx)) {
      setAxisPinned(true);
    }
  }

  applyLatestRef.current = applyLatest;
  applyFocusPinnedRef.current = applyFocusOrLatestPinned;

  function indexFromClient(clientX: number, clientY: number): number | null {
    const chart = chartRef.current as ChartWithHover | null;
    const canvas = canvasRef.current;
    if (!chart || !canvas || !parsed.ok) return null;
    const xScale = chart.scales.x;
    if (!xScale) return null;
    const canvasRect = canvas.getBoundingClientRect();
    const px = clientX - canvasRect.left;
    const py = clientY - canvasRect.top;
    const area = chart.chartArea;
    if (area && (px < area.left || px > area.right || py < area.top || py > area.bottom)) {
      return null;
    }
    const dataX = Number(xScale.getValueForPixel(px));
    if (!Number.isFinite(dataX)) return null;
    const index = Math.round(dataX);
    const max = Math.max(0, parsed.spec.labels.length - 1);
    if (index < 0 || index > max) return null;
    return index;
  }

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
      setAxisHover(null);
      setAxisPinned(false);
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;

    releaseCanvas(canvas);
    setAxisHover(null);
    setAxisPinned(false);

    const isCandle = parsed.spec.type === "candlestick";
    const axisChart = isAxisChartType(parsed.spec.type);
    const configOpts: ChartJsConfigOpts =
      variant === "lightbox" && axisChart
        ? {
            ...(isCandle ? { candleWindow: LIGHTBOX_CANDLE_WINDOW } : {}),
            axisPanelRail: AXIS_PANEL_RAIL_LIGHTBOX,
          }
        : {};

    try {
      const chart = new Chart(canvas, chartJsConfigFromSpec(parsed.spec, tooltipUi, configOpts));
      chartRef.current = chart;
      setError(null);
      // Default left rail to focusLabel (or latest), pinned.
      if (axisChart) {
        requestAnimationFrame(() => {
          applyFocusPinnedRef.current();
        });
      }
    } catch (err) {
      releaseCanvas(canvas);
      setError(err instanceof Error ? err.message : String(err || ""));
    }

    return () => {
      releaseCanvas(canvasRef.current);
    };
  }, [source, parsed, tooltipUi, variant]);

  // Non-passive wheel so zoom does not scroll the chat transcript.
  useEffect(() => {
    const el = wrapRef.current;
    if (!el || !isCandlestick) return;
    const onWheel = (e: WheelEvent) => {
      const target = e.target as HTMLElement | null;
      if (target?.closest?.(".chart-axis-panel")) return;
      e.preventDefault();
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [isCandlestick, parsed.ok, error]);

  useEffect(() => {
    if (!isAxisChart || !axisPinned) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        applyLatestRef.current();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isAxisChart, axisPinned]);

  function handleAxisMouseMove(e: ReactMouseEvent<HTMLDivElement>) {
    const chart = chartRef.current as ChartWithHover | null;
    if (!chart || !parsed.ok || !isAxisChartType(parsed.spec.type)) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;

    const canvasRect = canvas.getBoundingClientRect();
    const px = e.clientX - canvasRect.left;
    const py = e.clientY - canvasRect.top;
    const area = chart.chartArea;

    // Pinned: keep panel + crosshair on pinned bar; allow moving to rail / anywhere in wrap.
    if (axisPinned && axisHover) {
      chart.$hoverIndex = axisHover.index;
      return;
    }

    if (area && (px < area.left || px > area.right || py < area.top || py > area.bottom)) {
      applyLatest();
      return;
    }

    const index = indexFromClient(e.clientX, e.clientY);
    if (index == null) {
      applyLatest();
      return;
    }
    applyAxisAtIndex(index, chart);
  }

  function handleAxisPointerDown(e: ReactMouseEvent<HTMLDivElement>) {
    if (e.button !== 0) return;
    pointerDownRef.current = { x: e.clientX, y: e.clientY };
  }

  function handleAxisClick(e: ReactMouseEvent<HTMLDivElement>) {
    if ((e.target as HTMLElement | null)?.closest?.(".chart-axis-panel")) return;
    const down = pointerDownRef.current;
    pointerDownRef.current = null;
    if (down && (Math.abs(e.clientX - down.x) > 6 || Math.abs(e.clientY - down.y) > 6)) {
      return; // pan / drag, not a click
    }
    const chart = chartRef.current as ChartWithHover | null;
    if (!chart) return;
    const index = indexFromClient(e.clientX, e.clientY);
    if (index == null) return;
    if (applyAxisAtIndex(index, chart)) {
      setAxisPinned(true);
    }
  }

  function handleWrapMouseLeave() {
    applyLatest();
  }

  const showChart = parsed.ok && !error;
  const showSource = !!error || !parsed.ok;
  const toneLabel =
    axisHover?.stage &&
    (axisHover.stage.tone === "up"
      ? t("chart.stage.tone.up")
      : axisHover.stage.tone === "down"
        ? t("chart.stage.tone.down")
        : t("chart.stage.tone.side"));
  const barUp =
    axisHover?.kind === "ohlc" && axisHover.ohlc
      ? axisHover.ohlc.c >= axisHover.ohlc.o
      : false;
  const upColor = CN_CANDLE_COLORS.border.up;
  const downColor = CN_CANDLE_COLORS.border.down;
  const openCloseColor = barUp ? upColor : downColor;
  const unitSuffix = parsed.ok && parsed.spec.unit ? ` ${parsed.spec.unit}` : "";

  return (
    <div
      className={`chart-block${error || !parsed.ok ? " is-error" : " chart-block--blend"}${variant === "lightbox" ? " chart-block--lightbox" : ""}`}
      data-testid="chart-block"
    >
      {(error || !parsed.ok) && (
        <div className="chart-block-error" data-testid="chart-error">
          {(!parsed.ok ? parsed.error : error) || t("chart.renderError")}
        </div>
      )}
      {showChart && isAxisChart && (
        <div
          className="chart-hint-row"
          data-testid="chart-hint-row"
          data-reveal={variant === "lightbox" ? "always" : "hover"}
          data-slot="top"
        >
          {isCandlestick ? (
            <>
              <span className="chart-hint-chip">
                <HintIconPan />
                <span>{t("chart.candle.hint")}</span>
              </span>
              <span className="chart-hint-chip">
                <HintIconPin />
                <span>{t("chart.candle.pinHint")}</span>
              </span>
            </>
          ) : (
            <>
              <span className="chart-hint-chip">
                <HintIconCrosshair />
                <span>{t("chart.series.hint")}</span>
              </span>
              <span className="chart-hint-chip">
                <HintIconPin />
                <span>{t("chart.series.pinHint")}</span>
              </span>
            </>
          )}
        </div>
      )}
      <div
        ref={wrapRef}
        className={`chart-block-canvas-wrap${isCandlestick ? " chart-block-canvas-wrap--candle" : ""}${isAxisChart && !isCandlestick ? " chart-block-canvas-wrap--axis" : ""}`}
        data-testid="chart-canvas-wrap"
        hidden={!showChart}
        onMouseMove={isAxisChart ? handleAxisMouseMove : undefined}
        onMouseLeave={isAxisChart ? handleWrapMouseLeave : undefined}
        onMouseDown={isAxisChart ? handleAxisPointerDown : undefined}
        onClick={isAxisChart ? handleAxisClick : undefined}
      >
        {variant === "inline" && showChart && (
          <button
            type="button"
            className="chart-fullscreen-btn"
            disabled={!parsed.ok || !!error}
            onClick={() => setLightboxOpen(true)}
            data-testid="chart-fullscreen"
            aria-label={t("chart.fullscreen")}
            title={t("chart.fullscreen")}
          >
            <FullscreenIcon />
          </button>
        )}
        <canvas ref={canvasRef} data-testid="chart-canvas" />
        {axisHover && (
          <div
            className={`chart-axis-panel${axisPinned ? " chart-axis-panel--pinned" : ""} chart-axis-panel--center`}
            data-testid="chart-axis-panel"
            data-pinned={axisPinned ? "true" : "false"}
            data-centered="true"
            data-tone={axisHover.stage?.tone ?? undefined}
            role="status"
            style={{ left: axisHover.panelLeft }}
            onWheel={(ev) => {
              ev.stopPropagation();
            }}
          >
            <div className="chart-axis-panel-date" data-testid="chart-axis-panel-date">
              {axisHover.label}
            </div>
            {axisHover.kind === "ohlc" && axisHover.ohlc && (
              <div className="chart-axis-panel-ohlc" data-testid="chart-axis-panel-ohlc">
                <div className="chart-axis-panel-kv chart-axis-panel-kv--row">
                  <span className="chart-axis-panel-k">{t("chart.ohlc.open")}</span>
                  <span className="chart-axis-panel-v" style={{ color: openCloseColor }}>
                    {formatChartPrice(axisHover.ohlc.o)}
                  </span>
                </div>
                <div className="chart-axis-panel-kv chart-axis-panel-kv--row">
                  <span className="chart-axis-panel-k">{t("chart.ohlc.high")}</span>
                  <span className="chart-axis-panel-v" style={{ color: upColor }}>
                    {formatChartPrice(axisHover.ohlc.h)}
                  </span>
                </div>
                <div className="chart-axis-panel-kv chart-axis-panel-kv--row">
                  <span className="chart-axis-panel-k">{t("chart.ohlc.low")}</span>
                  <span className="chart-axis-panel-v" style={{ color: downColor }}>
                    {formatChartPrice(axisHover.ohlc.l)}
                  </span>
                </div>
                <div className="chart-axis-panel-kv chart-axis-panel-kv--row">
                  <span className="chart-axis-panel-k">{t("chart.ohlc.close")}</span>
                  <span className="chart-axis-panel-v" style={{ color: openCloseColor }}>
                    {formatChartPrice(axisHover.ohlc.c)}
                  </span>
                </div>
              </div>
            )}
            {axisHover.kind === "series" && axisHover.seriesRows && (
              <div className="chart-axis-panel-ohlc" data-testid="chart-axis-panel-series">
                {axisHover.seriesRows.map((row) => (
                  <div className="chart-axis-panel-kv chart-axis-panel-kv--stack" key={row.name}>
                    <span className="chart-axis-panel-k" style={{ color: row.color }}>
                      {row.name}
                    </span>
                    <span className="chart-axis-panel-v">
                      {formatChartPrice(row.value)}
                      {unitSuffix}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {axisHover.stage && (
              <div className="chart-axis-panel-stage" data-testid="chart-axis-panel-stage">
                <div className="chart-axis-panel-head">
                  <span
                    className="chart-axis-panel-tone"
                    data-tone={axisHover.stage.tone}
                    data-testid="chart-axis-panel-tone"
                    aria-hidden
                  />
                  {toneLabel ? (
                    <span className="chart-axis-panel-tone-text">{toneLabel}</span>
                  ) : null}
                </div>
                <div className="chart-axis-panel-row">
                  <span className="chart-axis-panel-label">{t("chart.stage.interval")}</span>
                  <span className="chart-axis-panel-value">
                    {axisHover.stage.start} – {axisHover.stage.end}
                  </span>
                </div>
                <div className="chart-axis-panel-row">
                  <span className="chart-axis-panel-label">{t("chart.stage.drivers")}</span>
                  <span className="chart-axis-panel-value chart-axis-panel-reason">
                    {axisHover.stage.reason}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      {showSource && (
        <pre className="chart-block-source" data-testid="chart-source">
          {source}
        </pre>
      )}
      {lightboxOpen && variant === "inline" && (
        <ChartLightbox onClose={() => setLightboxOpen(false)}>
          <ChartBlock
            source={source}
            chartToolResults={chartToolResults}
            variant="lightbox"
          />
        </ChartLightbox>
      )}
    </div>
  );
}
