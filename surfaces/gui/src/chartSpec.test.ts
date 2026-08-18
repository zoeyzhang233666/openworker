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

  it("accepts candlestick ohlc as [o,h,l,c] tuples", () => {
    const result = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        title: "沥青期货",
        labels: ["2026-05-15", "2026-05-18"],
        ohlc: [
          [4203, 4292, 4203, 4275],
          [4294, 4373, 4269, 4334],
        ],
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.ohlc).toEqual([
        { o: 4203, h: 4292, l: 4203, c: 4275 },
        { o: 4294, h: 4373, l: 4269, c: 4334 },
      ]);
    }
  });

  it("rejects ohlc tuple with wrong length", () => {
    const result = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["D1"],
        ohlc: [[70, 72, 69]],
      }),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/\[o,h,l,c\]/);
  });

  it("rejects ohlc tuple with non-finite number", () => {
    const result = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["D1"],
        ohlc: [[70, 72, 69, "x"]],
      }),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/ohlc\[0\]\.c/);
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

  it("accepts candlestick stages and drops invalid tones", () => {
    const result = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "candlestick",
        labels: ["2026-01-01", "2026-01-02", "2026-01-03"],
        ohlc: [
          { o: 1, h: 2, l: 0.5, c: 1.5 },
          { o: 2, h: 3, l: 1.5, c: 2.5 },
          { o: 2.5, h: 2.8, l: 2, c: 2.2 },
        ],
        stages: [
          { start: "2026-01-01", end: "2026-01-02", tone: "up", reason: "地缘溢价" },
          { start: "2026-01-02", end: "2026-01-03", tone: "bogus", reason: "无效" },
          { start: "2026-01-03", end: "2026-01-03", tone: "side", reason: "横盘" },
        ],
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.stages).toEqual([
        { start: "2026-01-01", end: "2026-01-02", tone: "up", reason: "地缘溢价" },
        { start: "2026-01-03", end: "2026-01-03", tone: "side", reason: "横盘" },
      ]);
    }
  });

  it("accepts stages and focusLabel on line charts", () => {
    const result = parseChartSpec(
      JSON.stringify({
        ...validLine,
        focusLabel: "D1",
        stages: [{ start: "D1", end: "D2", tone: "up", reason: "涨" }],
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.focusLabel).toBe("D1");
      expect(result.spec.stages).toEqual([
        { start: "D1", end: "D2", tone: "up", reason: "涨" },
      ]);
    }
  });

  it("ignores stages on bar charts", () => {
    const result = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "bar",
        labels: ["A", "B"],
        series: [{ name: "s", values: [1, 2] }],
        stages: [{ start: "A", end: "B", tone: "up", reason: "涨" }],
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.spec.stages).toBeUndefined();
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

  it("merges stages from short-ref onto tool chart_spec", () => {
    const result = resolveChartSource(
      JSON.stringify({
        type: "candlestick",
        from_tool: "lookup_yahoo_ohlc",
        symbol: "CL=F",
        title: "WTI 走势阶段",
        stages: [
          { start: "2026-01-01", end: "2026-01-02", tone: "up", reason: "地缘溢价抬升" },
        ],
      }),
      [{ name: "lookup_yahoo_ohlc", preview: toolPreview }],
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.ohlc).toHaveLength(2);
      expect(result.spec.title).toBe("WTI 走势阶段");
      expect(result.spec.stages).toEqual([
        { start: "2026-01-01", end: "2026-01-02", tone: "up", reason: "地缘溢价抬升" },
      ]);
    }
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