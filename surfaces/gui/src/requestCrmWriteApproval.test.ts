import { describe, expect, it } from "vitest";
import {
  READY_FOR_CRM_WRITE,
  crmWriteApprovalIntentMessage,
  isReadyForCrmWrite,
} from "./requestCrmWriteApproval";

describe("requestCrmWriteApproval", () => {
  it("detects ready_for_crm_write in assistant text", () => {
    expect(isReadyForCrmWrite(null)).toBe(false);
    expect(isReadyForCrmWrite("draft only")).toBe(false);
    expect(isReadyForCrmWrite(`verdict=pass\n${READY_FOR_CRM_WRITE}`)).toBe(true);
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
