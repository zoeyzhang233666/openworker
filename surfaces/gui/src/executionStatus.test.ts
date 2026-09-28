import { describe, expect, it } from "vitest";
import { statusLabel } from "./executionStatus";

describe("shared execution status", () => {
  const t = (key: string) => key;
  it("distinguishes pause and incomplete output from completion across old and new records", () => {
    expect(statusLabel("budget_paused", t)).toBe("Task budget paused");
    expect(statusLabel("waiting_children", t)).toBe("Subagents are still working");
    expect(statusLabel("truncated", t)).toBe("Output incomplete");
    expect(statusLabel("ok", t)).toBe(statusLabel("completed", t));
    expect(statusLabel("error", t)).toBe(statusLabel("failed", t));
  });
});
