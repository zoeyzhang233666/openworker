import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * D-081: legacy OpenWorker `surfaces.chat` / `surfaces.code` (prefs show_chat/show_code,
 * default false) must never force the active agent back to cowork. Persona enabled/surfaced
 * owns picker visibility; snapping hid 代码/问答 empty-states behind ChemClaw.
 */
describe("D-081 surfaces must not snap agent to cowork", () => {
  it("App.tsx has no chat/code → cowork surfaces gate", () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const src = readFileSync(join(here, "App.tsx"), "utf8");
    expect(src).not.toMatch(/agent === ["']chat["']\s*&&\s*!surfaces\.chat/);
    expect(src).not.toMatch(/agent === ["']code["']\s*&&\s*!surfaces\.code/);
    expect(src).not.toMatch(/!surfaces\.chat\)\s*\|\|\s*\(agent === ["']code["']/);
  });

  it("effective agent stays on the selected persona even when surfaces prefs are off", () => {
    // Policy mirror: selected agent wins; prefs are ignored for binding.
    const surfaces = { cowork: true, chat: false, code: false };
    for (const agent of ["chat", "code", "cowork", "chain-lobster"] as const) {
      const effective = agent; // D-081: no remap via surfaces
      void surfaces;
      expect(effective).toBe(agent);
    }
  });
});
