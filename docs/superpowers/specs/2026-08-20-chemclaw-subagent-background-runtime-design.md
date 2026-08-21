# ChemClaw Subagent Runtime + BackgroundTaskManager 设计（D-171）

## 1. 目标与边界

Phase 2 把现有同步、只读、一次性的 `explore` 泛化为声明式 Subagent Runtime，并把 Agent 与 Shell 的后台执行收口到一个可查询、可停止、可继续发消息、可读取输出、可等待/汇总的 `BackgroundTaskManager`。

本阶段继续复用唯一 `TurnEngine`、`ConversationStore`、`PermissionEngine`、MCP/Skill/Persona 与 TurnTrace；不引入第二套 Agent Loop，不嵌入第三方运行时，不实现 Team/Swarm、Hook Bus、Verifier、远程执行或 Worktree 自动隔离，也不恢复普通用户侧“活动/执行诊断”页面。

## 2. 成熟项目参考基线

实现不是从零设计，固定对照以下 2026-08-20 拉取的上游版本：

- [HKUDS/OpenHarness](https://github.com/HKUDS/OpenHarness) `9b2efd795c6aa09f88b0c257d269a9e518da6ae7`：采用统一 task record、Agent/Shell 同一 manager、`create/get/list/stop/write/read/listener` 生命周期与直接 `argv` 的 Windows 安全经验。
- [bytedance/deer-flow](https://github.com/bytedance/deer-flow) `a5acc25de6742b2166b3f41c97bd895822277b94`：采用独立子 Agent context、`task_started/completed/failed` 状态、轮询超时、协作取消和 terminal 后再清理的语义。
- [openai/openai-agents-python](https://github.com/openai/openai-agents-python) `2af94722d93a5a1719af33ab7559ba79cc778f7f`：采用 manager-owned agent-as-tool、父子 trace/group 关联以及嵌套 Agent 工具仍由外层审批边界管理的原则。
- [LangGraph durable execution](https://github.com/langchain-ai/langgraph)：仅借鉴 thread/checkpoint、interrupt/resume、幂等副作用的语义；不引入 Graph runtime。本阶段进程重启只做状态调和和子会话恢复，不承诺从被中断的 Tool 指令中点自动重放。

与上游不同：OpenHarness 在 Agent 进程退出后写入会重启并丢失上下文；ChemClaw 使用持久 child session 重建同一 `TurnEngine` 上下文，继续消息不丢历史。

## 3. 深模块边界

### 3.1 `BackgroundTaskManager`

公开接口只包含：

- `start_agent(spec, adapter)` / `start_shell(spec)`
- `get(task_id)` / `list(owner_session_id, status, limit)`
- `read_output(task_id, cursor, limit)`
- `send_message(task_id, message)`
- `stop(task_id)`
- `wait(task_id, timeout)` / `gather(task_ids, timeout)`
- `register_completion_listener(listener)`

Manager 持有状态机、并发、取消、输出游标、completion listener 与 SQLite 持久化；它不理解 Prompt、Tool、Persona 或 Permission。

状态固定为 `queued -> running -> completed|failed|cancelled`。已完成 Agent 收到后续消息时可 `completed -> queued -> running`，`run_count` 增加并复用 child session。Shell 不接受消息。进程启动时将遗留 `queued/running` 调和为 `interrupted`，保留输出和错误说明；Agent 可通过后续消息从持久 child session 继续，Shell 不自动重放命令。

### 3.2 `SubagentRuntime`

公开接口只包含 profile 查询、前台执行、后台启动以及对 Manager 生命周期方法的薄转发。它通过 `AgentTaskAdapter` 复用 `TurnEngine.run()`，不实现模型循环。

`SubagentProfile` 为 `frozen + extra=forbid + version=1`：

- `id/title/description/agent_id`
- `mode/model/max_turns`
- `tool_allowlist/disallowed_tools/skills/mcp_servers`
- `background/isolation/allow_nested`

首批内置 profile：

- `explore`：Code Agent、PLAN、只读文件/搜索/Git、10 turns、禁止递归。
- `research`：ChemClaw Agent、PLAN、Web/化学身份/企业身份等只读研究工具、32 turns、禁止递归。
- `worker`：Code Agent、INTERACTIVE、继承现有工具与审批、32 turns、禁止递归；不自动授予写入、Shell 或外部发送权限。

Profile 是平台可信配置。模型只能选择已注册 profile，不能在调用参数里任意拼接 Tool/权限/model 配置。

## 4. 权限、上下文与隔离

- 子 Agent 的每个 Tool 仍走自己的 `TurnPlan -> guards -> PermissionEngine -> ToolRegistry`。
- `explore/research` 使用 PLAN，写入、Shell 与外部副作用硬拒绝。
- `worker` 使用 INTERACTIVE；审批复用父会话 Inbox 路由，后台无前台 socket 时也不会静默放行。
- 子 Agent 使用独立 child session 与消息历史；只继承显式 workspace、profile、模型与父 trace/task 标识，不复制父会话正文。
- Phase 2 isolation 为 `read_only|shared_workspace`。`worktree|remote` 仅保留枚举的未来兼容位，不在本阶段启用。
- 子 Agent 默认不能再启动子 Agent，防止无界递归。

## 5. Shell 兼容

`run_shell(run_in_background=true)`、`shell_task_output`、`shell_task_kill` 名称与返回形状保持兼容，但在由 `SessionManager` 构建的引擎里委托统一 Manager。直接构造 `LocalExecutor` 的 CLI/旧单测保留本地兼容实现。

后台 Shell 启动仍必须先通过 `run_shell` 的高风险审批。读取和停止仅能访问当前 owner session 创建的 task；通用 REST API使用本地鉴权并按 session 过滤。

## 6. Agent 工具合同

为 Code/Knowledge Agent 注册：

- `start_subagent(task, profile, background, description)`
- `background_task_status(task_id)`
- `background_task_output(task_id, cursor)`
- `background_task_send(task_id, message)`
- `background_task_stop(task_id)`
- `background_task_gather(task_ids, timeout_seconds)`

`explore(task)` 保持旧同步返回 `{report}` 合同，内部改由 `SubagentRuntime.run_foreground(profile="explore")` 实现。没有 Session runtime 的直接 `build_engine()` 调用继续使用旧 explorer builder，保证兼容。

所有任务控制工具都验证 owner session；不能跨会话猜 task id 控制他人任务。`start_subagent(profile="worker")` 本身不等于写权限，子 Agent 的 consequential Tool 仍逐项审批。

## 7. 持久化与输出

沿用 `coworker.db`，新增独立表：

- `background_tasks`：内容最小化 metadata、状态、父/子 session、profile、时间、计数与错误。
- `background_task_output`：单调 `seq`、stream、text、时间。

API/Tool 默认单次输出有字符上限并返回 `next_cursor`/`truncated`。Task metadata 不保存父会话 Prompt、Tool 参数、凭据或 reasoning。Agent 正文只存在 child conversation 与按用户要求读取的 task output；TurnTrace 仍保持 D-169 的内容无关约束。

默认保留 30 天且最多 5000 个 terminal task；清理只删除对应 task/output，不删除 child conversation。清理和持久化失败为 best-effort，不能拖垮主 turn。

## 8. Server API

- `GET /v1/subagent-profiles`
- `POST /v1/background-tasks/agent`
- `GET /v1/background-tasks?session_id=...`
- `GET /v1/background-tasks/{task_id}`
- `GET /v1/background-tasks/{task_id}/output?cursor=...`
- `POST /v1/background-tasks/{task_id}/messages`
- `POST /v1/background-tasks/{task_id}/stop`
- `POST /v1/background-tasks/gather`

显式启动 Agent task 需要有效 session、profile 和 workspace；无效 profile/跨 session 控制返回 404/422。Phase 2 不增加 GUI 页面。

## 9. 验收

- `explore` 旧合同、只读、无递归全部通过。
- `research/worker` 使用独立 context；worker 未审批不能写。
- Agent 前台返回报告；后台立即返回 task id，可查状态/增量输出/停止/继续发消息。
- Shell 旧工具名接入统一 task id、状态、输出和停止。
- 两个以上 Agent 可并行，`gather` 按输入顺序汇总，不因单个失败丢失其他结果。
- completion listener 只在每次 run terminal 时触发；listener 异常不影响任务。
- 重启调和遗留运行状态；Agent 后续消息复用持久 child session，Shell 不自动重放。
- owner session 隔离、输出上限、30 天/5000 条清理、REST schema 有测试。
- D-165/D-166/D-169 聚焦回归、现有 Permission/MCP/Automation/Shell/Subagent 测试通过；不新增依赖、不恢复 Activity GUI。
