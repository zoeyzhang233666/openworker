import { describe, expect, it } from "vitest";
import {
  DEFAULT_PERMISSION_MODE,
  modeFromHealth,
  resolvePermissionMode,
} from "./permissionMode";

describe("permissionMode boot seeding", () => {
  it("reads auto from health so Composer can show full access before WS ready", () => {
    expect(modeFromHealth({ mode: "auto" })).toBe("auto");
    expect(resolvePermissionMode("auto", DEFAULT_PERMISSION_MODE)).toBe("auto");
  });

  it("keeps interactive when health omits or sends an unknown mode", () => {
    expect(modeFromHealth({})).toBeNull();
    expect(modeFromHealth({ mode: "yolo" })).toBeNull();
    expect(resolvePermissionMode(undefined)).toBe("interactive");
    expect(resolvePermissionMode("custom")).toBe("interactive");
  });

  it("preserves the already-synced mode when a new session reconnects", () => {
    // startNewSession must not reset Composer; ready remains the authority.
    const synced = resolvePermissionMode("auto");
    expect(resolvePermissionMode(undefined, synced)).toBe("auto");
    expect(resolvePermissionMode("interactive", synced)).toBe("interactive");
  });
});
