import { describe, expect, it } from "vitest";
import { parseChartSpec, resolveChartSource } from "./chartSpec";

const validLine = {
  version: 1 as const,
  type: "line" as const,
  title: "甲醇近30天",
  unit: "元/吨",
  labels: ["D1", "D2", "D3"],
  series: [{ name: "陕西", values: [6100, 6035, null] }],
};

describe("parseChartSpec", () => {
  it("accepts a valid line chart", () => {
    const result = parseChartSpec(JSON.stringify(validLine));
    expect(result).toEqual({ ok: true, spec: validLine });
  });

  it("accepts bar and area", () => {
    expect(parseChartSpec(JSON.stringify({ ...validLine, type: "bar" })).ok).toBe(true);
    expect(parseChartSpec(JSON.stringify({ ...validLine, type: "area" })).ok).toBe(true);
  });

  it("rejects invalid JSON", () => {
    const result = parseChartSpec("{not-json");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/json/i);
  });

  it("rejects mismatched series.values length", () => {
    const result = parseChartSpec(
      JSON.stringify({
        ...validLine,
        series: [{ name: "陕西", values: [1, 2] }],
      }),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/length/i);
  });

  it("rejects string values", () => {
    const result = parseChartSpec(
      JSON.stringify({
        ...validLine,
        series: [{ name: "陕西", values: [6100, "6035", null] }],
      }),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/number/i);
  });

  it("rejects version other than 1", () => {
    const result = parseChartSpec(JSON.stringify({ ...validLine, version: 2 }));
    expect(result.ok).toBe(false);
  });

  it("rejects empty series", () => {
    const result = parseChartSpec(JSON.stringify({ ...validLine, series: [] }));
    expect(result.ok).toBe(false);
  });

  it("maps xLabel/yLabel aliases to xTitle/yTitle", () => {
    const result = parseChartSpec(
      JSON.stringify({
        ...validLine,
        xLabel: "日期",
        yLabel: "元/吨",
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.xTitle).toBe("日期");
      expect(result.spec.yTitle).toBe("元/吨");
      expect("xLabel" in result.spec).toBe(false);
      expect("yLabel" in result.spec).toBe(false);
    }
  });

  it("maps snake_case x_label/y_label aliases", () => {
    const result = parseChartSpec(
      JSON.stringify({
        ...validLine,
        x_label: "日期",
        y_label: "均价（元/吨）",
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.xTitle).toBe("日期");
      expect(result.spec.yTitle).toBe("均价（元/吨）");
    }
  });

  it("prefers xTitle/yTitle over xLabel/yLabel", () => {
    const result = parseChartSpec(
      JSON.stringify({
        ...validLine,
        xTitle: "X",
        yTitle: "Y",
        xLabel: "日期",
        yLabel: "元/吨",
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.xTitle).toBe("X");
      expect(result.spec.yTitle).toBe("Y");
    }
  });

  it("rejects function-like keys / arbitrary options bags", () => {
    const result = parseChartSpec(
      JSON.stringify({
        ...validLine,
        options: { plugins: { tooltip: { callbacks: {} } } },
      }),
    );
    if (result.ok) {
      expect("options" in result.spec).toBe(false);
    } else {
      expect(result.ok).toBe(false);
    }
  });

  it("accepts nested x.labels with dual series (LLM drift)", () => {
    const result = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "line",
        title: "柠檬酸日度均价走势（山东昌乐县 · 元/吨）",
        x: { labels: ["06-18", "06-20", "06-22"] },
        series: [
          { name: "一水柠檬酸", values: [6495, 6495, 6495] },
          { name: "无水柠檬酸", values: [7066.67, 7066.67, 7066.67] },
        ],
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.labels).toEqual(["06-18", "06-20", "06-22"]);
      expect(result.spec.series).toHaveLength(2);
      expect("x" in result.spec).toBe(false);
    }
  });

  it("prefers top-level labels over x.labels", () => {
    const result = parseChartSpec(
      JSON.stringify({
        ...validLine,
        labels: ["A", "B", "C"],
        x: { labels: ["X", "Y", "Z"] },
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.spec.labels).toEqual(["A", "B", "C"]);
  });

  it("rejects empty x object without labels", () => {
    const { labels: _drop, ...withoutLabels } = validLine;
    const result = parseChartSpec(JSON.stringify({ ...withoutLabels, x: {} }));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/labels must be an array/i);
  });

  it("defaults missing version to 1", () => {
    const { version: _v, ...rest } = validLine;
    const result = parseChartSpec(JSON.stringify(rest));
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.spec.version).toBe(1);
  });

  it("accepts candlestick ohlc aligned with labels", () => {
    const result = parseChartSpec(
      JSON.stringify({
        type: "candlestick",
        title: "WTI",
        labels: ["D1", "D2"],
        ohlc: [
          { o: 70, h: 72, l: 69, c: 71 },
          { open: 71, high: 73, low: 70, close: 72 },
        ],
        yLabel: "USD/bbl",
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.type).toBe("candlestick");
      expect(result.spec.series).toEqual([]);
      expect(result.spec.ohlc).toEqual([
        { o: 70, h: 72, l: 69, c: 71 },
        { o: 71, h: 73, l: 70, c: 72 },
      ]);
      expect(result.spec.yTitle).toBe("USD/bbl");
    }
  });

  it("truncates candlestick to min(labels, ohlc) prefix when lengths differ", () => {
    const result = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["D1", "D2", "D3"],
        ohlc: [
          { o: 1, h: 2, l: 0.5, c: 1.5 },
          { o: 2, h: 3, l: 1.5, c: 2.5 },
        ],
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.labels).toEqual(["D1", "D2"]);
      expect(result.spec.ohlc).toHaveLength(2);
    }
  });

  it("rejects candlestick without ohlc", () => {
    const result = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["D1"],
        series: [{ name: "x", values: [1] }],
      }),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/ohlc/i);
  });
});

describe("resolveChartSource Yahoo short-ref", () => {
  const toolPreview = JSON.stringify({
    status: "ok",
    symbol: "CL=F",
    chart_spec: {
      version: 1,
      type: "candlestick",
      title: "Crude Oil (CL=F)",
      labels: ["2026-01-01", "2026-01-02"],
      ohlc: [
        { o: 70, h: 72, l: 69, c: 71 },
        { o: 71, h: 73, l: 70, c: 72 },
      ],
      yLabel: "USD",
    },
  });

  it("resolves from_tool + symbol from tool preview", () => {
    const result = resolveChartSource(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        from_tool: "lookup_yahoo_ohlc",
        symbol: "cl=f",
      }),
      [{ name: "lookup_yahoo_ohlc", preview: toolPreview }],
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.ohlc).toHaveLength(2);
      expect(result.spec.title).toBe("Crude Oil (CL=F)");
    }
  });

  it("allows title override on short-ref", () => {
    const result = resolveChartSource(
      JSON.stringify({
        type: "candlestick",
        from_tool: "lookup_yahoo_ohlc",
        symbol: "CL=F",
        title: "WTI",
      }),
      [{ name: "lookup_yahoo_ohlc", preview: toolPreview }],
    );
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.spec.title).toBe("WTI");
  });

  it("errors when symbol is missing from tools", () => {
    const result = resolveChartSource(
      JSON.stringify({
        type: "candlestick",
        from_tool: "lookup_yahoo_ohlc",
        symbol: "BZ=F",
      }),
      [{ name: "lookup_yahoo_ohlc", preview: toolPreview }],
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/BZ=F/i);
  });
});