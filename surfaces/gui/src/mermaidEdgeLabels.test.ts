import { describe, expect, it } from "vitest";
import { mermaidNeedsEdgeLabels } from "./mermaidEdgeLabels";

describe("mermaidNeedsEdgeLabels", () => {
  it("flags bare flowchart edges", () => {
    expect(mermaidNeedsEdgeLabels("flowchart TD\n  A --> B")).toBe(true);
  });

  it("accepts labeled edges", () => {
    expect(mermaidNeedsEdgeLabels('flowchart TD\n  A -->|"采购"| B')).toBe(false);
  });

  it("ignores pie charts", () => {
    expect(mermaidNeedsEdgeLabels('pie title x\n  "a": 10')).toBe(false);
  });
});
