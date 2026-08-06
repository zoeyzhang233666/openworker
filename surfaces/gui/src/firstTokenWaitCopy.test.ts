import { describe, expect, it } from "vitest";
import {
  FIRST_TOKEN_WAIT_EARLY_KEYS,
  FIRST_TOKEN_WAIT_LATE_KEYS,
  FIRST_TOKEN_WAIT_ROTATE_MS,
  FIRST_TOKEN_WAIT_ROTATION_KEYS,
  advanceFirstTokenWaitIndex,
  nextFirstTokenWaitIndex,
  isFirstTokenEmptyWindow,
  isFirstTokenThinkingOpen,
  hasPostUserTurnActivity,
} from "./firstTokenWaitCopy";

describe("firstTokenWaitCopy", () => {
  it("exposes early→late rotation sequence and a 3s rotate interval", () => {
    expect(FIRST_TOKEN_WAIT_EARLY_KEYS.length).toBe(2);
    expect(FIRST_TOKEN_WAIT_LATE_KEYS.length).toBe(4);
    expect(FIRST_TOKEN_WAIT_ROTATION_KEYS).toEqual([
      ...FIRST_TOKEN_WAIT_EARLY_KEYS,
      ...FIRST_TOKEN_WAIT_LATE_KEYS,
    ]);
    expect(FIRST_TOKEN_WAIT_ROTATION_KEYS.length).toBe(6);
    expect(FIRST_TOKEN_WAIT_ROTATE_MS).toBe(3000);
  });

  it("advances and wraps rotation indices", () => {
    expect(nextFirstTokenWaitIndex(0)).toBe(0);
    expect(advanceFirstTokenWaitIndex(0)).toBe(1);
    expect(advanceFirstTokenWaitIndex(5)).toBe(0);
    expect(advanceFirstTokenWaitIndex(5, FIRST_TOKEN_WAIT_ROTATION_KEYS.length)).toBe(0);
  });

  it("detects first-token empty window vs post-user activity", () => {
    const idle = [{ kind: "user", text: "hi" }];
    expect(
      isFirstTokenEmptyWindow(idle, {
        running: true,
        compacting: false,
        reasoningStream: "",
        streaming: "",
      }),
    ).toBe(true);
    expect(
      isFirstTokenEmptyWindow(idle, {
        running: true,
        compacting: false,
        reasoningStream: "think",
        streaming: "",
      }),
    ).toBe(false);
    expect(hasPostUserTurnActivity([...idle, { kind: "tool" }])).toBe(true);
    expect(isFirstTokenThinkingOpen(idle)).toBe(true);
    expect(isFirstTokenThinkingOpen([...idle, { kind: "tool" }])).toBe(false);
  });
});
