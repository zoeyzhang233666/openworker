# ChemClaw 化工多平台内容重构 — 可粘贴交接

> **选用结论（2026-08-10）**：相对「冯冯形五 Skill 洗稿草图」，采用 **Plan B「内容重构」规格**。  
> **本文件** = Plan B 正文收紧为可粘贴指令 + **M1 硬分期**（EXE / 全量语料 / 词表升级框架 **不是** 第一期 blocker）。  
> **正式实施计划**：[../superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md](../superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md)  
> **状态**：**M1+M2 已落地（D-104 / D-107）**。粘贴块仍可用于新对话对齐约束。M3 待点名且确认打安装包。

## 如何使用

1. 仅在 `chemclaw-clean` worktree / 对话中开 Agent；**不要**在 `fengfeng-lobster` 实现。
2. 用户点名授权后，把下方「可粘贴交接指令」整段贴给 ChemClaw Cursor。
3. 同时尽量附上：脱敏化工样例、规避词初稿、平台优先级；缺样例时 M1 可用 3～5 条合成夹具。
4. 默认：新建独立 Persona；**不改** `DEFAULT_PERSONA_ID`；新 Agent **默认禁用**；用户在智能体页启用。

## 对比摘要（为何不用 Plan A 做规格）

| | Plan A（洗稿草图） | Plan B（本交接） |
|---|---|---|
| 叙事 | 多平台洗稿 | 事实保持 + 独立表达 + 平台适配 + 合规质检 |
| Skill | 含独立 `platform-classifier` | 平台下沉 Persona；4 核心 + 可选 hook |
| 事实 | 语境抽取 | `RewriteBrief` 结构化合同 |
| 质检 | 偏 LLM 自检 | 确定性脚本 + gate（对标销售质量门禁） |
| 工程 | 点到 seed/打包 | M1 源码可验；打包/词表升级进 M3 |

---

## 可粘贴交接指令（复制给 ChemClaw Cursor）

将下面 `text` 代码块整段复制：

```text
你在 ChemClaw / OpenWorker 的 chemclaw-clean worktree 工作。
工作目录：D:\OpenWorker\openworker\.worktrees\chemclaw-clean

不要改、不要引用、不要合并 d:\小红书提示词\fengfeng-lobster（另一产品「冯冯的龙虾」金融线）。
不要把金融涂-委婉 Skill 原样拷进 ChemClaw。不要改 ChemClaw 品牌或 DEFAULT_PERSONA_ID。

先阅读：AGENTS.md、docs/chemclaw/README.md、docs/chemclaw/DECISIONS.md、docs/chemclaw/DOMAIN.md、
docs/chemclaw/HANDOFF_PLATFORM_REWRITE.md、
docs/superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md。
采用外贸/转化龙虾包工程形状（Persona 编排 + schemas/scripts + 确定性质检），不要做成五个空壳 SKILL.md 的 Prompt Demo。

【产品定位】
内部目标是「事实保持 + 独立表达 + 平台适配 + 合规质检」，不要只写成「洗稿」。
不要把目标定义为绕过平台原创/风控检测。

Persona：
- id: platform-rewrite-lobster
- 显示名：化工内容重构龙虾
- family: knowledge
- tools: [files, search, shell, todo]
- messaging: false
- connectors: false
- default_permission_mode: interactive
- 默认禁用；不改 DEFAULT_PERSONA_ID（仍为 cowork）
- 不要写 Markdown manifest 不存在的 default_surfaced 字段

Skills（M1 四核心；M2 才做 hook）：
1. chem-rewrite-brief — 产出结构化 RewriteBrief（事实合同）
2. chem-platform-rewrite — 按平台重构表达，不新增事实，不做最终 pass
3. chem-content-policy — 营销/平台/化工安全词表 + scripts/scan_content.py
4. chem-content-quality-check — scripts/check_content.py；确定性扫描 + 语义质检
可选（M2）：chem-hook-cta-pack — 仅用户要标题/封面/钩子/CTA 时 load_skill

平台识别：用户明确说「改成小红书」等时由 Persona 设 target_platform，不要单独 heavyweight platform-classifier Skill。
平台不明时 ask_user 或给推荐。

第一期平台：xiaohongshu / douyin / x。预留视频号/公众号/LinkedIn/Facebook，M1 不实现。

【事实边界 — 硬约束】
用户仅要求改写时：不得主动联网补产品事实；不得新增原文没有的 CAS/纯度/规格/认证/检测/安全结论/客户案例/价格/交期/市场排名/「第一」类表述。
immutable_facts 只能保持；未知进 unknown_fields；常识不得填进 immutable_facts；冲突须标记，不得自行择一。
用户明确要求查证/补充/联网时才可搜索；外部事实必须与用户原始事实分开标注。

【RewriteBrief 最小字段（M1）】
target_platform, content_type, language, audience, communication_goal,
immutable_facts（至少：product_name, cas, grade, purity, packaging, application_facts, numeric_claims, certifications）,
claims_allowed, claims_needing_evidence, prohibited_inferences, unknown_fields,
must_keep, must_remove, user_forbidden_terms（可空）。
完整 YAML 字段可在 schema 注释预留，M1 不必一次填满。

【平台交付格式】
小红书：【标题】【封面字】【正文】【标签】【改写说明】
抖音：【口播稿】【画面提示】【话题】【改写说明】
X：【帖文】【线程拆分可选】【Hashtags】【改写说明】
默认不发帖、不登录平台。gate 仅可到 ready_for_publish_review（人工审阅），不是已发布。

【Policy / Gate】
lexicon 字段至少：rule_id, term, platform, locale, category, severity(info|warning|block), action(keep|review|rewrite|remove|block), replacement_strategy, notes。
区分平台经验规则 vs 法律/监管口径，不要一律叫「违规」。
quality gate 输出 verdict: pass | revise | blocked；仅 pass 才允许 ready_for_publish_review。
独立表达检测要保守：事实/规格行允许高重叠；惩罚长连续营销句雷同；禁止为降重改数字/CAS。

【流水线】
专项改写按序 load_skill：chem-rewrite-brief → chem-platform-rewrite → chem-content-policy → chem-content-quality-check。
revise → 回到 chem-platform-rewrite。Skill 缺失须披露，不得假装已过门禁。

【路径】
Persona: coworker/personas/builtin/platform-rewrite-lobster.md
Skills: coworker/skills/bundled/<name>/{SKILL.md,references/,schemas/,scripts/}
seed_bundled_skills 须能种出；已存在同名目录不自动升级（已知陷阱，M3 再做 managed rules + user override）。

【M1 范围 — 硬分期；超出即超范围】
做：四核心 Skill + Persona + 最小 schema + scan/check 脚本 + 小型 base.csv + 三平台 references + pytest（注册、默认仍 cowork、禁词命中、事实字段不变）+ docs/chemclaw/platform-rewrite/ 短文 README。
不做（本轮禁止）：chem-hook-cta-pack；10～20 条全量业务语料（无业务样例时用 3～5 合成夹具即可）；词表升级框架；wheel/PyInstaller/桌面包验收；改默认智能体；自动发帖/登录；大改品牌。

【M2 / M3 — 仅当用户点名】
M2：hook-cta-pack；业务 regression corpus；resources_path / 只读 root 专项集成测。
M3：bundled managed rules + user override + rule_version；安装包内 load_skill 验收（须用户确认打安装包）。

【验收（M1）】
1. 化工样例 → 小红书四段式（含改写说明）；敏感词被扫/改。
2. 同素材 → 抖音口播与 X 短帖语气明显不同（非同文换壳）。
3. 注入「国家级/第一/包过/绝对安全/100%无风险」→ scanner 命中且 gate != pass。
4. 原文无 CAS/认证/案例等 → 输出不得新增。
5. 现有龙虾未被误删；默认仍是 cowork。

【实施顺序】
1. 先 brainstorming/plan 输出：Persona 大纲、Skill 文件树、RewriteBrief/gate 最小 schema、lexicon 字段、M1 文件清单。
2. 用户确认设计后再写文件；TDD：先写 pytest 再实现。
3. 一次只做本产品线 M1；保护 dirty worktree，禁止 git add .；不提交除非用户要求。
4. 收口时更新 docs/chemclaw/README.md 与 DECISIONS（新 D-xxx，仅在用户已授权实现时）。

若用户尚未显式授权实现「化工内容重构内置能力包」，先只输出设计确认清单，不要写 Persona/Skill 代码。
```

---

## 业务侧附件（开发前尽量准备）

- 10～20 条真实/脱敏样例（好坏都要）；没有则 M1 用合成夹具。
- 规避词 Excel：原词 → 替代表述 → 平台 → 类型 → 严重度。
- 平台优先级（默认：小红书 > 抖音 > X）。
- 可选：品牌口径规范。

## 明确不做（全里程碑）

- 自动登录/发帖/评论/私信/批量仿写竞品。
- 「绕原创检测」产品化。
- 复制 `fengfeng-lobster` 金融 Skill。
- 修改 `DEFAULT_PERSONA_ID` / 大范围品牌改造。
