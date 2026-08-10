# ChemClaw → Cursor 接力说明（2026-08-07）

> **过时（2026-08-10）**：本文「尚未完成：外贸拓客收口」及「未接 Provider」清单已被后续提交否定。外贸/内贸/商机/转化首包与多数 Provider（D-091—D-112）已落地；内容重构 M1+M2（D-104/D-107）已落地。请以 [`README.md`](README.md)、[`DECISIONS.md`](DECISIONS.md)、[`GATE_VERIFY_2026-08-09.md`](GATE_VERIFY_2026-08-09.md) 与 `AGENTS.md` 当前门禁为准。下文仅作历史交接，**不要**再按「先收口外贸五 Skill」整表重做。

> 工作目录：`D:\OpenWorker\openworker\.worktrees\chemclaw-clean`  
> 分支：`chemclaw-clean`  
> 基线提交：`81b0b5c6e9c515594cd7664f334e76b7901fbac3`  
> 当前工作树：大量未提交改动，包含用户此前工作；严禁 reset、checkout 或覆盖不相关文件。

## 给 Cursor 的首条提示词

将下面整段复制给 Cursor Agent：

```text
你正在接手芯化和云 ChemClaw 的持续开发。唯一工作目录是：
D:\OpenWorker\openworker\.worktrees\chemclaw-clean

先不要写代码。请按顺序完整阅读：
1. AGENTS.md
2. docs/chemclaw/README.md
3. docs/superpowers/specs/2026-07-29-chemclaw-product-design.md
4. docs/chemclaw/DECISIONS.md
5. docs/chemclaw/DOMAIN.md
6. docs/superpowers/specs/2026-08-07-chemclaw-sales-growth-intelligence-design.md
7. docs/superpowers/plans/2026-08-07-chemclaw-export-sales-builtin-pack.md
8. docs/chemclaw/CURSOR_HANDOFF_2026-08-07.md

随后执行只读检查：git status --short、git diff --stat、git diff --check。不要依赖旧聊天恢复事实，不要 reset/checkout/clean，不要覆盖现有 dirty worktree，不要提交或合并 main，除非我明确授权。

当前用户目标不是继续空泛规划，而是把 ChemClaw 做成芯化和云用于外贸拓客、内贸拓客、商机发现和销售转化的实用产品。科研/报告能力只是辅助；化工社 Skills 只作锦上添花；Public APIs/API 客户端应进入 Tool/Provider 层，不能塞进 Skill。

当前第一条外贸拓客纵向链路已经基本实现：1 个内置 Agent + 5 个 bundled Skill。请先按本交接文件的“尚未完成”清单把这一个小任务严格收口，采用 TDD，先复现失败再修复，运行真实 SessionManager/CLI/Schema 测试，并做独立只读 code review。不要马上扩张到更多薄 Agent。

收口后再按已批准销售规格逐个小任务继续：优先内贸拓客纵向链路，其次商机雷达/OpportunitySignal；复用产品情报、企业核验和评分核心，不批量内置 D:\化工社skills合集，不自动发送邮件、不写真实 CRM、不购买数据、不绕过权限审批。

每次开始修改前先用中文汇报：当前状态、任务边界、验收标准、预计文件范围。每次只完成一个可独立验收的小任务。所有显示按钮必须真能工作；任何发送和外部写入必须继续走现有审批。
```

## 已经落盘的本任务成果

### 内置 Agent

- `coworker/personas/builtin/export-sales-lobster.md`
- ID：`export-sales-lobster`
- 中文名：外贸拓客龙虾
- 保持 `cowork` 为默认；按现有产品策略，新内置 Agent 默认禁用，用户可在“智能体”页启用。
- 按顺序挂载以下五个 Skill；提示词明确客户清单优先、证据追溯、部分失败披露、草稿/发送分离、禁止猜企业/联系人/邮箱/采购量、禁止绕过审批。

### 五个 bundled Skill

1. `coworker/skills/bundled/chem-export-prospecting/`
   - 可恢复、可审计 `ProspectingRun`
   - 记录输入、市场、版本、Provider、阶段、预算、检查点、失败和下一步
2. `coworker/skills/bundled/chem-product-intelligence/`
   - `CommercialSKU`、`ProductLanguageMap`、`ApplicationGraph`
   - 标准库 CAS 规范化/校验 CLI
3. `coworker/skills/bundled/chem-buyer-discovery/`
   - 多语言 `SearchRun`、查询轮次、学习来源、候选、实体关系、去重和停止统计
4. `coworker/skills/bundled/chem-company-qualification/`
   - `CompanyEvidencePack`、主体/角色/业务相关性/风险核验
   - 与 ranking 共用同结构 `source`/`EvidenceItem`
5. `coworker/skills/bundled/chem-lead-ranking/`
   - `scripts/score_lead.py`
   - 固定 `chem-lead-fit@1.0.0`
   - Lead Fit 六项 30/20/20/10/10/10；Evidence Confidence 独立计算
   - 等级/极性确定性映射，不接收模型自填百分比
   - 单来源、未决冲突、重大冲突有置信度上限
   - `Qualified` 要求 resolved 主体、正向主体/角色证据，以及“一条 A 或两条独立 B”的产品/应用相关性
   - 事件型证据缺少 `event_date` 时 freshness=0；不得支持 `signal_recency`
   - 不允许虚构 `task-provided:*` 一类来源定位符

### 运行时接线

- `coworker/agent.py`
  - `build_engine(..., skill_dirs=...)` 支持 SessionManager 显式注入真实 SkillStore 路径；直接调用仍保留原默认路径。
- `coworker/server/manager.py`
  - 交互会话和定时任务会话统一传 `self._skill_dirs(...)`。
  - `effective_skill_names` 与真正 `load_skill` 使用同一组目录。
- `tests/test_export_sales_pack_integration.py`
  - 已真实验证 `SessionManager(data_dir != state_dir)`：seed → 启用 Agent → 创建 Engine → 五个 `load_skill` 全成功。
- `tests/test_export_sales_lobster.py`
  - 已验证实际 interactive 会话中：读操作允许；本地写、Shell、CRM/外部动作请求审批。

### 前端最小接线

- `surfaces/gui/src/components/PersonasTab.tsx`：将 `export-sales-lobster` 纳入内置 i18n 映射。
- `surfaces/gui/src/i18n.tsx`：新增中英文 name/tagline。
- `surfaces/gui/src/i18n.test.tsx`
- `surfaces/gui/src/exportSalesPersonaI18n.test.ts`

## 已验证结果

- 最新核心合同 smoke（2026-08-07）：

```text
pytest tests/test_export_sales_skills.py \
       tests/test_chem_lead_ranking.py \
       tests/test_export_sales_pack_integration.py -q
43 passed in 6.94s
```

- Persona + runtime 定向：`6 passed`
- `tests/test_skills_sessions.py`：`14 passed`
- 前端 i18n：`4 passed`
- 此前较宽回归：`97 passed, 1 skipped`，但发生在最后几次评分强化之前，必须重新跑。
- 四个非 ranking Skill 已通过官方 `quick_validate.py`；ranking 需再跑一次。
- 独立前向实测曾成功运行 ranking CLI，但也暴露并促成了“禁止占位 locator”和“缺事件日期不得算新鲜”的后续修复；修复后的同场景尚未二次前向实测。

## 尚未完成：先把当前小任务收口

1. 重新运行完整目标回归：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.\.venv\Scripts\python.exe -m pytest `
  tests\test_export_sales_skills.py `
  tests\test_chem_lead_ranking.py `
  tests\test_export_sales_lobster.py `
  tests\test_export_sales_pack_integration.py `
  tests\test_skill_bootstrap.py `
  tests\test_skills_store.py `
  tests\test_skills.py `
  tests\test_skills_sessions.py `
  tests\test_persona_loading.py `
  tests\test_persona_registry.py `
  -q -p no:cacheprovider
```

2. 运行前端回归：

```powershell
cd surfaces\gui
npm.cmd test -- --run src/i18n.test.tsx src/exportSalesPersonaI18n.test.ts src/localization-audit.test.ts
```

3. 对五个 Skill 逐个运行：
   - `skill-creator/scripts/quick_validate.py`
   - 所有 JSON Schema `Draft202012Validator.check_schema`
   - 所有 JSON 文件解析
   - CAS CLI 与 ranking CLI 使用 `load_skill` 返回的绝对 `resources_path`，从无关 cwd 启动

4. 做一次修复后的前向测试：用户只口述“德国分销商、卖苯甲酸钠、近一年进口过”，但不提供企业名、URL、登记号、文件、贸易记录号或精确事件日期。正确行为应是 `NeedsReview`/请求补证，不得生成 Qualified 分数，不得制造占位 locator。

5. 做独立只读 code review。第一次 review 找出的 Critical/Important 已修，但四包修复后的 reviewer 因交接被中断，尚无最终结论。重点检查：
   - CompanyEvidencePack → ranking EvidenceItem 是否完全兼容
   - 来源类型 tier 上限是否与销售规格 §7.3 一致
   - Qualified 门槛、冲突、未知值和事件日期边界
   - 自定义 data_dir 下真实 `load_skill`
   - 任何权限绕过、外部写入或伪造来源
   - Schema 是否接受空业务对象

6. 清理测试产生的临时目录前，先逐个解析并确认目标位于本 worktree 且确为本任务生成：
   - `.test-tmp-chem-lead-ranking-*`
   - `.tmp/`
   - 任意 Skill 内 `__pycache__/` 或 `*.pyc`
   不得运行 `git clean`，不得删除未知目录。

7. 更新治理文档（现在仍存在状态冲突）：
   - `docs/chemclaw/README.md`：把“销售增长仅设计、未批准实现”改为“用户已明确授权且首个外贸内置能力包已实现”，写实际测试数；不得声称 API/Provider、邮件、CRM 或专属工作台已经完成。
   - `docs/chemclaw/DECISIONS.md`：新增 D-091，记录本次明确授权的范围、1 Agent + 5 Skill、默认仍是 cowork、无外部 API/写入、权限不变、确定性评分和真实 SessionManager 接线。
   - `docs/superpowers/specs/2026-08-07-chemclaw-sales-growth-intelligence-design.md`：修正页首及 §18 的“尚未批准实施”；只承认本包，不能把所有后续阶段视为自动批准。
   - `docs/superpowers/plans/2026-08-07-chemclaw-export-sales-builtin-pack.md`：按真实执行结果勾选/记录 RED、GREEN、回归和偏差。
   - `docs/chemclaw/DOMAIN.md` 已有销售领域对象，除非审查发现缺口，不必再扩写。

8. 对本任务明确路径运行 `git diff --check`，检查 UTF-8、尾随空格、重复 D 编号和 Mermaid 边标签。不要把其他 dirty 文件一起暂存或提交。

## 重要未解决边界（不能假装已经完成）

- 未接 PubChem、GLEIF、Comtrade、TED、SAM、SEC、USAspending、海关数据、Apollo、CRM 或邮件 Provider。
- API 必须进入平台 Tool/Provider 层；不能内嵌到 Skill。
- 当前 scoring/CAS 是 Skill 内 Python 脚本，通过 Shell 执行；开发环境已验证仓库 `.venv`，但 Windows 正式安装包是否向 Agent shell 暴露可用 Python 尚未验证。正式发布前应选择并验证受限脚本运行器或注册只读结构化 Tool。
- `seed_bundled_skills` 对已存在同名目录不自动升级；完整 Skill 版本激活、依赖、原子更新、回滚仍未实现，不能宣称满足完整安装生命周期。
- Schema 是合同和测试资产；除 ranking/CAS 外，其他阶段尚无平台级结构化校验 Tool。
- 新 Agent 没有专属客户清单工作台/空态任务卡；对话式首版可用。
- 英文界面目前只补了智能体管理列表的 name/tagline；Sidebar/PersonaView 的通用 persona 本地化仍有既有架构缺口。
- `default_permission_mode` 当前是 manifest 推荐元数据；真正权限模式来自 SessionManager/会话。不要误称 persona 字段能自行控制权限。
- 内贸拓客 Agent、商机雷达 Agent、外贸销售转化（联系策略/邮件草稿/询盘/报价）均未实现。
- `D:\化工社skills合集` 共约 158 个科研向 Skill，只做参考；不得批量复制内置。

## dirty worktree 边界

本任务相关或部分相关路径：

- `coworker/agent.py`
- `coworker/server/manager.py`（同时含此前“本机资料”等不相关改动，不能整文件回退）
- `coworker/personas/builtin/export-sales-lobster.md`
- 五个 `coworker/skills/bundled/chem-*/` 新目录
- `tests/test_chem_lead_ranking.py`
- `tests/test_export_sales_lobster.py`
- `tests/test_export_sales_pack_integration.py`
- `tests/test_export_sales_skills.py`
- `tests/test_skills_sessions.py`
- `surfaces/gui/src/components/PersonasTab.tsx`
- `surfaces/gui/src/i18n.tsx`（同时含此前 UI 改动，不能整文件回退）
- `surfaces/gui/src/i18n.test.tsx`
- `surfaces/gui/src/exportSalesPersonaI18n.test.ts`
- 本文件、销售规格、销售实施计划、README/DECISIONS/DOMAIN 中销售段落

明显属于此前其他任务、不要顺手改动或纳入本任务提交的例子：

- `coworker/cloud.py`
- `coworker/server/app.py` 中云/本机资料改动
- 大量 `surfaces/gui/src/App.tsx`、Sidebar、Settings、FolderGate、CloudSignIn 等 dirty 文件
- `tests/test_cloud_server.py`、`tests/test_local_profile.py` 及对应 UI tests

如果需要提交，必须先与用户确认，并按逐路径/逐 hunk 暂存；不要 `git add .`。

## 当前包收口后的下一条业务主线

在当前包通过完整回归和文档收口后，另写一个小任务计划实现“内贸拓客纵向链路”：复用 `chem-product-intelligence`、`chem-company-qualification`、`chem-lead-ranking`，只新增国内 Provider/中文查询/园区工商与国内角色规则以及必要 Agent。再下一项是 `OpportunitySignal`/商机雷达。每项仍须真实测试、权限边界和回退，不以数量堆薄 Skill。
