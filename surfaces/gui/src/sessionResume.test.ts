import { describe, expect, it } from "vitest";
import {
  eventImpliesRunning,
  runningFromReady,
  shouldApplySessionMessages,
  shouldSkipSessionReselect,
} from "./sessionResume";

describe("shouldSkipSessionReselect", () => {
  it("skips when selecting the already-active session", () => {
    expect(shouldSkipSessionReselect("abc", "abc")).toBe(true);
  });

  it("does not skip a different session", () => {
    expect(shouldSkipSessionReselect("a", "b")).toBe(false);
  });

  it("does not skip when agent must change", () => {
    expect(
      shouldSkipSessionReselect("abc", "abc", {
        agent: "code",
        currentAgent: "chat",
      }),
    ).toBe(false);
  });

  it("does not skip when workspace must change", () => {
    expect(
      shouldSkipSessionReselect("abc", "abc", {
        workspace: "/other",
        currentWorkspace: "/here",
      }),
    ).toBe(false);
  });
});

describe("runningFromReady", () => {
  it("is true only when ready.running is boolean true", () => {
    expect(runningFromReady({ running: true })).toBe(true);
    expect(runningFromReady({ running: false })).toBe(false);
    expect(runningFromReady({})).toBe(false);
    expect(runningFromReady(null)).toBe(false);
  });
});

describe("eventImpliesRunning", () => {
  it("treats mid-turn stream/tool events as live", () => {
    expect(eventImpliesRunning("assistant_delta")).toBe(true);
    expect(eventImpliesRunning("tool_proposed")).toBe(true);
    expect(eventImpliesRunning("permission_required")).toBe(true);
    expect(eventImpliesRunning("ready")).toBe(false);
    expect(eventImpliesRunning("turn_done")).toBe(false);
  });
});

describe("shouldApplySessionMessages", () => {
  it("rejects stale generations and mismatched session ids", () => {
    expect(shouldApplySessionMessages(2, 2, "s1", "s1")).toBe(true);
    expect(shouldApplySessionMessages(1, 2, "s1", "s1")).toBe(false);
    expect(shouldApplySessionMessages(2, 2, "s1", "s2")).toBe(false);
  });
});
