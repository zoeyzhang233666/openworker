/** Dialogue CTA: after quality gate `ready_for_human_send`, inject a human send request. */

export const REQUEST_SEND_APPROVAL_EVENT = "ocw-request-send-approval";

export const READY_FOR_HUMAN_SEND = "ready_for_human_send";

/** True when assistant text (or artifact body) marks the draft ready for human send. */
export function isReadyForHumanSend(text: string | undefined | null): boolean {
  if (!text) return false;
  return text.includes(READY_FOR_HUMAN_SEND);
}

/**
 * User message sent when the transcript «提交发送审批» button is clicked.
 * Agent must call connector `email_send` (still approval-gated); never auto-send.
 */
export function sendApprovalIntentMessage(): string {
  return (
    "请提交发送审批：在质量门禁已为 ready_for_human_send 的前提下，" +
    "使用连接器工具 email_send 发送上述开发信草稿。" +
    "请先确认或请我提供可靠收件人邮箱（to）、主题与正文；" +
    "调用后等待我在审批卡中允许；未批准前不得宣称已发送。" +
    "若邮件未连接，请用中文说明并引导我在「连接」中配置 Email（IMAP/SMTP）。"
  );
}
