import { describe, expect, it } from "vitest";
import {
  leadFollowupIntentMessage,
  leadResearchIntentMessage,
  leadRescoreIntentMessage,
} from "./requestLeadFollowup";

describe("requestLeadFollowup", () => {
  it("builds a research intent with company and no auto-send", () => {
    const msg = leadResearchIntentMessage({
      company: "Example Chemie",
      nextAction: "补官网",
      matchReason: "SKU 相关",
    });
    expect(msg).toContain("Example Chemie");
    expect(msg).toContain("补官网");
    expect(msg).toContain("SKU 相关");
    expect(msg).toMatch(/确认/);
    expect(msg).not.toMatch(/请自动外发/);
  });

  it("builds a rescore intent that forbids silent score changes", () => {
    const msg = leadRescoreIntentMessage({
      skuSummary: "苯甲酸钠",
      marketSummary: "DE",
    });
    expect(msg).toContain("重新评分");
    expect(msg).toContain("苯甲酸钠");
    expect(msg).toContain("不会静默改分");
  });

  it("routes by kind", () => {
    expect(
      leadFollowupIntentMessage({ kind: "research", company: "Acme" }),
    ).toContain("Acme");
    expect(leadFollowupIntentMessage({ kind: "rescore" })).toContain("重新评分");
  });
});
