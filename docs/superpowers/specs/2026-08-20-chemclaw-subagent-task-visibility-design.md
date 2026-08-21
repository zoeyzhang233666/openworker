# ChemClaw Phase 2 子智能体与后台任务产品闭环规格（D-172）

**状态：用户已批准；实施与真实产品验收完成（2026-08-20）**

## 1. 问题

D-171 已建立 `SubagentRuntime + BackgroundTaskManager`、持久 task、REST 与模型工具，但普通复杂对话没有形成产品闭环：

- Scenario 只能表达 `allow_subagent`，没有把该决策转成明确的 Tool Projection 与逐轮委派指令。
- `subagent_started` 永远为 false；模型可能继续由主上下文串行调用十余次工具。
- BackgroundTask 生命周期只存在 SQLite/REST，没有进入父会话的 live event seam。
- GUI 右侧栏只有进度、产物与访问权限；用户看不到 Agent/Shell task，也无法检查输出、停止或续发要求。

2026-08-20 真实会话 `c3b686dc-2f8` 证明该缺口：Scenario 为 `chemical_company_research` 且 `subagent_eligible=true`，但 Background Task 为 0、Trace `subagent_calls=0`，主智能体自行调用 13 次工具。

## 2. 产品目标

在不恢复 D-170 独立“活动/执行诊断”页的前提下，把 Phase 2 做成会话内可见、可恢复、可控制的能力：

1. 可拆分的复杂研究请求能获得并使用 Subagent 工具。
2. 父会话右侧栏只在存在 task 时显示“子智能体与后台任务”。
3. 用户可查看任务说明、Profile/类型、状态、耗时、增量工作记录与最终报告。
4. 用户可停止运行中任务，并向 Agent task 续发要求；Shell 不接受消息。
5. WebSocket 提供低延迟变化通知，REST/SQLite 是刷新、重连和断线恢复权威。
6. PermissionEngine 仍是所有子智能体实际 Tool 调用的最终权限权威。

## 3. 非目标

- 不恢复账号菜单“活动”或独立诊断页面。
- 不实现完整 Team/Swarm、Agent 群聊、自动 Verifier 或 Hook Bus。
- 不展示模型隐藏推理/chain-of-thought；只展示任务说明、状态、工具进展、系统记录和最终报告。
- 不允许前端绕过 owner session、Profile、Permission 或审批。
- 不自动重放进程中断的 Shell/Tool 副作用。

## 4. 深模块与接缝

### 4.1 Delegation Policy

`TurnPlanner` 仍是唯一逐轮规划接缝。对于匹配到 `ScenarioSpec.allow_subagent=true` 且 route 为 `AGENT`/`DEEP_RESEARCH` 的请求：

- 若当前投影是 allowlist，合并 `start_subagent` 与 status/output/send/stop/gather 控制工具。
- 若当前投影为 legacy/full，不缩窄工具面。
- 逐轮上下文加入短委派政策：只有存在至少两个可独立推进的研究分支时，最多启动 3 个 `research` background task；任务必须有界且不重叠；主 Agent 继续有用工作并在最终综合前 gather。
- 单事实、单数据源、简单查价和需先澄清但尚无可执行分支的请求不强制委派。
- Planner 只决定 eligibility/工具面/指导，不直接执行 Tool；真实 `start_subagent` Tool 成功才算 started。

### 4.2 BackgroundTask Event Interface

`BackgroundTaskManager` 增加统一 change listener：`created/status/output`，载荷只含 change 与最新 `BackgroundTaskRecord`，不含 Prompt、Tool 参数、凭据或 reasoning。

`SessionManager` 是 transport adapter：在 FastAPI lifespan 绑定当前 event loop，把 manager change 映射为父会话 WS `background_task_changed`。WS 是提示刷新，不是权威存储；客户端收到事件后仍通过 REST 读取当前 task/output。

### 4.3 GUI Task Module

新增 `BackgroundTasksSection` 深模块，外部 interface 只需要 `sessionId/refreshKey`。模块内部负责：

- 按 session 加载与恢复任务；运行中保守轮询，WS refreshKey 触发即时刷新。
- task 列表、状态与耗时。
- 点击 task 后读取最多 100k 字符输出，展示工具/系统进展和最终报告。
- Agent 续发要求与运行中停止。
- session 切换时清空旧 task/detail，所有控制请求携带 owner `session_id`。

RightRail 只负责放置该模块；tasks 为空时整个区域不渲染。

## 5. 用户界面

任务卡包含：

- 标题：Profile title 或“后台命令”。
- 描述：父 Agent 委派的有界任务。
- 状态：等待中/运行中/已完成/失败/已停止/已中断。
- 元信息：Agent 或 Shell、耗时、运行次数。

点击后显示：

- 工具开始/完成、系统事件与最终报告；不展示隐藏推理。
- 运行中“停止任务”。
- Agent task 的“补充要求”输入与发送；完成后发送会复用 child conversation 重新排队。
- 返回任务列表。

## 6. 安全与恢复

- 所有 REST 操作必须携带 session id，并沿用本地 sidecar token 鉴权。
- Manager 的 owner-session check 是跨会话读取与控制的最终隔离。
- `worker` 仍经 PermissionEngine；GUI 不提供任何授权提升入口。
- 页面刷新后从 `background_tasks`/`background_task_output` 恢复。
- queued/running 在服务重启时仍按 D-171 调和为 interrupted。

## 7. 验收

- `chemical_company_research` / `chemical_market_research` 的匹配 TurnPlan 可见 `start_subagent` 与任务控制工具，并含 delegation guidance。
- 简单化学身份/查价不额外投影 Subagent。
- Manager 对 created/running/output/terminal 发 change；listener 失败不影响 task。
- 父会话 WS 收到 `background_task_changed`；刷新/重连后 REST 返回同一任务。
- RightRail 无任务时不显示区域；有 Agent/Shell task 时显示并可进入详情。
- 输出、停止、Agent 续发、Shell 禁止续发、错误与中英文状态均有 GUI 测试。
- D-165/D-166/D-169/D-171、Permission、Shell、Server、GUI build 回归不新增失败。

## 8. 实施结果

- TurnPlan eligibility、Subagent 工具投影与有界 delegation guidance 已接入单一 Planner seam。
- BackgroundTask change → owner session WS → REST 刷新链路已完成。
- RightRail 已按需显示任务列表与详情，支持停止和 Agent 续发；独立“活动”页未恢复。
- 真实 ApiHub 会话已创建 3 个并行 `research` task；父轮 Provider 超时后任务继续并在右栏可见。
- 真实验收发现并补齐 `research` 对会话产物的只读 `read_file/list_files`，未增加写权限。
- 已完成 Agent task 可从右栏续发；实机验证同一 task `run_count=2`，读取原报告、继续检索并再次完成。
- 聚焦 Python 52 passed、GUI 34 passed、production build 与 compileall 通过；Python 全量仍受既有 Windows ACL 污染约束，未宣称全量通过。
