import { describe, expect, it } from "vitest";
import { needsWorkspaceBeforeSend, openFolderGateOnNewSession } from "./folderGatePolicy";

describe("D-082 folder gate policy", () => {
  it("never opens the gate on new session alone", () => {
    expect(openFolderGateOnNewSession()).toBe(false);
  });

  it("blocks send only when project-scoped and no workspace", () => {
    expect(needsWorkspaceBeforeSend(true, null)).toBe(true);
    expect(needsWorkspaceBeforeSend(true, "")).toBe(true);
    expect(needsWorkspaceBeforeSend(true, "/repo")).toBe(false);
    expect(needsWorkspaceBeforeSend(false, null)).toBe(false);
    expect(needsWorkspaceBeforeSend(false, "/scratch")).toBe(false);
  });
});
