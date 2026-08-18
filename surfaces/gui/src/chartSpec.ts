/** Controlled ChartSpec v1 — data only; never execute model-supplied Chart.js options. */

export type ChartType = "line" | "bar" | "area" | "scatter" | "candlestick";

export type ChartSeries = {
  name: string;
  values: Array<number | null>;
};

export type ChartOhlcBar = {
  o: number;
  h: number;
  l: number;
  c: number;
};

/** Trend stage for candlestick annotations (model-authored; UI paints bands/arrows). */
export type ChartStageTone = "up" | "down" | "side";

export type ChartStage = {
  /** Match against labels (exact, then suffix/prefix soft match). */
  start: string;
  end: string;
  tone: ChartStageTone;
  /** Short reason (1–3 lines); truncated at parse. */
  reason: string;
};

export type ChartSpec = {
  version: 1;
  type: ChartType;
  title?: string;
  subtitle?: string;
  unit?: string;
  labels: string[];
  /** Scalar series for line/bar/area/scatter. Empty for candlestick. */
  series: ChartSeries[];
  /** Single-instrument OHLC aligned with labels (candlestick only). */
  ohlc?: ChartOhlcBar[];
  /** Stage bands for candlestick and line/area trend charts. */
  stages?: ChartStage[];
  /** Pin crosshair/panel to this label on mount (exact/soft match via findLabelIndex). */
  focusLabel?: string;
  xTitle?: string;
  yTitle?: string;
  yMin?: number;
  yMax?: number;
  showLegend?: boolean;
};

export const MAX_CHART_STAGES = 8;
export const MAX_STAGE_REASON_LEN = 160;
const STAGE_TONES = new Set<ChartStageTone>(["up", "down", "side"]);

export type ParseChartSpecResult =
  | { ok: true; spec: ChartSpec }
  | { ok: false; error: string };

/** Tool row preview used to resolve Yahoo short-ref charts. */
export type ChartToolResult = {
  name: string;
  preview?: string;
};

const CHART_TYPES = new Set<ChartType>(["line", "bar", "area", "scatter", "candlestick"]);

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function optionalString(value: unknown, field: string): string | undefined | { error: string } {
  if (value === undefined) return undefined;
  if (typeof value !== "string") return { error: `${field} must be a string` };
  return value;
}

function optionalNumber(value: unknown, field: string): number | undefined | { error: string } {
  if (value === undefined) return undefined;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return { error: `${field} must be a finite number` };
  }
  return value;
}

function optionalBoolean(value: unknown, field: string): boolean | undefined | { error: string } {
  if (value === undefined) return undefined;
  if (typeof value !== "boolean") return { error: `${field} must be a boolean` };
  return value;
}

function parseSeries(raw: unknown, labelsLen: number, index: number): ChartSeries | { error: string } {
  if (!isPlainObject(raw)) return { error: `series[${index}] must be an object` };
  if (typeof raw.name !== "string" || !raw.name.trim()) {
    return { error: `series[${index}].name must be a non-empty string` };
  }
  if (!Array.isArray(raw.values)) {
    return { error: `series[${index}].values must be an array` };
  }
  if (raw.values.length !== labelsLen) {
    return {
      error: `series[${index}].values length (${raw.values.length}) must match labels length (${labelsLen})`,
    };
  }
  const values: Array<number | null> = [];
  for (let i = 0; i < raw.values.length; i++) {
    const v = raw.values[i];
    if (v === null) {
      values.push(null);
      continue;
    }
    if (typeof v !== "number" || !Number.isFinite(v)) {
      return { error: `series[${index}].values[${i}] must be a number or null` };
    }
    values.push(v);
  }
  return { name: raw.name, values };
}

function parseOhlcBar(raw: unknown, index: number): ChartOhlcBar | { error: string } {
  // LLM hand-copy often emits [o, h, l, c] tuples instead of objects.
  if (Array.isArray(raw)) {
    if (raw.length !== 4) {
      return { error: `ohlc[${index}] must be [o,h,l,c] or {o,h,l,c}` };
    }
    const [o, h, l, c] = raw;
    for (const [key, val] of [
      ["o", o],
      ["h", h],
      ["l", l],
      ["c", c],
    ] as const) {
      if (typeof val !== "number" || !Number.isFinite(val)) {
        return { error: `ohlc[${index}].${key} must be a finite number` };
      }
    }
    return { o: o as number, h: h as number, l: l as number, c: c as number };
  }
  if (!isPlainObject(raw)) {
    return { error: `ohlc[${index}] must be [o,h,l,c] or {o,h,l,c}` };
  }
  const o = raw.o ?? raw.open;
  const h = raw.h ?? raw.high;
  const l = raw.l ?? raw.low;
  const c = raw.c ?? raw.close;
  for (const [key, val] of [
    ["o", o],
    ["h", h],
    ["l", l],
    ["c", c],
  ] as const) {
    if (typeof val !== "number" || !Number.isFinite(val)) {
      return { error: `ohlc[${index}].${key} must be a finite number` };
    }
  }
  return { o: o as number, h: h as number, l: l as number, c: c as number };
}

/** Resolve a stage boundary string against chart labels. */
export function findLabelIndex(labels: string[], needle: string): number {
  const n = needle.trim();
  if (!n) return -1;
  const exact = labels.findIndex((l) => l === n);
  if (exact >= 0) return exact;
  const soft = labels.findIndex((l) => l.endsWith(n) || n.endsWith(l));
  if (soft >= 0) return soft;
  return labels.findIndex((l) => l.includes(n) || n.includes(l));
}

/**
 * Parse optional stages array. Invalid entries are dropped (not fatal).
 * Used for candlestick and line/area trend charts.
 */
export function parseStages(raw: unknown): ChartStage[] | undefined {
  if (raw === undefined) return undefined;
  if (!Array.isArray(raw)) return undefined;
  const stages: ChartStage[] = [];
  for (let i = 0; i < raw.length && stages.length < MAX_CHART_STAGES; i++) {
    const item = raw[i];
    if (!isPlainObject(item)) continue;
    if (typeof item.start !== "string" || !item.start.trim()) continue;
    if (typeof item.end !== "string" || !item.end.trim()) continue;
    if (typeof item.tone !== "string" || !STAGE_TONES.has(item.tone as ChartStageTone)) continue;
    if (typeof item.reason !== "string") continue;
    const reason = item.reason.trim().slice(0, MAX_STAGE_REASON_LEN);
    if (!reason) continue;
    stages.push({
      start: item.start.trim(),
      end: item.end.trim(),
      tone: item.tone as ChartStageTone,
      reason,
    });
  }
  return stages.length > 0 ? stages : undefined;
}

/** Prefer top-level `labels`; fall back to nested `x.labels` (common LLM drift). */
function resolveLabelsRaw(parsed: Record<string, unknown>): unknown {
  if (Array.isArray(parsed.labels)) return parsed.labels;
  if (isPlainObject(parsed.x) && Array.isArray(parsed.x.labels)) return parsed.x.labels;
  return parsed.labels;
}

/** Nested `x.title` / string `x.label` when flat xTitle aliases are absent. */
function resolveXTitleRaw(parsed: Record<string, unknown>): unknown {
  const flat = parsed.xTitle ?? parsed.xLabel ?? parsed.x_label;
  if (flat !== undefined) return flat;
  if (!isPlainObject(parsed.x)) return undefined;
  if (typeof parsed.x.title === "string") return parsed.x.title;
  if (typeof parsed.x.label === "string") return parsed.x.label;
  return undefined;
}

function parseCommonMeta(parsed: Record<string, unknown>): {
  ok: true;
  meta: Pick<
    ChartSpec,
    "title" | "subtitle" | "unit" | "xTitle" | "yTitle" | "yMin" | "yMax" | "showLegend" | "focusLabel"
  >;
} | { ok: false; error: string } {
  const title = optionalString(parsed.title, "title");
  if (title && typeof title === "object") return { ok: false, error: title.error };
  const subtitle = optionalString(parsed.subtitle, "subtitle");
  if (subtitle && typeof subtitle === "object") return { ok: false, error: subtitle.error };
  const unit = optionalString(parsed.unit, "unit");
  if (unit && typeof unit === "object") return { ok: false, error: unit.error };
  const focusLabel = optionalString(parsed.focusLabel ?? parsed.focus_label, "focusLabel");
  if (focusLabel && typeof focusLabel === "object") return { ok: false, error: focusLabel.error };
  const xTitleRaw = resolveXTitleRaw(parsed);
  const yTitleRaw = parsed.yTitle ?? parsed.yLabel ?? parsed.y_label;
  const xTitle = optionalString(xTitleRaw, "xTitle");
  if (xTitle && typeof xTitle === "object") return { ok: false, error: xTitle.error };
  const yTitle = optionalString(yTitleRaw, "yTitle");
  if (yTitle && typeof yTitle === "object") return { ok: false, error: yTitle.error };
  const yMin = optionalNumber(parsed.yMin, "yMin");
  if (yMin && typeof yMin === "object") return { ok: false, error: yMin.error };
  const yMax = optionalNumber(parsed.yMax, "yMax");
  if (yMax && typeof yMax === "object") return { ok: false, error: yMax.error };
  const showLegend = optionalBoolean(parsed.showLegend, "showLegend");
  if (showLegend && typeof showLegend === "object") return { ok: false, error: showLegend.error };

  const meta: Pick<
    ChartSpec,
    "title" | "subtitle" | "unit" | "xTitle" | "yTitle" | "yMin" | "yMax" | "showLegend" | "focusLabel"
  > = {};
  if (typeof title === "string") meta.title = title;
  if (typeof subtitle === "string") meta.subtitle = subtitle;
  if (typeof unit === "string") meta.unit = unit;
  if (typeof focusLabel === "string" && focusLabel.trim()) meta.focusLabel = focusLabel.trim();
  if (typeof xTitle === "string") meta.xTitle = xTitle;
  if (typeof yTitle === "string") meta.yTitle = yTitle;
  if (typeof yMin === "number") meta.yMin = yMin;
  if (typeof yMax === "number") meta.yMax = yMax;
  if (typeof showLegend === "boolean") meta.showLegend = showLegend;
  return { ok: true, meta };
}

function parseLabels(labelsRaw: unknown): string[] | { error: string } {
  if (!Array.isArray(labelsRaw)) {
    return { error: "labels must be an array" };
  }
  if (labelsRaw.length === 0) {
    return { error: "labels must not be empty" };
  }
  const labels: string[] = [];
  for (let i = 0; i < labelsRaw.length; i++) {
    const label = labelsRaw[i];
    if (typeof label !== "string") {
      return { error: `labels[${i}] must be a string` };
    }
    labels.push(label);
  }
  return labels;
}

/** True when fence is a Yahoo short-ref (no OHLC hand-copy). */
export function isYahooChartRef(parsed: Record<string, unknown>): boolean {
  const fromTool = typeof parsed.from_tool === "string" ? parsed.from_tool.trim() : "";
  const symbol = typeof parsed.symbol === "string" ? parsed.symbol.trim() : "";
  return fromTool === "lookup_yahoo_ohlc" && !!symbol;
}

function findYahooChartSpecJson(
  toolResults: ChartToolResult[] | undefined,
  symbol: string,
): string | { error: string } {
  const want = symbol.trim().toUpperCase();
  const candidates = (toolResults || []).filter((t) => t.name === "lookup_yahoo_ohlc" && t.preview);
  for (let i = candidates.length - 1; i >= 0; i--) {
    const preview = candidates[i]!.preview!;
    let payload: unknown;
    try {
      payload = JSON.parse(preview);
    } catch {
      continue;
    }
    if (!isPlainObject(payload)) continue;
    if (payload.status !== "ok") continue;
    const sym = typeof payload.symbol === "string" ? payload.symbol.trim().toUpperCase() : "";
    if (sym !== want) continue;
    if (!isPlainObject(payload.chart_spec)) {
      return { error: `Yahoo OHLC for ${symbol} has no chart_spec` };
    }
    return JSON.stringify(payload.chart_spec);
  }
  return { error: `no Yahoo OHLC for symbol ${symbol}` };
}

/**
 * Resolve a fenced ```chart body: Yahoo short-ref → tool chart_spec; otherwise parseChartSpec.
 * Optional title on the ref overrides the tool chart_spec title.
 */
export function resolveChartSource(
  source: string,
  toolResults?: ChartToolResult[],
): ParseChartSpecResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(source);
  } catch {
    return { ok: false, error: "Invalid JSON: chart source is not valid JSON" };
  }
  if (!isPlainObject(parsed)) {
    return { ok: false, error: "Chart spec must be a JSON object" };
  }

  if (isYahooChartRef(parsed)) {
    const symbol = String(parsed.symbol).trim();
    const found = findYahooChartSpecJson(toolResults, symbol);
    if (typeof found !== "string") return { ok: false, error: found.error };
    const resolved = parseChartSpec(found);
    if (!resolved.ok) return resolved;
    const stages = parseStages(parsed.stages);
    const next: ChartSpec = { ...resolved.spec };
    if (typeof parsed.title === "string" && parsed.title.trim()) {
      next.title = parsed.title;
    }
    if (stages) next.stages = stages;
    return { ok: true, spec: next };
  }

  return parseChartSpec(source);
}

/** Parse and validate a fenced ```chart JSON body into ChartSpec v1. */
export function parseChartSpec(source: string): ParseChartSpecResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(source);
  } catch {
    return { ok: false, error: "Invalid JSON: chart source is not valid JSON" };
  }

  if (!isPlainObject(parsed)) {
    return { ok: false, error: "Chart spec must be a JSON object" };
  }

  // Missing version is treated as 1 (common LLM omission); explicit non-1 still fails.
  if (parsed.version !== undefined && parsed.version !== 1) {
    return { ok: false, error: "version must be 1" };
  }

  if (typeof parsed.type !== "string" || !CHART_TYPES.has(parsed.type as ChartType)) {
    return { ok: false, error: "type must be one of: line, bar, area, scatter, candlestick" };
  }

  // Short-ref without tool context cannot be fully parsed here.
  if (isYahooChartRef(parsed)) {
    return {
      ok: false,
      error: `candlestick short-ref requires tool resolve for symbol ${String(parsed.symbol).trim()}`,
    };
  }

  const labelsResult = parseLabels(resolveLabelsRaw(parsed));
  if ("error" in labelsResult) return { ok: false, error: labelsResult.error };
  let labels = labelsResult;

  const metaResult = parseCommonMeta(parsed);
  if (!metaResult.ok) return metaResult;

  const chartType = parsed.type as ChartType;

  if (chartType === "candlestick") {
    if (!Array.isArray(parsed.ohlc) || parsed.ohlc.length === 0) {
      return { ok: false, error: "candlestick requires a non-empty ohlc array" };
    }
    // LLM hand-copy often truncates one array; keep aligned prefix.
    const n = Math.min(parsed.ohlc.length, labels.length);
    if (n < 1) {
      return { ok: false, error: "candlestick requires aligned labels and ohlc" };
    }
    labels = labels.slice(0, n);
    const ohlcRaw = parsed.ohlc.slice(0, n);
    const ohlc: ChartOhlcBar[] = [];
    for (let i = 0; i < ohlcRaw.length; i++) {
      const bar = parseOhlcBar(ohlcRaw[i], i);
      if ("error" in bar) return { ok: false, error: bar.error };
      ohlc.push(bar);
    }
    const stages = parseStages(parsed.stages);
    const spec: ChartSpec = {
      version: 1,
      type: "candlestick",
      labels,
      series: [],
      ohlc,
      ...metaResult.meta,
    };
    if (stages) spec.stages = stages;
    return { ok: true, spec };
  }

  if (!Array.isArray(parsed.series) || parsed.series.length === 0) {
    return { ok: false, error: "series must be a non-empty array" };
  }

  const series: ChartSeries[] = [];
  for (let i = 0; i < parsed.series.length; i++) {
    const item = parseSeries(parsed.series[i], labels.length, i);
    if ("error" in item) return { ok: false, error: item.error };
    series.push(item);
  }

  // Strip unknown keys (e.g. options / plugins) — never forward to Chart.js.
  const stages =
    chartType === "line" || chartType === "area" ? parseStages(parsed.stages) : undefined;
  const spec: ChartSpec = {
    version: 1,
    type: chartType,
    labels,
    series,
    ...metaResult.meta,
  };
  if (stages) spec.stages = stages;

  return { ok: true, spec };
}
