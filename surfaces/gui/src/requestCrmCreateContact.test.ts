import { describe, expect, it } from "vitest";
import {
  READY_FOR_CRM_CREATE_CONTACT,
  crmCreateContactIntentMessage,
  isReadyForCrmCreateContact,
} from "./requestCrmCreateContact";
import { isReadyForCrmWrite } from "./requestCrmWriteApproval";

describe("requestCrmCreateContact", () => {
  it("detects ready_for_crm_create_contact without matching note-write gate", () => {
    expect(isReadyForCrmCreateContact(null)).toBe(false);
    expect(isReadyForCrmCreateContact("draft only")).toBe(false);
    expect(isReadyForCrmCreateContact(`verdict=pass\n${READY_FOR_CRM_CREATE_CONTACT}`)).toBe(
      true,
    );
    expect(isReadyForCrmCreateContact("ready_for_crm_write")).toBe(false);
    expect(isReadyForCrmWrite(READY_FOR_CRM_CREATE_CONTACT)).toBe(false);
  });

  it("builds an intent that requires hubspot_create_contact and human approval", () => {
    const msg = crmCreateContactIntentMessage();
    expect(msg).toContain("hubspot_create_contact");
    expect(msg).toContain("ready_for_crm_create_contact");
    expect(msg).toContain("审批");
    expect(msg).toContain("email");
    expect(msg).toMatch(/连接/);
    expect(msg).toMatch(/hubspot_update_object|hubspot_create_task/);
  });
});
