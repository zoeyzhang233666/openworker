# ChemClaw 商机雷达内置能力包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 交付可启用的「商机雷达龙虾」，把「SKU/市场约束 + 有来源事件」整理为可跟进的 `Opportunity` 清单。

**Architecture:** Agent 编排；`chem-opportunity-radar` 状态机；`chem-opportunity-scoring` 确定性评分；复用 product-intelligence 与 company-qualification。本轮不接 Provider、不默认挂 MCP 询盘/新设 Skill。

**Tech Stack:** markdown persona、bundled Skill、JSON Schema、pytest、标准库 Python。

**Status (2026-08-07 closeout):** 已完成并收口（D-093）。GUI 需重启 sidecar 后可见；新 Agent 默认禁用。

## Global Constraints

- 默认 `cowork`；`opportunity-radar-lobster` 默认禁用。
- 无外部 API/CRM/自动外发；占位 locator 拒绝。
- 保护 dirty worktree。

---

### Task 1: `chem-opportunity-scoring`

- [x] Schemas + `score_opportunity.py` + tests（`chem-opportunity-fit@1.0.0`，25/20/25/15/15）

### Task 2: `chem-opportunity-radar`

- [x] 主 Skill + run/signal 合同 + tests

### Task 3: Agent + 集成 + 治理

- [x] Persona、i18n、集成/前向、D-093、README、规格
- [x] 回归：**172 passed, 1 skipped**；GUI i18n **24 passed**

## Out of Scope

- TED/SAM/Comtrade/海关 Provider
- 默认挂载 chem-newbiz-lead / chem-inquiry-feed
- 专属工作台 UI
