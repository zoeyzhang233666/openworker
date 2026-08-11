---
name: chem-opportunity-radar
description: "Use when 用户要围绕化工 SKU 与市场约束，把有来源的询盘/招标/扩产等事件整理为可跟进商机清单。"
---

# 商机雷达编排

把一次商机发现任务组织为可恢复的 `OpportunityRadarRun`，而不是客户拓客名单或研究报告。仅在 SKU/市场约束足够明确，且至少有一条可回溯事件来源（文件、URL、登记号）或用户确认进入补证流程后继续。

## 输入与边界

- 输入：SKU 草稿或品名、市场/区域、关注的 `signal_type`、时间窗与排除条件。
- 依次加载 `chem-product-intelligence`、`chem-company-qualification`、`chem-opportunity-scoring`。
- 外部读取仅用已配置 Tool/Provider；**大陆默认**优先平台 Tool `search_tenders`（TED，免密钥）；美国联邦采购 `search_sam_opportunities`（SAM.gov）为**境外可选**，仅当已配置 `sam:default` 且用户明确需要时使用；欧盟 VAT 可用 `validate_eu_vat`；将返回的信号纳入 `signal_collect`；**不**在本 Skill 内嵌 TED/SAM/VAT 客户端。
- 本 Skill **不**默认调用 `chem-newbiz-lead` / `chem-inquiry-feed`（MCP 依赖未纳入本包）。
- 禁止把搜索摘要当作事件正文；无来源口述不得生成 `OpportunitySignal`，只能 `NeedsReview` 并请求补证。
- **禁止伪造** TED `publication-number` / SAM `noticeId` / `signal_id`；`search_tenders` / `search_sam_opportunities` 失败、empty 或未配置时披露并改走 TED/网页搜索，不得编造公告，也不要反复要求申请 SAM 密钥。
- 默认只读；发送/CRM/付费调用须审批。

## 状态机

维护 `input → signal_collect → normalize → score → complete|blocked`。按 `schemas/opportunity-radar-run.schema.json` 记录版本、阶段、预算、信号 ID、商机 ID、失败与下一步。无信号时以空清单 `complete`，不得伪造招标。

## 输出纪律

交付可跟进的 `Opportunity` 摘要：主体、信号、商机分、证据置信度、风险与 `recommended_action`。`NeedsReview`/`Watch` 不得包装为可立即外联。拒绝 `task-provided:*` 占位 locator。
