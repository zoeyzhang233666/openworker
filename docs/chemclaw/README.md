# ChemClaw 项目控制台

## 当前状态

- 产品设计：书面规格已于 2026-07-29 获得用户批准。
- 实施计划：阶段 1“首条真实纵向链路”已获用户批准。
- 当前阶段：阶段 1，Task 2B“现有用户可见界面中文化”完成，等待用户验收。
- 当前分支：`design/chemclaw-foundation`
- 当前 Worktree：`D:\OpenWorker\openworker\.worktrees\chemclaw-design`
- 业务代码：Task 2 产品壳层和 Task 2B 轻量双语界面已完成；内部协议、包名、CLI、数据库兼容字段和上游许可证保持不变。
- 当前产品数据：OpenWorker 源码为刚克隆状态，没有需要迁移的用户数据。
- 浏览器源码预览：默认显示简体中文，可切换英文并在刷新后保留选择。
- 回归状态：Task 2B 本地化定向单测、ChemClaw 壳层 E2E 和 GUI 生产构建通过；后端全量测试仍保留已知 Windows/上游基线失败，详见测试文档。

## 下一道门禁

1. 用户验收 Task 2B 的中文覆盖、英文切换与刷新保留。
2. 验收通过后再执行阶段 1 Task 3。
3. 不在 Task 2B 中提前实现真实 Skill 页面或其他 Task 3 功能。

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

- Worktree 已建立 Python 3.11 `.venv` 和前端 `node_modules`。
- Python 下载缓存、Python 发行版、开发状态和 pytest 临时目录统一放在 `D:\OpenWorker\.chemclaw-dev`。
- Rust、Visual Studio Build Tools、LLVM/Clang 和 Playwright Chromium 已安装为机器/用户级共享工具链，不需要为每个 Worktree 重装。
- 浏览器热更新推荐用于日常高频修改；Tauri 源码模式用于验证原生桌面能力；两者都不需要先构建安装包。
- 完整版本、命令、测试数字、启动顺序和已知缺陷以 [TESTING.md](TESTING.md) 为准。

## 新任务推荐开场

> 继续 ChemClaw 阶段 1。请先阅读 AGENTS.md、项目控制台、已批准规格、TESTING.md 和实施计划，核对最近提交与未完成任务。一次只执行指定 Task；测试并形成小提交后停止，不提前做后续 Task。
