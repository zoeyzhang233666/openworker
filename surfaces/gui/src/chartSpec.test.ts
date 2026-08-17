import { describe, expect, it } from "vitest";
import { parseChartSpec } from "./chartSpec";

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

  it("maps x.title / x.label to xTitle when flat aliases absent", () => {
    const withTitle = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "line",
        x: { labels: ["D1", "D2"], title: "日期" },
        series: [{ name: "价", values: [1, 2] }],
      }),
    );
    expect(withTitle.ok).toBe(true);
    if (withTitle.ok) expect(withTitle.spec.xTitle).toBe("日期");

    const withLabel = parseChartSpec(
      JSON.stringify({
        version: 1,
        type: "line",
        x: { labels: ["D1", "D2"], label: "日" },
        series: [{ name: "价", values: [1, 2] }],
      }),
    );
    expect(withLabel.ok).toBe(true);
    if (withLabel.ok) expect(withLabel.spec.xTitle).toBe("日");
  });
});
