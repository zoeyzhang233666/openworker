import { describe, expect, it } from "vitest";
import {
  READY_FOR_CRM_CREATE_CONTACT,
  crmCreateContactIntentMessage,
  isReadyForCrmCreateContact,
} from "./requestCrmCreateContact";
import { isReadyForCrmWrite } from "./requestCrmWriteApproval";

describe("requestCrmCreateContact", () => {
  it("detects recommended_action ready_for_crm_create_contact without matching note-write gate", () => {
    expect(isReadyForCrmCreateContact(null)).toBe(false);
    expect(isReadyForCrmCreateContact("draft only")).toBe(false);
    expect(isReadyForCrmCreateContact(READY_FOR_CRM_CREATE_CONTACT)).toBe(false);
    expect(
      isReadyForCrmCreateContact(
        "若后续需要新建联系人，我会走 ready_for_crm_create_contact 与审批",
      ),
    ).toBe(false);
    expect(
      isReadyForCrmCreateContact(
        `verdict=pass\nrecommended_action: ${READY_FOR_CRM_CREATE_CONTACT}`,
      ),
    ).toBe(true);
    expect(isReadyForCrmCreateContact("recommended_action: ready_for_crm_write")).toBe(
      false,
    );
    expect(isReadyForCrmWrite("recommended_action: ready_for_crm_create_contact")).toBe(
      false,
    );
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
