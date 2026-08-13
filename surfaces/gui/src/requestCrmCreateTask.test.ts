import { describe, expect, it } from "vitest";
import {
  READY_FOR_CRM_CREATE_TASK,
  crmCreateTaskIntentMessage,
  isReadyForCrmCreateTask,
} from "./requestCrmCreateTask";
import { isReadyForCrmUpdateObject } from "./requestCrmUpdateObject";
import { isReadyForCrmCreateContact } from "./requestCrmCreateContact";

describe("requestCrmCreateTask", () => {
  it("detects recommended_action ready_for_crm_create_task without matching other gates", () => {
    expect(isReadyForCrmCreateTask(null)).toBe(false);
    expect(isReadyForCrmCreateTask("draft only")).toBe(false);
    expect(isReadyForCrmCreateTask(READY_FOR_CRM_CREATE_TASK)).toBe(false);
    expect(
      isReadyForCrmCreateTask(
        "若后续需要建任务，我会走 ready_for_crm_create_task 与审批",
      ),
    ).toBe(false);
    expect(
      isReadyForCrmCreateTask(
        `verdict=pass\nrecommended_action: ${READY_FOR_CRM_CREATE_TASK}`,
      ),
    ).toBe(true);
    expect(isReadyForCrmCreateTask("recommended_action: ready_for_crm_create_contact")).toBe(
      false,
    );
    expect(isReadyForCrmUpdateObject("recommended_action: ready_for_crm_create_task")).toBe(
      false,
    );
    expect(isReadyForCrmCreateContact("recommended_action: ready_for_crm_create_task")).toBe(
      false,
    );
  });

  it("builds an intent that requires hubspot_create_task and human approval", () => {
    const msg = crmCreateTaskIntentMessage();
    expect(msg).toContain("hubspot_create_task");
    expect(msg).toContain("ready_for_crm_create_task");
    expect(msg).toContain("审批");
    expect(msg).toContain("title");
    expect(msg).toMatch(/连接/);
    expect(msg).toMatch(/hubspot_update_object|hubspot_log_note|hubspot_create_contact/);
  });
});
