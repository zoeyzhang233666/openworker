# ChemClaw 现有能力加固实施记录

规格：[用户批准的设计](../specs/2026-09-27-chemclaw-stability-design.md)。基线 993d0d0。

- [ ] 0 现状/问题/测试清单，上游固定提交与完整模块差异台账。
- [ ] 1 只读子智能体、工具性质验证、旧写任务兼容。
- [ ] 2 统一任务状态、共享 300/15 预算、五路并发、继续/停止/恢复/汇合。
- [ ] 3 主/子模型能力和上下文、工具发现、诊断验收。
- [ ] 4 全部可离线产品回归及失败分类、界面状态。
- [ ] 5 上游逐项适配与沙箱评估（不接入沙箱）。
- [ ] 6 隔离真实验收准备；账号/模型/额度/外发范围另确认；正式构建安装未授权。

每阶段小提交，记录实际结果，未验证不得标完成。

第一步（2026-09-27）：只读执行守卫、用户明确只读分类的 MCP、停用 worker/market_report 新建及恢复、共用主/子压缩和检查点。基线四文件 29 passed/3 failed（旧 profiles 断言两项，无进展被旧测试期待为 max_iterations 一项）；修改后五文件 34 passed。禁联网策略快照已接入，重启根目录/共享预算仍在下一步补齐。

第二步（2026-09-28）：SessionManager 主/子任务共享 SQLite 预算，原子领取并结算成功轮次，崩溃时未结算请求记为不确定消耗；最后 15 轮只准主助手整理交付。暂停、截断、阻塞不再统称失败，普通消息/审批恢复不续增预算。主任务停止只传播本任务组；后台迟到结果不自动唤醒已停止/换组的主任务；快速子任务等整批委派结束再汇总。检查点覆盖开始、工具前后、每 50 轮和完成；恢复未知写操作先核对。长结果支持同一输出块内分页，不再丢前半段。后台研究继承模型设置、只读目录、禁联网约束，刷新经过明确只读分类的 MCP。

实际回归：`test_task_budget/task_group_integration/background_states/background_tasks/subagent/subagent_readonly/subagent_runtime/subagent_cohort_wake/runtime_budget/runtime_resume/runtime_acceptance/durable_resume/deliver_mcp` 共 **78 passed**；GUI BackgroundTasksSection/itemsFromMessages **11 passed**，`tsc --noEmit` 通过。包括真实引擎 300 轮后暂停并继续、主助手 2 轮＋小助手 35 轮累计 37 轮、重启未知写操作不重做。发现并修复跨 asyncio.run 重用 Event 引起的假空响应；审批测试明确指定交互权限模式，不改变产品默认权限。

仍待：独立 CLI explore 路径、定时任务与全部产品回归、摘要辅助调用计量、上下文拆分、所有上游候选评估及真实服务验收。本段结果不是“所有 bug 已修好”。安装、构建、合并和真实账号操作均未执行。
