import { describe, expect, it } from "vitest";
import {
  READY_FOR_CRM_UPDATE_OBJECT,
  crmUpdateObjectIntentMessage,
  isReadyForCrmUpdateObject,
} from "./requestCrmUpdateObject";
import { isReadyForCrmWrite } from "./requestCrmWriteApproval";
import { isReadyForCrmCreateTask } from "./requestCrmCreateTask";

describe("requestCrmUpdateObject", () => {
  it("detects recommended_action ready_for_crm_update_object without matching other gates", () => {
    expect(isReadyForCrmUpdateObject(null)).toBe(false);
    expect(isReadyForCrmUpdateObject("draft only")).toBe(false);
    expect(isReadyForCrmUpdateObject(READY_FOR_CRM_UPDATE_OBJECT)).toBe(false);
    expect(
      isReadyForCrmUpdateObject(
        "若后续需要更新字段，我会走 ready_for_crm_update_object 与审批",
      ),
    ).toBe(false);
    expect(
      isReadyForCrmUpdateObject(
        `verdict=pass\nrecommended_action: ${READY_FOR_CRM_UPDATE_OBJECT}`,
      ),
    ).toBe(true);
    expect(isReadyForCrmUpdateObject("recommended_action: ready_for_crm_write")).toBe(
      false,
    );
    expect(isReadyForCrmWrite("recommended_action: ready_for_crm_update_object")).toBe(
      false,
    );
    expect(isReadyForCrmCreateTask("recommended_action: ready_for_crm_update_object")).toBe(
      false,
    );
  });

  it("builds an intent that requires hubspot_update_object and human approval", () => {
    const msg = crmUpdateObjectIntentMessage();
    expect(msg).toContain("hubspot_update_object");
    expect(msg).toContain("ready_for_crm_update_object");
    expect(msg).toContain("审批");
    expect(msg).toContain("object_id");
    expect(msg).toMatch(/连接/);
    expect(msg).toMatch(/hubspot_log_note|hubspot_create_contact|hubspot_create_task/);
  });
});
