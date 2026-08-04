# ChemClaw 项目控制台

## 当前状态

- 产品设计：书面规格已于 2026-07-29 获得用户批准。
- 实施计划：阶段 1“首条真实纵向链路”已获用户批准。
- **架构调整（2026-08-03）**：采用方案 A，从 OpenWorker 最新 `main`（含 2026-08-01 Skills PR #391）重建 ChemClaw 层，丢弃自研 `capabilities` 模块。
- 当前阶段：阶段 1，上游 Skill + ChemClaw 品牌/汉化/导航（进行中，待用户界面验收）。
- 当前分支：`chemclaw-clean`（与本机 worktree 目录同名；GitHub 上选此分支即可，无需并入 `main`）
- **唯一开发基线 Worktree**：`D:\OpenWorker\openworker\.worktrees\chemclaw-clean`（后续只在此继续开发）
- 旧 Worktree（只读备份，待确认后删除，本次不删）：`D:\OpenWorker\openworker\.worktrees\chemclaw-design`（分支 `design/chemclaw-foundation` / 标签式备份 `backup/broken-2026-08-03` 已在 `backup` 远程）
- 业务代码（本 Worktree）：
  - ✅ 基于 upstream/main（OpenWorker Skills 官方实现）
  - ✅ ChemClaw 品牌 + 全界面汉化（cherry-pick 自旧分支）
  - ✅ D-006 主导航：对话 / 技能 / 专家龙虾 / 定时任务 / 连接 / 设置
  - ✅ 技能页使用上游 `SkillsTab`，已汉化；不再使用自研 `SkillsView` / `capabilities`
  - ✅ 专家龙虾页（`PersonasTab`）控件与内置专家文案已接入 i18n（此前只汉化了页标题）
  - ✅ 首次启动 seed 完整内置 Skills（Serenity 七个中文投研 + builtin-skills 除 computer-use + chem-* 系列；含 references/scripts；可删且不回种）
  - ✅ Skill 名支持中文；zip 上传保留附属文件与扩展 frontmatter
  - ❌ 已移除薄提示词版 `serenity.industry-chain-mapping`（若开发态仍残留，可在技能页手动删除一次）
  - ✅ 自动更新入口已关闭（`UPDATES_ENABLED = false`）
  - ✅ 空模型流不再静默落成空白助手消息（`TurnEngine` 改为可重试 ERROR）
  - ✅ OpenAI 兼容流遇 `incomplete chunked read` 时自动重试并回退非流式；错误文案中文化
  - ✅ 对话内中文 `artifact:` 链接打开产物：解码 react-markdown 的 percent-encode，避免误报「文件已移动/删除」
  - ✅ 产物预览期间手动展开左侧栏不再被自动打回（预览开闭边沿折叠 + 稳定 `onPreviewChange`）
  - ✅ 对话与 MD 报告 fenced mermaid 真实渲染（图/源码、遮罩全屏、SVG/PNG；流式不出图；防抖占位）
  - ✅ Mermaid 全屏：以矢量 SVG（viewBox）铺满视口，缩放改 CSS 宽高而非 bitmap transform，避免又小又糊
  - ✅ Mermaid 全局主题改为 `neo`（彩色现代主题；图内 `%%{init}%%` / `classDef` 仍可覆盖）
  - ✅ Mermaid 悬停/聚焦才显示框线与工具栏（默认融文；错误态始终露出；工具栏 visibility 保占位防抖）
  - ✅ 设置页 Context compaction 已汉化；默认触发阈值/上限拉到允许最大值（95% / 2,000,000 tokens）
  - ✅ 后台对话继续与回切追齐：离开设置/其他对话不杀 turn；同会话重选不误清 streaming；`ready.running` + `turn_done` REST 追齐最终回答（D-061）
  - 🔄 对话挂载条等待在上游 Skill 稳定后单独处理
- 浏览器源码预览：默认显示简体中文，可切换英文并在刷新后保留选择。
- 运行态修复（2026-08-03，开发 state）：
  - OpenAI 兼容网关 `base_url` 补全为 `…/v1`（缺 `/v1` 会导致 0 chunk 空回答）
  - 默认模型改为流式稳定的 `kimi-k2.5`（原 `deepseek-v4-flash` 在该网关上工具流易断）
  - 真实 WS 链路验证：`agent=chat` → 助手返回 `OK`
  - 回归状态（2026-08-04，bundled skills）：
  - `pytest tests/test_skills_store.py tests/test_skill_bootstrap.py tests/test_skills.py tests/test_skills_api.py`：71 passed, 1 skipped
  - 内置目录：`coworker/skills/bundled/` 共 43 个完整 skill（无 `computer-use`、无薄版 industry-chain）
  - 回归状态（2026-08-04，Context compaction）：
  - `pytest tests/test_compaction_engine.py tests/test_compaction.py`：31 passed
  - `npm test`（i18n + localization-audit）：21 passed
  - 回归状态（2026-08-04，后台对话继续 / 回切追齐）：
  - `pytest tests/test_server.py::test_ws_ready_reports_running tests/test_session_events.py`：7 passed
  - `npm test -- --run src/sessionResume.test.ts src/itemsFromMessages.test.ts`：13 passed
- 回归状态（2026-08-03）：
  - `pytest tests/test_engine.py`（空流 + 流式 + 无工具）：3 passed
  - `pytest` stream 重试/回退 + model errors：12 passed
  - `npm test`（i18n + localization-audit）：21 passed
  - `npm test -- --run src/navArtifactPreview.test.ts`：4 passed
  - Mermaid：`mermaidExports` + `MermaidBlock` + `Markdown` 定向单测（含 theme `neo` 断言与「同文案重渲染不重复 mermaid.render」）；真实链路探针：scrollHeight 稳定、滚轮可到页底、5s 内无图卸载
  - `npm run build` 通过（含 mermaid.core chunk）
  - UpdateBanner 单测因 ChemClaw 关闭自动更新而预期失败（非回归）

## 下一道门禁

1. 用户在 `chemclaw-clean` 打开界面验收：品牌 ChemClaw、默认中文、主导航、技能页（中文投研 + chem-* 内置、可删除不回种）、Mermaid neo 可见。
2. 验收满意后删除旧 `chemclaw-design` worktree（`git worktree remove`）；在此之前勿在旧树继续开发。
3. 规划对话挂载条、Serenity Agent（专家龙虾）、以及依赖型 Skill 的便携运行时安装器；Mermaid 手工 UI 验收清单见实施计划 Task 5。

## 文档索引

- [完整产品设计](../superpowers/specs/2026-07-29-chemclaw-product-design.md)
- [已批准决策](DECISIONS.md)
- [领域术语](DOMAIN.md)
- [测试、开发环境与源码预览](TESTING.md)
- 仓库级协作入口：`AGENTS.md`
- [阶段 1 实施计划](../superpowers/plans/2026-07-29-chemclaw-first-vertical-slice.md)

## 路线图摘要

1. 项目文档、Git/Worktree 和测试基线。
2. ChemClaw 品牌、中文化、真实 Skill 页面、Serenity 代表 Skill、对话挂载和 Mermaid 闭环。
3. 完整 Skill/Agent 平台与第一个可日常使用的 ChemClaw 安装程序。
4. SAG 检索、备份恢复和大数据导入。
5. 2D、3D 和探索模式。
6. 双链化工百科、标准产业链图和交互价格图。

## 当前环境检查

- 日常开发请使用 **`chemclaw-clean` Worktree**（唯一开发基线；不要再在旧的 `chemclaw-design` 上改代码）。
- Python 下载缓存、开发状态和 pytest 临时目录统一放在 `D:\OpenWorker\.chemclaw-dev`。
- 拉 upstream：`git fetch upstream main`（remote：`https://github.com/andrewyng/openworker`）。
- 完整版本、命令、测试数字、启动顺序和已知缺陷以 [TESTING.md](TESTING.md) 为准。

## 新任务推荐开场

> 继续 ChemClaw 阶段 1（分支与 worktree 均为 `chemclaw-clean`）。请先阅读 AGENTS.md、项目控制台、已批准规格、TESTING.md 和实施计划。Skill 功能以 OpenWorker 上游实现为准；ChemClaw 只做品牌、汉化、导航与 bundled Skill 薄层。一次只执行指定 Task。
