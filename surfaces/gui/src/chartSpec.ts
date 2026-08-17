/** Controlled ChartSpec v1 — data only; never execute model-supplied Chart.js options. */

export type ChartType = "line" | "bar" | "area" | "scatter";

export type ChartSeries = {
  name: string;
  values: Array<number | null>;
};

export type ChartSpec = {
  version: 1;
  type: ChartType;
  title?: string;
  subtitle?: string;
  unit?: string;
  labels: string[];
  series: ChartSeries[];
  xTitle?: string;
  yTitle?: string;
  yMin?: number;
  yMax?: number;
  showLegend?: boolean;
};

export type ParseChartSpecResult =
  | { ok: true; spec: ChartSpec }
  | { ok: false; error: string };

const CHART_TYPES = new Set<ChartType>(["line", "bar", "area", "scatter"]);

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

  if (parsed.version !== 1) {
    return { ok: false, error: "version must be 1" };
  }

  if (typeof parsed.type !== "string" || !CHART_TYPES.has(parsed.type as ChartType)) {
    return { ok: false, error: "type must be one of: line, bar, area, scatter" };
  }

  const labelsRaw = resolveLabelsRaw(parsed);
  if (!Array.isArray(labelsRaw)) {
    return { ok: false, error: "labels must be an array" };
  }
  if (labelsRaw.length === 0) {
    return { ok: false, error: "labels must not be empty" };
  }
  const labels: string[] = [];
  for (let i = 0; i < labelsRaw.length; i++) {
    const label = labelsRaw[i];
    if (typeof label !== "string") {
      return { ok: false, error: `labels[${i}] must be a string` };
    }
    labels.push(label);
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

  const title = optionalString(parsed.title, "title");
  if (title && typeof title === "object") return { ok: false, error: title.error };
  const subtitle = optionalString(parsed.subtitle, "subtitle");
  if (subtitle && typeof subtitle === "object") return { ok: false, error: subtitle.error };
  const unit = optionalString(parsed.unit, "unit");
  if (unit && typeof unit === "object") return { ok: false, error: unit.error };
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

  // Strip unknown keys (e.g. options / plugins) — never forward to Chart.js.
  const spec: ChartSpec = {
    version: 1,
    type: parsed.type as ChartType,
    labels,
    series,
  };
  if (typeof title === "string") spec.title = title;
  if (typeof subtitle === "string") spec.subtitle = subtitle;
  if (typeof unit === "string") spec.unit = unit;
  if (typeof xTitle === "string") spec.xTitle = xTitle;
  if (typeof yTitle === "string") spec.yTitle = yTitle;
  if (typeof yMin === "number") spec.yMin = yMin;
  if (typeof yMax === "number") spec.yMax = yMax;
  if (typeof showLegend === "boolean") spec.showLegend = showLegend;

  return { ok: true, spec };
}
