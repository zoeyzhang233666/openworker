# ChemClaw Phase 2 子智能体与后台任务产品闭环实施计划（D-172）

**规格：** `docs/superpowers/specs/2026-08-20-chemclaw-subagent-task-visibility-design.md`

**状态：已完成并经真实会话验收（2026-08-20）**

1. 在 TurnPlan 增加明确 delegation eligibility；为 eligible Scenario 合并 Subagent 控制工具，并在逐轮上下文注入有界并行委派政策。
2. 为 BackgroundTaskManager 增加 created/status/output change interface 与测试；SessionManager 绑定 FastAPI event loop 并向 owner session WS 推送 `background_task_changed`。
3. 补齐前端 BackgroundTask/Output 类型和 list/output/send/stop REST adapter。
4. 新建 `BackgroundTasksSection`，接入 RightRail；实现任务列表、详情、状态/耗时、输出、停止和 Agent 续发，空任务不显示。
5. App 消费 `background_task_changed`，以 refresh key 驱动 task 模块；REST 负责初始加载和重连恢复。
6. 跑 Python/GUI 聚焦回归、build 与真实开发服务冒烟；验证复杂研究实际创建 task 并在右侧栏可见。
7. 更新 D-171/D-172、README、DECISIONS、DOMAIN、TESTING；如实记录全量与 Windows ACL 状态。

实施保留 D-168—D-171 全部未提交改动，不恢复 `AuditView`/“活动”入口，不清理既有 ACL 异常 pytest 目录。

## 实际结果

- 代码：7 项全部完成；真实验收追加 `research` Profile 的只读 `read_file/list_files`。
- 回归：Python 52 passed；GUI 34 passed；production build、`compileall` 通过。
- Live：ApiHub 会话 `c3b686dc-2f8` 实际创建并完成 3 个 `research` task；RightRail 显示 3 张任务卡并可打开工作记录，其中两个分支产出带证据链接的完整复核报告。父轮 Provider 超时后 child task 仍继续直至完成，验证后台生命周期独立；已完成任务经右栏续发后以 `run_count=2` 读取原报告、继续检索并再次完成。
- 全量：未重跑已知会触发 Windows SecretStore ACL 污染的 Python 全量组合，不声称全量通过。
