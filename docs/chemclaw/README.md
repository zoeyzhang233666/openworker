# ChemClaw 项目控制台

## 当前状态

- 产品设计：已在对话中逐节批准，书面规格等待用户复核。
- 当前阶段：阶段 0，项目控制基础。
- 当前分支：`design/chemclaw-foundation`
- 当前 Worktree：`D:\OpenWorker\openworker\.worktrees\chemclaw-design`
- 业务代码：尚未修改。
- 当前产品数据：OpenWorker 源码为刚克隆状态，没有需要迁移的用户数据。

## 下一道门禁

1. 用户审核完整设计规格。
2. 根据反馈修订并重新自审。
3. 用户批准书面规格后，使用 `writing-plans` 为“首条真实纵向链路”编写实施计划。
4. 实施计划获批后才开始业务代码修改。

## 文档索引

- [完整产品设计](../superpowers/specs/2026-07-29-chemclaw-product-design.md)
- [已批准决策](DECISIONS.md)
- [领域术语](DOMAIN.md)
- 仓库级协作入口：`AGENTS.md`
- 后续实施计划目录：`docs/superpowers/plans/`

## 路线图摘要

1. 项目文档、Git/Worktree 和测试基线。
2. ChemClaw 品牌、中文化、真实 Skill 页面、Serenity 代表 Skill、对话挂载和 Mermaid 闭环。
3. 完整 Skill/Agent 平台与第一个可日常使用的 ChemClaw 安装程序。
4. SAG 检索、备份恢复和大数据导入。
5. 2D、3D 和探索模式。
6. 双链化工百科、标准产业链图和交互价格图。

## 当前环境检查

- 当前主工作区和规划 Worktree 都没有 Python 虚拟环境或前端 `node_modules`。
- Node.js 与 npm 可用。
- 当前 `python` 命令由 uv trampoline 提供，但在沙箱内启动子进程被拒绝。
- 当前终端找不到 Rust `cargo`。
- 因本次只提交文档，没有为规划 Worktree 重复安装整套依赖，也没有宣称业务测试已通过。
- 正式实施前必须建立并记录可复现的 Python、Node 和 Rust 测试基线。

## 新任务推荐开场

> 继续 ChemClaw 项目。请先阅读仓库根目录的 AGENTS.md 和其中指定的项目文档，再用中文汇报当前状态，不要直接修改代码。
