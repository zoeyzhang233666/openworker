/** Dialogue CTA: after `ready_for_crm_update_object`, inject HubSpot field-update request. */

export const REQUEST_CRM_UPDATE_OBJECT_EVENT = "ocw-request-crm-update-object";

export const READY_FOR_CRM_UPDATE_OBJECT = "ready_for_crm_update_object";

/** Gate line only — bare mentions in prose must not show the CTA. */
const READY_FOR_CRM_UPDATE_OBJECT_ACTION =
  /recommended_action:\s*ready_for_crm_update_object\b/i;

/** True when assistant text marks readiness to update HubSpot object properties. */
export function isReadyForCrmUpdateObject(text: string | undefined | null): boolean {
  if (!text) return false;
  return READY_FOR_CRM_UPDATE_OBJECT_ACTION.test(text);
}

/**
 * User message when «提交 CRM 字段更新审批» is clicked.
 * Agent must call `hubspot_update_object` (approval-gated); never invent IDs/values.
 */
export function crmUpdateObjectIntentMessage(): string {
  return (
    "请提交 CRM 字段更新审批：在质量门禁已为 ready_for_crm_update_object 的前提下，" +
    "使用连接器工具 hubspot_update_object 更新已有 HubSpot 记录的字段。" +
    "object_type（contacts|companies|deals）、object_id 与非空 properties 必须来自用户已提供或已核验的事实，不得编造。" +
    "调用后等待我在审批卡中允许；未批准前不得宣称已更新 CRM。" +
    "本操作不要调用 hubspot_log_note / hubspot_create_contact / hubspot_create_task；" +
    "若只需写笔记或新建联系人/任务，应使用对应门禁与 CTA。" +
    "若 HubSpot 未连接，请用中文说明并引导我在「连接」中配置 HubSpot 门户。"
  );
}
