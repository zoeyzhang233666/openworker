# ChemClaw HubSpot 创建联系人审批（D-109）

**Goal:** 对话内人工触发 HubSpot 新建联系人；复用连接器审批卡；与笔记写入（D-105）门禁并列。

**Architecture:**
- 复用 `hubspot_create_contact`（EXTERNAL / `requires_approval`）
- GUI：`ready_for_crm_create_contact` →「提交创建联系人审批」→ 注入意图
- Skill/龙虾：可靠 email + 门禁 + CTA 后才可调用；仍禁 update/task 产品 CTA

**Status (2026-08-10):** 已完成（D-109）。

## Tasks

- [x] `requestCrmCreateContact` + Transcript/App/i18n + vitest
- [x] 转化龙虾 / chem-sales-engagement / quality 接线 + wire 单测
- [x] D-109 / README / DOMAIN / GATE / 规格 / defer

## Out of Scope

- `hubspot_update_object` / `hubspot_create_task` / `create_company` 产品 CTA
- Close、买联系人、清单页 CRM、自动写
