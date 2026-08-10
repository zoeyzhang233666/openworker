---
name: chem-sales-engagement
description: "Use when 用户要对已核验化工 Lead/商机产出联系策略、开发信/消息草稿与跟进计划，且发送须人工审批。"
---

# 销售接触编排

把一次销售转化任务组织为可恢复的 `EngagementRun`：联系策略 → 草稿 → 质量门禁 →（可选）人工触发发送审批 / CRM 笔记写入审批 / 创建联系人审批。草稿不等于发送；本 Skill **不**自动外发、**不**自动写 CRM、不购买联系人。

## 输入与边界

- 输入：已核验 Lead 或 Opportunity ID、目标市场/语言、渠道偏好、SKU 或品名约束、已知联系事实（可为空）。
- 依次加载 `chem-product-intelligence`（SKU 事实）与 `chem-sales-quality-check`（确定性门禁）。
- 无可靠个人邮箱/手机时，只输出**岗位策略**与待补证项；禁止编造邮箱、微信或电话。
- 禁止编造价格、交期、认证、已寄样、已发送或已成交等事实。
- 默认只读；外发须用户明确要求后调用连接器 `email_send`，并走现有审批。
- CRM：`ready_for_crm_write` +「提交 CRM 写入审批」→ 仅 `hubspot_log_note`；`ready_for_crm_create_contact` +「提交创建联系人审批」→ 仅 `hubspot_create_contact`（email 须已核验，禁止编造）。**禁止**主动调用 `hubspot_update_object` / `hubspot_create_task`；禁止无门禁/无 CTA 调用写工具；付费调用仍须审批。

## 状态机

维护 `input → strategy → draft → quality_gate → complete|blocked`。按 `schemas/engagement-run.schema.json` 记录版本、阶段、草稿/计划 ID、门禁结果、失败与下一步。

## 输出纪律

- `OutreachDraft`：可空 `recipient_email`；必须有 `recipient_role`；价格/交期声明须有证据 ID。
- `FollowupPlan`：节拍 + 停止条件 + 人工确认点；不得假设邮件已发出。
- 质量门禁未 `pass` 时不得建议 `ready_for_human_send` / `ready_for_crm_write` / `ready_for_crm_create_contact`，也不得调用 `email_send` / `hubspot_log_note` / `hubspot_create_contact`。
- 仅当 `ready_for_human_send` **且**用户明确要求发送 **且**有可靠 `to` 邮箱时，才可调用 `email_send`；未获审批不得宣称已发送。
- 仅当文案含 `ready_for_crm_write` **且**用户明确要求写入 CRM **且**已知可靠 HubSpot 对象类型与 ID 时，才可调用 `hubspot_log_note`；未获审批不得宣称已写入；HubSpot 未连接时披露中文错误并引导「连接」。
- 仅当文案含 `ready_for_crm_create_contact` **且**用户明确要求创建（含「提交创建联系人审批」CTA）**且**有可靠 email 时，才可调用 `hubspot_create_contact`；未获审批不得宣称已创建；禁止编造邮箱/姓名。
- 拒绝 `task-provided:` / `unknown:` / `placeholder:` 占位 locator。

详见 `references/engagement-discipline.md`。
