import { describe, expect, it } from "vitest";

const sources = import.meta.glob(["./components/PersonasTab.tsx"], {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

describe("export sales persona localization", () => {
  it("routes the built-in persona through the localized label map", () => {
    expect(sources["./components/PersonasTab.tsx"]).toContain('"export-sales-lobster"');
  });
});
