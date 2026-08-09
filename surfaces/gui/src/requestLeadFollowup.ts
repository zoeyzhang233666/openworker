/** Lead-list workbench CTAs: inject follow-up / rescore intents into chat (no auto-run). */

export const REQUEST_LEAD_FOLLOWUP_EVENT = "ocw-request-lead-followup";

export type LeadFollowupKind = "research" | "rescore";

export type RequestLeadFollowupDetail = {
  kind: LeadFollowupKind;
  company?: string;
  nextAction?: string;
  matchReason?: string;
  skuSummary?: string;
  marketSummary?: string;
};

/** Continue research for one company — user must confirm in chat; workbench does not run tools. */
export function leadResearchIntentMessage(detail: {
  company: string;
  nextAction?: string;
  matchReason?: string;
}): string {
  const company = (detail.company || "").trim() || "（未命名企业）";
  const next = (detail.nextAction || "").trim();
  const reason = (detail.matchReason || "").trim();
  const parts = [
    `请继续补查客户清单中的企业「${company}」。`,
    "不要自动外发或写 CRM；先列出证据缺口与拟用查询，等我确认后再执行补查。",
  ];
  if (next) parts.push(`当前建议下一步：${next}`);
  if (reason) parts.push(`匹配原因摘要：${reason}`);
  return parts.join("");
}

/** Rescore / adjust ICP for the imported list — scores change only after user confirms in chat. */
export function leadRescoreIntentMessage(detail: {
  skuSummary?: string;
  marketSummary?: string;
}): string {
  const sku = (detail.skuSummary || "").trim();
  const market = (detail.marketSummary || "").trim();
  const parts = [
    "请基于当前客户清单，与我确认 ICP / 排除条件后重新评分（Lead Fit 与 Evidence Confidence）。",
    "工作台不会静默改分；须我确认评分规则与输入后再调用评分脚本。",
    "不要自动外发或写 CRM。",
  ];
  if (sku) parts.push(`SKU 摘要：${sku}`);
  if (market) parts.push(`市场摘要：${market}`);
  return parts.join("");
}

export function leadFollowupIntentMessage(detail: RequestLeadFollowupDetail): string {
  if (detail.kind === "rescore") {
    return leadRescoreIntentMessage({
      skuSummary: detail.skuSummary,
      marketSummary: detail.marketSummary,
    });
  }
  return leadResearchIntentMessage({
    company: detail.company || "",
    nextAction: detail.nextAction,
    matchReason: detail.matchReason,
  });
}
