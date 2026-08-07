# ChemClaw 内贸拓客内置能力包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付可在 ChemClaw「智能体」页发现并启用的「内贸拓客龙虾」，把「具体化工 SKU + 国内市场/园区/行业约束」变成有证据、可继续处理的国内客户清单。

**Architecture:** 与外贸包同构——1 Agent 编排 + 1 国内主 Skill 状态机 + 复用四个已收口能力 Skill。国内差异写在主 Skill 的 references/schema 约束里；不新建第二套评分脚本，不接真实国内 API。

**Tech Stack:** Python 3.10+、pytest、YAML frontmatter、Markdown、JSON Schema、现有 SessionManager `skill_dirs`。

**Status (2026-08-07 closeout):** 已完成并收口（D-092）。GUI 需重启 sidecar 后可见；新 Agent 默认禁用。

## Global Constraints

- 产品文案只显示 ChemClaw；默认语言简体中文。
- 默认智能体仍为 `cowork`；`domestic-sales-lobster` 默认禁用。
- 不接付费/工商/海关 Provider；不写 CRM；不自动发邮件/短信。
- 不猜测企业名、信用代码、联系人手机/微信、采购量或分数。
- 权限与审批不变；发送/外部写入须审批。
- 复用 `chem-lead-fit@1.0.0` 与占位 locator 拒绝逻辑；不复制 `score_lead.py`。
- 不批量内置化工社 Skills；不把 `chem-newbiz-lead` 挂为默认 Skill。
- 保护 dirty worktree；只改本计划路径。

---

### Task 1: `chem-domestic-prospecting` + 合同测试

**Files:**
- Create: `coworker/skills/bundled/chem-domestic-prospecting/**`
- Create: `tests/test_domestic_sales_skills.py`

- [x] Write package/bootstrap/schema tests.
- [x] Add SKILL.md、references、prospecting-run schema（复用 `chemclaw.prospecting-run.v1` 合同）。
- [x] GREEN + `PYTHONUTF8=1` quick_validate。

### Task 2: `domestic-sales-lobster` + 权限/发现测试

**Files:**
- Create: `coworker/personas/builtin/domestic-sales-lobster.md`
- Create: `tests/test_domestic_sales_lobster.py`
- Modify: `surfaces/gui/src/components/PersonasTab.tsx`、`surfaces/gui/src/i18n.tsx`
- Create: `surfaces/gui/src/domesticSalesPersonaI18n.test.ts`

- [x] Persona tests + manifest + i18n；默认禁用。
- [x] GREEN：interactive 读允许，写/shell/CRM 需审批。

### Task 3: 集成、前向场景、治理收口

**Files:**
- Create: `tests/test_domestic_sales_pack_integration.py`
- Modify: `docs/chemclaw/README.md`、`DECISIONS.md`（D-092）、销售规格 §17.5/§18、本计划勾选

- [x] SessionManager custom data_dir `load_skill` 五个全成功。
- [x] 口述前向：江苏园区/苯甲酸钠/食品添加剂下游 → NeedsReview，禁占位 locator。
- [x] 回归：**152 passed, 1 skipped**；GUI i18n **24 passed**；不宣称国内 API/商机雷达已完成。

## Out of Scope

- 商机雷达 / `OpportunitySignal`
- 国内工商/海关 Provider
- 专属工作台 / SessionIntro 空态卡
- 自动启用或设为默认智能体
