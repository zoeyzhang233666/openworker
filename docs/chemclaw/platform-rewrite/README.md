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

## 默认边界

- 仅改写时不主动联网补 CAS / 纯度 / 认证 / 案例等  
- 默认智能体仍为 ChemClaw/`cowork`；本龙虾默认禁用，需在「智能体」页启用  
- knowledge 会话会自动把已安装 `skills` 目录挂为**只读 root**，以便 `load_skill` 后的 `read_file` 能读 references/schemas（不放宽全盘权限）  
- 词表升级与安装包验收属 M3（见实施计划）

## 收口记录（M2）

- **2026-08-10**：工作区曾显示 platform-rewrite 相关路径「已修改」，核对 blob 与 `HEAD` 内容一致（Windows 换行/stat 假 dirty），已 `git restore` 清标记。
- 定向回归：`pytest tests/test_platform_rewrite_skills.py tests/test_platform_rewrite_lobster.py tests/test_platform_rewrite_corpus.py` → **26 passed**（`--basetemp` 指向 `D:\OpenWorker\.chemclaw-dev\pytest-basetemp\...`）。
- **未启动 M3**；下一刀须点名且确认打安装包。

## 相关文件

- Persona：`coworker/personas/builtin/platform-rewrite-lobster.md`
- Skills：`coworker/skills/bundled/chem-rewrite-brief|chem-platform-rewrite|chem-content-policy|chem-content-quality-check|chem-hook-cta-pack/`
- 合成夹具：`fixtures/`
- 回归语料（M2）：[`corpus/REGRESSION_CORPUS.md`](corpus/REGRESSION_CORPUS.md) + `corpus/cases/`
- 计划：`docs/superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md`
- 交接：`docs/chemclaw/HANDOFF_PLATFORM_REWRITE.md`
