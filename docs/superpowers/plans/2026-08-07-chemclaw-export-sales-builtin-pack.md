# ChemClaw 外贸拓客内置能力包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:dispatching-parallel-agents to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一个可在 ChemClaw 中发现和启用的 `export-sales-lobster` 内置智能体，以及五个有真实合同、规则和确定性脚本的外贸拓客内置 Skill。

**Architecture:** 继续使用现有 markdown persona 与 bundled Skill 的发现/首启复制机制，不新增第二套注册表。Agent 只编排；五个 Skill 分别承担总流程、产品情报、客户发现、企业核验和确定性排名；外部 API 仍留在未来 Provider 层。

**Tech Stack:** Python 3.10+、pytest、YAML frontmatter、Markdown、JSON Schema、Python 标准库。

**Status (2026-08-07 closeout):** 已完成并收口（D-091）。GUI 需重启 sidecar 后可见；新 Agent 默认禁用。

## Global Constraints

- 默认简体中文；正常产品文案只显示 ChemClaw。
- 不改变 `cowork` 默认智能体，不自动启用或设为默认。
- 不新增外部依赖、不接真实 API、不写真实外部数据。
- 不猜测企业、联系人、邮箱、采购量或分数。
- 所有发送和外部写入继续经过现有权限/审批。
- `Lead Fit Score` 六项上限固定为 30/20/20/10/10/10；`Evidence Confidence` 独立计算。
- Skill 附属 `references/`、`schemas/`、`scripts/` 必须被 bootstrap 完整复制。
- 保护当前 dirty worktree，只暂存本计划明确列出的路径。

---

### Task 1: 五个 bundled Skill 与真实附属资产

**Files:**
- Create: `tests/test_export_sales_skills.py`
- Create: `coworker/skills/bundled/chem-export-prospecting/**`
- Create: `coworker/skills/bundled/chem-product-intelligence/**`
- Create: `coworker/skills/bundled/chem-buyer-discovery/**`
- Create: `coworker/skills/bundled/chem-company-qualification/**`
- Create: `coworker/skills/bundled/chem-lead-ranking/**`

**Interfaces:**
- Produces Skill IDs: `chem-export-prospecting`, `chem-product-intelligence`, `chem-buyer-discovery`, `chem-company-qualification`, `chem-lead-ranking`.
- Produces executable functions: `normalize_cas(value: str) -> str`, `is_valid_cas(value: str) -> bool`, `score_lead(payload: dict) -> dict`.

- [x] Write tests that require all five Skill IDs, non-empty descriptions, the approved supporting asset paths, byte-identical bootstrap copies, and SkillLoader discovery.
- [x] Run RED then GREEN for Skill package presence (historical; packages now present).
- [x] Add the five `SKILL.md` files, focused reference documents and strict JSON Schemas. Add standard-library CAS validation and lead-scoring scripts.
- [x] Test CAS normalization/checksum, fixed score totals, confidence separation, unknown-field behavior, threshold decisions and malformed input.
- [x] Run Skill + ranking tests green.

### Task 2: `export-sales-lobster` 内置智能体

**Files:**
- Create: `tests/test_export_sales_lobster.py`
- Create: `coworker/personas/builtin/export-sales-lobster.md`

**Interfaces:**
- Consumes the five stable Skill IDs from Task 1.
- Produces persona ID `export-sales-lobster` with `family: knowledge`, interactive permissions and the existing files/search/shell/todo capabilities.

- [x] Write tests for manifest identity, Chinese product copy, exact five default Skill IDs, registry discovery, builtin status, non-default status and mandatory evidence/permission instructions.
- [x] Run RED then GREEN for persona presence (historical).
- [x] Add the manifest and system prompt. Require sequential loading of the five Skills, structured `ProspectingRun`, evidence-linked conclusions, partial-result disclosure and explicit approval for sending/writes.
- [x] Persona + permission tests green；默认 `enabled=false`，不改变 `cowork` 默认。

### Task 3: 集成回归与项目状态

**Files:**
- Modify: `docs/chemclaw/README.md`
- Modify: `docs/chemclaw/DECISIONS.md`（D-091）
- Modify: sales spec status / §18；本计划勾选

- [x] Closeout regression（2026-08-07）：`pytest` 外贸相关套件 **139 passed, 1 skipped**（含 bootstrap/store/skills/persona + export pack）；GUI i18n 相关 **23 passed**。
- [x] Schema `Draft202012Validator.check_schema` + JSON 解析；`quick_validate.py` 在 `PYTHONUTF8=1` 下五 Skill 均 valid；CAS/ranking CLI 以 `load_skill` 绝对路径、无关 cwd 可执行。
- [x] 前向场景：仅口述德国分销商/苯甲酸钠/近一年进口、无企业标识 → `NeedsReview` / `research_first`，不得 Qualified。
- [x] 独立审查 Critical 已修：拒绝 `task-provided:` / `unknown:` / `placeholder:` 占位 locator（脚本 + 两侧 Schema）。
- [x] 更新 README / D-091 / 规格状态；不宣称 API/Provider、邮件、CRM 或专属工作台已完成。
- [x] 审查确认：无权限绕过；`skill_dirs` 真实接线；未干扰无关 dirty 文件。

## Closeout deviations / residual

- Windows 默认代码页下 `quick_validate.py` 需 `PYTHONUTF8=1`（上游脚本未显式 UTF-8）。
- `seed_bundled_skills` 不升级已存在同名目录；收口时已手工同步 state 中 ranking/qualification 合同文件。
- CompanyEvidencePack Schema 的 Qualified 门禁仍弱于 `score_lead`；以脚本为权威（记入 D-091）。
- worktree 内若干 `.test-tmp-chem-lead-ranking-*` / `.tmp/pytest-export-sales-*` 因 `openworker-server` 占用无法删除；无 `__pycache__` 残留于五 Skill；勿用 `git clean`。

## Out of Scope

- PubChem/GLEIF/Comtrade/TED/SAM/SEC/USAspending Provider implementation
- 自动邮件发送、CRM 写入、联系人购买或抓取
- Skill manifest/版本/依赖安装器重构
- 外贸工作台新页面
- 内贸拓客与商机雷达 Agent
