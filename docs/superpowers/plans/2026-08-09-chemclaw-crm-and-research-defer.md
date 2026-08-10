# ChemClaw CRM / 买联系人 / 化工社科研 — 远期队列

> HubSpot **笔记写入（D-105）**与**创建联系人（D-109）**审批 CTA 已交付；**合集单包 `uncertainty-and-units`（D-111）已试点**；**合集 Triage（D-112）已落盘**，P0/P1 待用户确认后再逐包实现；其余 CRM/买联系人/化工社批量仍须点名。

## CRM / 买联系人 / 多渠道外发

- **已交付（D-105）**：对话内 `ready_for_crm_write` → `hubspot_log_note` + 审批卡；清单页仍无 CRM 按钮；不自动写。
- **已交付（D-109）**：对话内 `ready_for_crm_create_contact` → `hubspot_create_contact` + 审批卡。
- 仍未做：字段更新 / 任务创建的产品 CTA；Close 等其他 CRM；买联系人；多渠道外发
- 任一新增真实 CRM 写入面或购买联系人必须：独立决策 + `requires_approval` + 中文审批文案
- 复用现有 connectors 优先于自研

## 阶段 6：化工社 / 科研（D-090）

- 本地目录 `D:\化工社skills合集` 仅作候选库
- **已试点（D-111）**：`uncertainty-and-units` → bundled；可选询盘/转化接线；计划见 `2026-08-10-chemclaw-uncertainty-and-units.md`
- **Triage（D-112）**：158 包分流表 [`docs/chemclaw/HUAGONGSHE_SKILL_TRIAGE.md`](../../chemclaw/HUAGONGSHE_SKILL_TRIAGE.md)；确认前不批量实现
- **逐包**审核其余候选：价值、上游版本、许可证、脚本/网络、依赖、兼容性、中文化、权限、测试、回退
- 不批量复制；不引入 RDKit/Datamol/TimesFM 等重型依赖到核心销售首包
- 科研能力服务销售判断，不主导导航与默认 Agent

## 开工条件

用户明确点名「CRM：…」（扩展写入面）或「审核某化工社 Skill：&lt;id&gt;」后再写独立小计划与代码。
