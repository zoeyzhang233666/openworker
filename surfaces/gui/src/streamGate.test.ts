import { describe, expect, it } from "vitest";
import { streamMode } from "./streamGate";
import type { Item } from "./types";
const USER: Item[] = [{ kind: "user", text: "你好" }];
const AFTER_TOOL: Item[] = [...USER,
  { kind: "tool", id: "t1", name: "read_file", args: { path: "a.md" }, status: "ok" },
];
describe("incremental text visibility", () => {
  it.each(["你", "你好！", "正在核对来源。", "H", "Hello!"])("shows first fragment: %s", text => {
    expect(streamMode(text, USER, true)).toBe("answer");
    expect(streamMode(text, AFTER_TOOL, true)).toBe("answer");
  });
  it("keeps settling text visible", () => {
    expect(streamMode("完成", AFTER_TOOL, false)).toBe("answer");
  });
  it("does not render an empty bubble", () => {
    expect(streamMode("", USER, true)).toBe("none");
    expect(streamMode("  ", USER, true)).toBe("none");
  });
});
