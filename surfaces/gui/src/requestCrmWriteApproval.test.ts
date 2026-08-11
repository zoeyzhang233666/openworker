import { describe, expect, it } from "vitest";
import {
  READY_FOR_CRM_WRITE,
  crmWriteApprovalIntentMessage,
  isReadyForCrmWrite,
} from "./requestCrmWriteApproval";

describe("requestCrmWriteApproval", () => {
  it("detects recommended_action ready_for_crm_write only", () => {
    expect(isReadyForCrmWrite(null)).toBe(false);
    expect(isReadyForCrmWrite("draft only")).toBe(false);
    expect(isReadyForCrmWrite(READY_FOR_CRM_WRITE)).toBe(false);
    expect(isReadyForCrmWrite("质量门禁通过（ready_for_crm_write）")).toBe(false);
    expect(
      isReadyForCrmWrite(`verdict=pass\nrecommended_action: ${READY_FOR_CRM_WRITE}`),
    ).toBe(true);
    expect(
      isReadyForCrmWrite("Follow-up ready. recommended_action: ready_for_crm_write"),
    ).toBe(true);
  });

  it("builds an intent that requires hubspot_log_note and human approval", () => {
    const msg = crmWriteApprovalIntentMessage();
    expect(msg).toContain("hubspot_log_note");
    expect(msg).toContain("ready_for_crm_write");
    expect(msg).toContain("审批");
    expect(msg).toContain("hubspot_create_contact");
    expect(msg).toMatch(/连接/);
  });
});
