# ChemClaw HubSpot 字段更新 / 任务创建审批 CTA（D-127）

**Goal:** 对话内人工触发 HubSpot 字段更新与跟进任务创建；复用连接器审批卡；与笔记（D-105）/ 创建联系人（D-109）门禁并列。

**Architecture:**
- 复用 `hubspot_update_object` / `hubspot_create_task`（EXTERNAL / `requires_approval`）
- GUI：`ready_for_crm_update_object` →「提交 CRM 字段更新审批」；`ready_for_crm_create_task` →「提交 CRM 任务创建审批」
- Skill/龙虾：可靠对象 ID / 已确认跟进动作 + 门禁 + CTA 后才可调用；不扩任务关联 API

**Status (2026-08-12):** 已完成（D-127）。

## Tasks

- [x] `requestCrmUpdateObject` / `requestCrmCreateTask` + Transcript/App/i18n + vitest
- [x] 转化龙虾 / chem-sales-engagement / quality 接线 + wire 单测
- [x] D-127 / README / DOMAIN / GATE / 规格 / defer

## Out of Scope

- Close、买联系人、`create_company`、清单页 CRM、自动写
- 扩展 `hubspot_create_task` 关联到联系人/公司（已知联系人写入 `notes`）
