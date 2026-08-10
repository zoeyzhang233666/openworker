# ChemClaw 化工多平台内容重构内置能力包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.  
> **规格来源：** Plan B「化工多平台内容重构」交接；相对 Plan A「洗稿草图」的选用结论见 [docs/chemclaw/HANDOFF_PLATFORM_REWRITE.md](../../chemclaw/HANDOFF_PLATFORM_REWRITE.md)。  
> **Status (2026-08-10):** **M1 已落地（D-104）**。M2/M3 待用户点名。

**Goal:** 交付可发现、默认可禁用的内置智能体「化工内容重构龙虾」（`platform-rewrite-lobster`）与四核心 bundled Skill，将化工/精细化工/贸易素材重构为小红书 / 抖音 / X 成稿，并保证事实不乱编、平台风格可区分、敏感表达可确定性扫描、门禁可回归。

**Architecture:** Persona 编排 + progressive disclosure Skills；`RewriteBrief` 为事实合同；`chem-content-policy` / `chem-content-quality-check` 用标准库脚本做确定性扫描；对标 [`chem-sales-quality-check`](../../../coworker/skills/bundled/chem-sales-quality-check/SKILL.md) 与外贸龙虾包形状。不新增第二套注册表；不自动发帖。

**Tech Stack:** Python 3.10+、pytest、YAML frontmatter、Markdown、JSON Schema、Python 标准库（CSV/字符串相似度，无重型 NLP 依赖）。

---

## Global Constraints

- 默认简体中文；正常产品文案只显示 ChemClaw。
- 不改变 `cowork` / `DEFAULT_PERSONA_ID`；新 Agent **默认禁用**（registry：无 state 时仅 default 启用）。
- 产品叙事用「内容重构 / 平台适配」，不用「绕原创检测」。
- 用户仅要求改写时：**不主动联网补事实**；禁止新增原文没有的 CAS/纯度/认证/检测/安全结论/案例/价格/交期/排名类表述。
- 草稿 ≠ 发布；无自动登录/发帖；gate 最高到 `ready_for_publish_review`。
- `seed_bundled_skills` 对已存在同名目录不升级（已知；词表升级属 M3）。
- Markdown persona **不要**写不存在的 `default_surfaced` 字段。
- 保护 dirty worktree；禁止 `git add .`；不提交除非用户要求。
- **一次只做当前里程碑**；M2/M3 须用户点名。

---

## 里程碑

| 里程碑 | 内容 | Blocker? |
|--------|------|----------|
| **M1** | Persona + 四核心 Skill + 最小 schema/脚本/词表 + pytest + 短文档 | 授权后的首期交付 |
| **M2** | `chem-hook-cta-pack`；业务语料 10～20（或点名）；resources 只读 root 集成测 | 否，点名后做 |
| **M3** | managed rules + user override + `rule_version`；wheel/PyInstaller 产物 `load_skill` | 否；打安装包须用户确认 |

---

## M1 Tasks（授权后执行）

### Task 1: 四核心 bundled Skill + 最小附属资产

**Files:**

- Create: `coworker/skills/bundled/chem-rewrite-brief/**`
- Create: `coworker/skills/bundled/chem-platform-rewrite/**`
- Create: `coworker/skills/bundled/chem-content-policy/**`
- Create: `coworker/skills/bundled/chem-content-quality-check/**`
- Create: `tests/test_platform_rewrite_skills.py`

**Interfaces:**

- Skill IDs: `chem-rewrite-brief`, `chem-platform-rewrite`, `chem-content-policy`, `chem-content-quality-check`
- Schemas: `rewrite-brief.schema.json`（最小字段集）, `rewrite-output.schema.json`, `content-gate-output.schema.json`
- Scripts: `scan_content.py`, `check_content.py`（标准库；经 `resources_path` 调用）
- Lexicon: `references/lexicon/base.csv`（小型；含 severity/action）
- Platforms: `references/platforms/{xiaohongshu,douyin,x}.md`

**RewriteBrief 最小字段:**

`target_platform`, `content_type`, `language`, `audience`, `communication_goal`, `immutable_facts`（product_name / cas / grade / purity / packaging / application_facts / numeric_claims / certifications）, `claims_allowed`, `claims_needing_evidence`, `prohibited_inferences`, `unknown_fields`, `must_keep`, `must_remove`, `user_forbidden_terms`

**Gate 输出:**

`verdict: pass | revise | blocked`；维度含 fact_integrity / policy_scan / platform_fit / independent_expression（独立表达阈值保守：规格行允许重叠）。

- [x] 写 RED 测试：四 Skill 存在、description 非空、bootstrap 可复制 references/schemas/scripts、scanner 命中禁词、事实字段不变夹具
- [x] 实现四 Skill 目录与脚本；GREEN
- [x] 3～5 条合成 regression 夹具（无业务样例时）

### Task 2: Persona `platform-rewrite-lobster`

**Files:**

- Create: `coworker/personas/builtin/platform-rewrite-lobster.md`
- Create: `tests/test_platform_rewrite_lobster.py`

**Frontmatter 要点:**

```yaml
id: platform-rewrite-lobster
name: 化工内容重构龙虾
family: knowledge
tools: [files, search, shell, todo]
messaging: false
connectors: false
default_permission_mode: interactive
skills:
  - chem-rewrite-brief
  - chem-platform-rewrite
  - chem-content-policy
  - chem-content-quality-check
```

系统提示：按序 `load_skill`；平台下沉 Persona；禁止编造/发帖；默认不搜索补事实；Skill 缺失须披露。

- [x] RED：注册、family、skills 列表、默认仍 `cowork`、非默认启用
- [x] GREEN：persona md + 测试
- [x] 空态推荐三问偏化工小红书/抖音口播/合规过稿（若需 i18n 映射则最小补丁）

### Task 3: 文档与治理收口（M1）

**Files:**

- Create: `docs/chemclaw/platform-rewrite/README.md`（短文：定位、流水线、边界、不自动发布）
- Update: `docs/chemclaw/README.md`、`docs/chemclaw/DECISIONS.md`（**仅授权实现后**追加 D-xxx）

- [x] 短文 README
- [x] 集成测：`seed_bundled_skills` 含四 Skill；persona 可 load（可与销售包集成测同型）
- [x] 授权实现收口：追加决策、勾选本计划 checkbox、更新控制台状态

---

## M2 Tasks（点名后）

- [ ] `chem-hook-cta-pack`（按需 load；可挂 persona `skills:` 但提示写清非每次加载）
- [ ] 业务 10～20 条 corpus + `REGRESSION_CORPUS.md`
- [x] knowledge session：`load_skill` → `resources_path` → `read_file` / 脚本；若 Path escapes → skills 目录只读 root（不放宽全盘）

---

## M3 Tasks（点名 + 确认打安装包后）

- [ ] bundled managed rules + user override；官方升级不覆盖用户词表；`rule_version`
- [ ] package-data / PyInstaller 核对 `SKILL.md` + references/schemas/scripts
- [ ] 构建产物内真实 `load_skill` 验收

---

## Out of Scope（全里程碑默认）

- 自动登录/发帖/评论/私信/批量竞品仿写
- 复制 `fengfeng-lobster` 金融 Skill
- 独立 heavyweight `platform-classifier` Skill
- 修改默认智能体或大范围品牌改造
- 销售主线 / CRM / 化工社批量内置（并行任务勿混进本 PR）

---

## 验收标准（M1）

1. 化工样例 → 小红书【标题/封面字/正文/标签/改写说明】；禁词被处理。
2. 同素材 → 抖音口播 vs X 短帖语气明显不同。
3. 注入「国家级/第一/包过/绝对安全/100%无风险」→ scanner 命中且 `verdict != pass`。
4. 原文无 CAS/认证/案例 → 输出不新增。
5. 默认智能体仍为 `cowork`；其它龙虾未被误删。

完成定义：**能改、能区分平台、不乱编、能扫风险、能自动 gate、能 pytest 回归**（M1）；打包与规则热升级属 M3，不以「看起来写得不错」代替。

---

## 授权门禁

实现前须用户明确说类似：

> 授权实现化工内容重构内置能力包（M1）

然后追加 DECISIONS `D-xxx`，再按 Task 1→2→3 执行。仅有本计划落盘 **不等于** 批准实现。
