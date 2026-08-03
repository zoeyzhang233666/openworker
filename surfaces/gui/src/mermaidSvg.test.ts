import { describe, expect, it } from "vitest";
import { fitLightboxSize, prepareLightboxSvg } from "./mermaidSvg";

describe("prepareLightboxSvg", () => {
  it("ensures viewBox and strips fixed width/height for CSS sizing", () => {
    const raw =
      '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200"><rect width="400" height="200"/></svg>';
    const prepared = prepareLightboxSvg(raw);
    expect(prepared.naturalW).toBe(400);
    expect(prepared.naturalH).toBe(200);
    expect(prepared.html).toContain('viewBox="0 0 400 200"');
    const root = new DOMParser().parseFromString(prepared.html, "image/svg+xml").documentElement;
    expect(root.hasAttribute("width")).toBe(false);
    expect(root.hasAttribute("height")).toBe(false);
  });

  it("derives viewBox from width/height when missing", () => {
    const raw =
      '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="160"><circle cx="10" cy="10" r="5"/></svg>';
    const prepared = prepareLightboxSvg(raw);
    expect(prepared.naturalW).toBe(320);
    expect(prepared.naturalH).toBe(160);
    expect(prepared.html).toContain('viewBox="0 0 320 160"');
  });
});

describe("fitLightboxSize", () => {
  it("fits wide diagram into viewport while preserving aspect", () => {
    const size = fitLightboxSize(1000, 500, 800, 600);
    expect(size.w).toBe(800);
    expect(size.h).toBe(400);
  });

  it("fits tall diagram into viewport while preserving aspect", () => {
    const size = fitLightboxSize(400, 800, 800, 600);
    expect(size.w).toBe(300);
    expect(size.h).toBe(600);
  });
});
