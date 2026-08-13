# 化工多平台内容重构

内置智能体「化工内容重构龙虾」（`platform-rewrite-lobster`）把化工 / 精细化工 / 贸易素材，改写成适合小红书、抖音、X 的发布稿，并做事实保持与敏感表达质检。

## 定位

- **事实保持 + 独立表达 + 平台适配 + 合规质检**
- 不是单纯同义词替换，也不是「绕原创检测」
- **草稿 ≠ 发布**：不登录平台、不自动发帖；门禁最高到 `ready_for_publish_review`（人工审阅）

## 流水线

1. `chem-rewrite-brief` — 结构化 `RewriteBrief` 事实合同  
2. `chem-platform-rewrite` — 按平台重构表达  
3. `chem-content-policy` — 词表 + `scan_content.py`  
4. `chem-content-quality-check` — `check_content.py` 确定性门禁  

平台由 Persona 识别（用户说「改成小红书」即可）。  
**按需（M2）**：`chem-hook-cta-pack` — 仅用户要标题 / 封面 / 钩子 / CTA 时 `load_skill`；不插入上述四步强制顺序；写入后仍须再过 policy → quality-check。

## 词表层（M3 / D-128）

- **官方 managed**：`chem-content-policy/references/lexicon/managed/base.csv` + `rule_version.txt` — 发版可热升级；勿手改。
- **用户覆盖**：同目录旁 `user.csv` — 自定义禁词，或 `action=suppress` 关掉某条 `rule_id`；官方同步**永不覆盖**。
- 扫描 JSON 含 `rule_set: { id: chem-content-policy, version }`。
- 启动：`seed_bundled_skills` 后调用 `sync_managed_lexicon`（只同步 managed；兼容旧 `lexicon/base.csv` 迁入 managed）。

## 默认边界

- 仅改写时不主动联网补 CAS / 纯度 / 认证 / 案例等  
- 默认智能体仍为 ChemClaw/`cowork`；本龙虾默认禁用，需在「智能体」页启用  
- knowledge 会话会自动把已安装 `skills` 目录挂为**只读 root**，以便 `load_skill` 后的 `read_file` 能读 references/schemas（不放宽全盘权限）

## 收口记录

- **2026-08-10（M1+M2）**：假 dirty 已清；定向 pytest 26 passed。
- **2026-08-12（M3 / D-128）**：managed + user 词表、`sync_managed_lexicon`、schema/`rule_set`、packaging SkillLoader 路径验收；`pytest` platform-rewrite + bootstrap + packaging **38 passed**。正式 NSIS frozen 补验须再确认打安装包。

## 相关文件

- Persona：`coworker/personas/builtin/platform-rewrite-lobster.md`
- Skills：`coworker/skills/bundled/chem-rewrite-brief|chem-platform-rewrite|chem-content-policy|chem-content-quality-check|chem-hook-cta-pack/`
- 合成夹具：`fixtures/`
- 回归语料（M2）：[`corpus/REGRESSION_CORPUS.md`](corpus/REGRESSION_CORPUS.md) + `corpus/cases/`
- 计划：`docs/superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md`
- 交接：`docs/chemclaw/HANDOFF_PLATFORM_REWRITE.md`
