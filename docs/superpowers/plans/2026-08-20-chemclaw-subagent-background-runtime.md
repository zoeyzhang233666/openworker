# ChemClaw Subagent Runtime + BackgroundTaskManager 实施计划（D-171）

**规格：** `docs/superpowers/specs/2026-08-20-chemclaw-subagent-background-runtime-design.md`

**状态：已实施，待用户验收**

1. 建立 BackgroundTask immutable models、SQLite store、状态机 manager、输出游标、取消、wait/gather、listener、重启调和与清理测试。
2. 建立 SubagentProfile registry 与 AgentTaskAdapter；复用 `TurnEngine`、child conversation、父会话 Inbox 审批与 trace 关联。
3. 将 `explore` 改为 Runtime 前台兼容包装；为 Code/Knowledge 注册受 owner session 隔离的 Subagent/任务控制工具。
4. 将 SessionManager 创建的 `LocalExecutor` 后台 Shell 接入统一 Manager，保留直接构造 executor 的旧行为与旧工具合同。
5. 增加 profile/task REST API，不增加 GUI 页面。
6. 跑新模块、Subagent、Shell、Permission、Engine、Server、Automation、D-165/D-166/D-169 聚焦回归和 Python 组合回归。
7. 更新 README、DECISIONS、DOMAIN、TESTING，记录真实结果、已知污染和 Phase 3 边界。

实施必须保留 D-168/D-169/D-170 的全部未提交修改；不恢复 `LeadsWorkbench`、`AuditView` 或“活动”入口，不清理现存 ACL 异常 pytest 临时目录。

## 实施结果（2026-08-20）

- 已建立统一 `BackgroundTaskManager`，Agent 与 Shell 共用 task id、状态、输出游标、停止、wait/gather、completion listener、30 天/5000 条清理与重启调和。
- 已建立声明式 `SubagentProfile` 与 `SubagentRuntime`；内置 `explore`、`research`、`worker`，全部复用现有 `TurnEngine`、Conversation、ToolRegistry、MCP、PermissionEngine 与 TurnTrace，不存在第二套 Agent Loop。
- `explore` 保留旧 `{report}` 前台合同；后台 Agent 可查状态、增量读输出、停止、续发消息并复用持久 child session。写入型 `worker` 仍由既有 PermissionEngine 最终裁决。
- SessionManager 的后台 Shell 已接入统一生命周期；直接构造 `LocalExecutor` 的旧用法保持兼容。
- 已新增 profile/task REST API；按 D-170 不恢复普通用户“活动/执行诊断”页面。
- 聚焦回归：Phase 2 runtime/permission **85 passed**；Harness/Planner/Trace **134 passed**；D-166 国内行情/市场守卫 **89 passed**；既有 Automation **21 passed**（1 项因固定写沙箱外目录而在宿主权限单独复跑）。服务器组合首个失败仍为已知 Windows `SecretStore` pytest 临时目录 ACL `PermissionError`，不是 Phase 2 功能断言；未宣称 Python 全量通过。
- 开发前后端已重启；健康检查返回 `ok`，鉴权后的 Profile API 真实返回 `explore,research,worker`。
