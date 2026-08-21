# ChemClaw Subagent 自动汇合设计（D-175）

## 1. 目标与边界

主通道：同批后台 Agent 子任务全部到达终态后，harness **主动**向父会话注入一次汇合消息（复用 `deliver_to_session`）。  
兜底：`background_task_status` / 短超时 `background_task_gather` / `background_task_output` 仅用于短查或读报告。  
最终综合只走汇合注入这一条触发通道；禁止把长阻塞 gather 当作最终等待。

不实现 AgentRoom、不引入第二套 Agent Loop、不 vendor 上游 runtime、不恢复「活动」页。

## 2. 上游对照（钉死合同，只吸语义）

| ChemClaw 行为 | 上游参考 | 落地方式 |
|---------------|----------|----------|
| 终态 completion listener | OpenHarness `BackgroundTaskManager.register_completion_listener`（`src/openharness/tasks/manager.py`，main 线与 D-171 钉死 SHA 同合同） | 沿用已有 `register_change_listener`；在 `change=="status"` 且终态时判定 cohort |
| 终态枚举含 failed/cancelled/timeout | DeerFlow `status_contract.py`：`completed\|failed\|cancelled\|timed_out\|polling_timed_out` | ChemClaw 终态：`completed\|failed\|cancelled\|interrupted` 一律算齐 |
| 短轮询超时不作主等待 | DeerFlow `task_tool` poll safety timeout | gather 默认 **60s**，硬顶 1800；政策禁止长阻塞当主路径 |
| 后台完成主动通知父会话 | Claude Code Task：`run_in_background` + harness 完成通知；禁止 sleep-poll | `deliver_to_session` 注入汇合消息；busy→steer，idle→新回合 |
| 并行 fan-in 后由 manager 综合 | OpenAI Agents SDK parallel agents / agent-as-tool | 父会话仍是唯一 Coordinator |
| 单任务 wake_on(job) | 本仓库 `WakeStore.complete_job`（此前未接线） | Agent 终态时调用 `complete_job(task_id)`，并尽快 `resume_due_wakes` |

## 3. DelegationCohort

公开接口：

- `register(owner_session_id, task_id, *, parent_trace_id, profile_id, description)`
- `on_terminal(task_id, *, status, error) -> Optional[CohortReady]`
- `reap_open()`（进程启动后可选：对仍 open 的 cohort 按当前 store 状态再评估）

Cohort 键：`(owner_session_id, parent_trace_id or "")`。同一键下连续 `register` 加入同一批；`synthesis_fired` 后该键关闭，后续 register 开新批。

`CohortReady`：cohort_id、owner_session_id、成员列表（task_id/status/error/profile/description）。只 fire 一次。

仅登记 `kind=="agent"` 的后台任务；Shell 不入 cohort。

## 4. 接线

在 `SessionManager._on_background_task_change`：

1. 保持现有 WS `background_task_changed` 广播。
2. `created` + agent → `cohort.register(...)`。
3. `status` ∈ 终态 → `wakes.complete_job(task_id)`；若有 due wake，在事件循环上调度 `resume_due_wakes`；再 `cohort.on_terminal`；若 ready → `deliver_to_session(owner, 汇合消息, source={kind: subagent_cohort_complete, ...})`。

汇合消息（中文）必须写明：成员终态、请立即综合、勿再长超时 gather、可用短 gather/output 读报告。

## 5. 短查政策

- `background_task_gather(..., timeout_seconds=60)` 默认。
- `_SUBAGENT_DELEGATION_CONTEXT`：启动后继续有用工作；最终综合由系统在全部完成后注入；期间仅短查。

## 6. 验收

- 三任务陆续完成只 deliver 一次；含 failed/cancelled 仍 fire。
- busy 父会话走 steer，不并行第二父轮。
- gather 默认 60。
- `wake_on` + 终态会 `complete_job`。
