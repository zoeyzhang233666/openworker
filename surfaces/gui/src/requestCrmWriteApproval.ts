/** Dialogue CTA: after quality gate `ready_for_crm_write`, inject a HubSpot note write request. */

export const REQUEST_CRM_WRITE_APPROVAL_EVENT = "ocw-request-crm-write-approval";

export const READY_FOR_CRM_WRITE = "ready_for_crm_write";

/** True when assistant text marks the engagement ready for human CRM write. */
export function isReadyForCrmWrite(text: string | undefined | null): boolean {
  if (!text) return false;
  return text.includes(READY_FOR_CRM_WRITE);
}

/**
 * User message sent when the transcript «提交 CRM 写入审批» button is clicked.
 * Agent must call connector `hubspot_log_note` (still approval-gated); never auto-write.
 */
export function crmWriteApprovalIntentMessage(): string {
  return (
    "请提交 CRM 写入审批：在质量门禁已为 ready_for_crm_write 的前提下，" +
    "使用连接器工具 hubspot_log_note，向已存在的 HubSpot 联系人/公司/交易记录一条跟进笔记。" +
    "请先确认对象类型（contacts|companies|deals）、对象 ID 与笔记正文；" +
    "调用后等待我在审批卡中允许；未批准前不得宣称已写入 CRM。" +
    "本首包不要调用 hubspot_create_contact / hubspot_update_object / hubspot_create_task。" +
    "若 HubSpot 未连接，请用中文说明并引导我在「连接」中配置 HubSpot 门户。"
  );
}
