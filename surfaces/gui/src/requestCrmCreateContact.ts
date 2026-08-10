/** Dialogue CTA: after `ready_for_crm_create_contact`, inject HubSpot create-contact request. */

export const REQUEST_CRM_CREATE_CONTACT_EVENT = "ocw-request-crm-create-contact";

export const READY_FOR_CRM_CREATE_CONTACT = "ready_for_crm_create_contact";

/** True when assistant text marks readiness to create a HubSpot contact (not note-write). */
export function isReadyForCrmCreateContact(text: string | undefined | null): boolean {
  if (!text) return false;
  return text.includes(READY_FOR_CRM_CREATE_CONTACT);
}

/**
 * User message when «提交创建联系人审批» is clicked.
 * Agent must call `hubspot_create_contact` (approval-gated); never invent email.
 */
export function crmCreateContactIntentMessage(): string {
  return (
    "请提交创建联系人审批：在质量门禁已为 ready_for_crm_create_contact 的前提下，" +
    "使用连接器工具 hubspot_create_contact 在 HubSpot 新建联系人。" +
    "email 必填，且必须来自用户已提供或已核验的事实；" +
    "first_name / last_name / portal 仅在已知时填写，不得编造。" +
    "调用后等待我在审批卡中允许；未批准前不得宣称已创建联系人。" +
    "本操作不要调用 hubspot_update_object / hubspot_create_task；" +
    "若只需给已有对象写笔记，应使用 ready_for_crm_write 与 hubspot_log_note。" +
    "若 HubSpot 未连接，请用中文说明并引导我在「连接」中配置 HubSpot 门户。"
  );
}
