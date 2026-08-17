import { describe, expect, it } from "vitest";
import { fullPersonaName, shortPersonaName } from "./personaScope";

describe("personaScope ChemClaw branding", () => {
  it("maps default cowork id to ChemClaw, not Coworker", () => {
    expect(shortPersonaName("ChemClaw", "cowork")).toBe("ChemClaw");
    expect(shortPersonaName(undefined, "cowork")).toBe("ChemClaw");
    expect(fullPersonaName("ChemClaw", "cowork")).toBe("ChemClaw");
    expect(fullPersonaName(undefined, "cowork")).toBe("ChemClaw");
  });

  it("does not append Coworker to ChemClaw display name", () => {
    expect(fullPersonaName("ChemClaw", "cowork")).not.toMatch(/Coworker/i);
  });
});
