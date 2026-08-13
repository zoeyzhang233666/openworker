/** Dialogue CTA: after `ready_for_crm_create_task`, inject HubSpot create-task request. */

export const REQUEST_CRM_CREATE_TASK_EVENT = "ocw-request-crm-create-task";

export const READY_FOR_CRM_CREATE_TASK = "ready_for_crm_create_task";

/** Gate line only — bare mentions in prose must not show the CTA. */
const READY_FOR_CRM_CREATE_TASK_ACTION =
  /recommended_action:\s*ready_for_crm_create_task\b/i;

/** True when assistant text marks readiness to create a HubSpot follow-up task. */
export function isReadyForCrmCreateTask(text: string | undefined | null): boolean {
  if (!text) return false;
  return READY_FOR_CRM_CREATE_TASK_ACTION.test(text);
}

/**
 * User message when «提交 CRM 任务创建审批» is clicked.
 * Agent must call `hubspot_create_task` (approval-gated); never invent title.
 */
export function crmCreateTaskIntentMessage(): string {
  return (
    "请提交 CRM 任务创建审批：在质量门禁已为 ready_for_crm_create_task 的前提下，" +
    "使用连接器工具 hubspot_create_task 在 HubSpot 创建跟进任务。" +
    "title 必须来自已确认的跟进动作，不得编造；due / notes / portal 仅在已知时填写。" +
    "若已知联系人或公司，把名称与 ID 写入 notes（本工具不关联对象）。" +
    "调用后等待我在审批卡中允许；未批准前不得宣称已创建任务。" +
    "本操作不要调用 hubspot_update_object / hubspot_log_note / hubspot_create_contact；" +
    "若只需更新字段或写笔记/新建联系人，应使用对应门禁与 CTA。" +
    "若 HubSpot 未连接，请用中文说明并引导我在「连接」中配置 HubSpot 门户。"
  );
}
