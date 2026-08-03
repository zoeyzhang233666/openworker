import { describe, expect, it } from "vitest";
import { applyArtifactPreviewNav } from "./navArtifactPreview";

describe("applyArtifactPreviewNav", () => {
  it("on first open collapses and remembers prior nav state", () => {
    const next = applyArtifactPreviewNav(
      { previewOpen: false, navCollapsed: false, navBeforePreview: null },
      true,
    );
    expect(next).toEqual({
      previewOpen: true,
      navCollapsed: true,
      navBeforePreview: false,
      clearPeek: true,
    });
  });

  it("ignores open=true while preview already open (no snap-back after manual expand)", () => {
    const next = applyArtifactPreviewNav(
      {
        previewOpen: true,
        navCollapsed: false, // user expanded via toggleNav
        navBeforePreview: null, // toggle cleared restore
      },
      true,
    );
    expect(next.navCollapsed).toBe(false);
    expect(next.previewOpen).toBe(true);
    expect(next.navBeforePreview).toBeNull();
    expect(next.clearPeek).toBe(false);
  });

  it("on close restores navBeforePreview when still set", () => {
    const next = applyArtifactPreviewNav(
      { previewOpen: true, navCollapsed: true, navBeforePreview: false },
      false,
    );
    expect(next).toEqual({
      previewOpen: false,
      navCollapsed: false,
      navBeforePreview: null,
      clearPeek: false,
    });
  });

  it("on close leaves nav alone when user took control during preview", () => {
    const next = applyArtifactPreviewNav(
      { previewOpen: true, navCollapsed: false, navBeforePreview: null },
      false,
    );
    expect(next).toEqual({
      previewOpen: false,
      navCollapsed: false,
      navBeforePreview: null,
      clearPeek: false,
    });
  });
});
