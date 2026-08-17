import { describe, expect, it } from "vitest";
import { artifactIdentity, normalizeSeparators } from "./artifactPath";

describe("artifactIdentity", () => {
  it("keeps workspace-relative paths", () => {
    expect(artifactIdentity("甲醇行情周报_2026W33.md")).toBe("甲醇行情周报_2026W33.md");
    expect(artifactIdentity("artifact:甲醇行情周报_2026W33.md")).toBe("甲醇行情周报_2026W33.md");
    expect(artifactIdentity("charts\\foo.png")).toBe("charts/foo.png");
  });

  it("strips a Windows absolute path only when it is inside the workspace", () => {
    const ws = "C:/Users/EDY/OpenWorker/6ce94f6e-13d";
    expect(
      artifactIdentity(
        "C:\\Users\\EDY\\OpenWorker\\6ce94f6e-13d\\甲醇行情周报_2026W33.md",
        "C:\\Users\\EDY\\OpenWorker\\6ce94f6e-13d",
      ),
    ).toBe("甲醇行情周报_2026W33.md");
    expect(artifactIdentity(`${ws}/reports/a.md`, ws)).toBe("reports/a.md");
  });

  it("does not collapse another session to a basename", () => {
    const ws = "C:/Users/EDY/OpenWorker/session-a";
    expect(
      artifactIdentity("C:\\Users\\EDY\\OpenWorker\\session-b\\secret.md", ws),
    ).toBe("C:/Users/EDY/OpenWorker/session-b/secret.md");
  });

  it("normalizes separators", () => {
    expect(normalizeSeparators("a\\b\\c.md")).toBe("a/b/c.md");
  });
});
