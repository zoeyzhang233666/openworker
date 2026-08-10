# ChemClaw HubSpot CRM 审批写入（D-105）

**Goal:** 对话内人工触发 HubSpot 跟进笔记写入；复用连接器审批卡；清单页无 CRM 按钮。

**Architecture:**
- 复用 `hubspot_log_note`（EXTERNAL / `requires_approval`）
- GUI：`ready_for_crm_write` →「提交 CRM 写入审批」→ 注入意图（镜像 D-099）
- 未连接中文错误；Skill/龙虾纪律禁止自动写与 create_contact 等首包路径

**Status (2026-08-10):** 已完成（D-105）。

## Tasks
- [x] HubSpot 未连接等运行时错误中文化 + pytest
- [x] `requestCrmWriteApproval` + Transcript/App/i18n + 单测
- [x] 转化龙虾 / chem-sales-engagement / quality 接线
- [x] D-105 / README / GATE / 规格 / defer

## Out of Scope
- Close、买联系人、`create_company`、清单页 CRM 按钮、自动写、SAM/海关
