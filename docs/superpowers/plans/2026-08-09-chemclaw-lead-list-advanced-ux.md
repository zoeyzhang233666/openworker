# ChemClaw 客户清单进阶 UX（D-102）

**Goal:** 清单工作台增加证据详情、继续补查、ICP 重评意图注入与断点只读提示；仍无 CRM/发送按钮。

**Architecture:**
- GUI `LeadsWorkbench` 行展开；`requestLeadFollowup.ts` 注入对话意图（对齐 send-approval 模式）
- 导入保留 `run_id` / `stage` / `budget`；无则隐藏断点条
- 不自动重跑拓客；不静默改分

**Status (2026-08-09):** 已完成（D-102）。

## Tasks
- [x] requestLeadFollowup + 单测
- [x] LeadsWorkbench 展开 / 补查 / 重评 / 断点条
- [x] App 监听 + i18n
- [x] D-102 / README / 规格

## Out of Scope
- Comtrade、SMTP 重做、买联系人、自动 ProspectingRun
