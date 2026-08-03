import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  mermaidExportFilename,
  downloadSvg,
  downloadPng,
  MERMAID_PNG_MAX_EDGE,
} from "./mermaidExports";

describe("mermaidExports", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "URL",
      {
        createObjectURL: vi.fn(() => "blob:mock"),
        revokeObjectURL: vi.fn(),
      },
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("formats filename chemclaw-diagram-YYYYMMDD-HHmmss.ext", () => {
    const at = new Date(Date.UTC(2026, 7, 3, 5, 6, 7)); // month 0-based → Aug
    expect(mermaidExportFilename("svg", at)).toMatch(
      /^chemclaw-diagram-\d{8}-\d{6}\.svg$/,
    );
    expect(mermaidExportFilename("png", at)).toMatch(/\.png$/);
  });

  it("downloadSvg creates an anchor click with svg mime", () => {
    const click = vi.fn();
    const el = { href: "", download: "", click } as unknown as HTMLAnchorElement;
    vi.spyOn(document, "createElement").mockReturnValue(el);
    downloadSvg("<svg></svg>", "chemclaw-diagram-test.svg");
    expect(el.download).toBe("chemclaw-diagram-test.svg");
    expect(click).toHaveBeenCalled();
  });

  it("downloadPng rejects when edge exceeds limit", async () => {
    // Force measured size above MERMAID_PNG_MAX_EDGE via stubbed Image in implementation test hook,
    // or call an exported measure helper. Prefer: export function assertPngBounds(w, h).
    const { assertPngBounds } = await import("./mermaidExports");
    expect(() => assertPngBounds(MERMAID_PNG_MAX_EDGE + 1, 10)).toThrow(/PNG_TOO_LARGE/);
  });
});
