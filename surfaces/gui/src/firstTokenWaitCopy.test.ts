import { describe, expect, it } from "vitest";
import {
  FEEDBACK_WAIT_ROTATION_KEYS,
  FIRST_TOKEN_WAIT_EARLY_KEYS,
  FIRST_TOKEN_WAIT_LATE_KEYS,
  FIRST_TOKEN_WAIT_ROTATE_MS,
  FIRST_TOKEN_WAIT_ROTATION_KEYS,
  advanceFirstTokenWaitIndex,
  nextFirstTokenWaitIndex,
  isFirstTokenEmptyWindow,
  isFirstTokenThinkingOpen,
  hasPostAnchorActivity,
  hasPostUserTurnActivity,
  waitAnchorIndex,
  waitCopyPool,
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
    expect(FEEDBACK_WAIT_ROTATION_KEYS.length).toBe(4);
  });

  it("advances and wraps rotation indices", () => {
    expect(nextFirstTokenWaitIndex(0)).toBe(0);
    expect(advanceFirstTokenWaitIndex(0)).toBe(1);
    expect(advanceFirstTokenWaitIndex(5)).toBe(0);
    expect(advanceFirstTokenWaitIndex(5, FIRST_TOKEN_WAIT_ROTATION_KEYS.length)).toBe(0);
    expect(advanceFirstTokenWaitIndex(3, FEEDBACK_WAIT_ROTATION_KEYS.length)).toBe(0);
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

  it("treats resolved ask_user as a new wait anchor (empty window again)", () => {
    const items = [
      { kind: "user" },
      { kind: "assistant" },
      { kind: "question", resolved: "偏简单精装" },
    ];
    expect(waitAnchorIndex(items)).toBe(2);
    expect(hasPostAnchorActivity(items)).toBe(false);
    expect(
      isFirstTokenEmptyWindow(items, {
        running: true,
        compacting: false,
        reasoningStream: "",
        streaming: "",
      }),
    ).toBe(true);
    expect(waitCopyPool(items)).toBe("feedback");
  });

  it("unresolved question after user ends the first empty window", () => {
    const items = [{ kind: "user" }, { kind: "question" }];
    expect(hasPostAnchorActivity(items)).toBe(true);
    expect(
      isFirstTokenEmptyWindow(items, {
        running: true,
        compacting: false,
        reasoningStream: "",
        streaming: "",
      }),
    ).toBe(false);
  });

  it("uses feedback pool when user sends right after a resolved question", () => {
    const items = [
      { kind: "user" },
      { kind: "question", resolved: "要目录" },
      { kind: "user" },
    ];
    expect(waitAnchorIndex(items)).toBe(2);
    expect(waitCopyPool(items)).toBe("feedback");
    expect(hasPostAnchorActivity(items)).toBe(false);
  });

  it("uses first pool for a normal new user message", () => {
    expect(waitCopyPool([{ kind: "user" }])).toBe("first");
    expect(
      waitCopyPool([{ kind: "user" }, { kind: "assistant" }, { kind: "user" }]),
    ).toBe("first");
  });
});
