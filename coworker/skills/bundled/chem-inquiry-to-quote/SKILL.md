---
name: chem-inquiry-to-quote
description: "Use when 用户提供化工询盘文本或字段，需要解析为 Inquiry 并用显式数字生成待人工审阅的 QuoteDraft。"
---

# 询盘转报价

把询盘组织为可恢复的 `QuoteRun`：解析 Inquiry →（可选）产品情报 → `calculate_quote` → QuoteDraft。草稿 ≠ 发送；**绝不编造单价或数量**。

## 输入与边界

- 输入：询盘原文/附件摘要、SKU/品名、数量、单位、目标 Incoterm/币种、已知单价或成本字段（可缺）。
- 加载 `chem-product-intelligence` 核验 SKU；用平台 Tool `calculate_quote` 做确定性合计。
- 缺 `quantity` 或 `unit_price` 时状态 `NeedsReview`，列出 `missing_fields`，不得用模型记忆补价。
- 当数量/浓度/规格单位含混、或检测不确定度影响报价表述时，可按需 `load_skill("uncertainty-and-units")` 做单位与不确定度核对；**不得**用其编造单价或数量，也**不得**替代 `calculate_quote`。
- 不调用 `chem-inquiry-feed` / `chem-quote-monitor`（MCP 未纳入本包）；不发邮件、不写 CRM。

## 状态机

维护 `input → parse → calculate → draft → complete|blocked`。合同见 `schemas/quote-run.schema.json`、`inquiry.schema.json`、`quote-draft.schema.json`。

## 输出纪律

- `Inquiry`：结构化字段 + 原文引用；未知标 unknown，不虚构。
- `QuoteDraft`：含计算器版本、分项与合计；`recommended_action` 仅为 `ready_for_human_review` 或 `await_inputs`。
- 拒绝 `task-provided:` 占位 locator。价格进入外联草稿前须有证据或计算器输出，并可用 `chem-sales-quality-check`。

详见 `references/inquiry-to-quote-discipline.md`。
