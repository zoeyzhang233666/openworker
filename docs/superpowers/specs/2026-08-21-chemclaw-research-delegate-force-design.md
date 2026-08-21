# ChemClaw 研究套利强制委派 + LLM 超时可重试

- 日期：2026-08-21
- 决策：**D-184**（计划稿曾用 D-183；与「思考收起连续可见」冲突后改号）
- 状态：已批准（随实施计划一并落地）
- 依据：沥青期货产业链上下游套利真机日志

## 1. 问题与目标

D-181 已放行化工 Web；真机研究任务仍全程串行（无 `start_subagent`），且中途出现 `APITimeoutError: Request timed out.`。

根因：

1. 「研究…产业链/套利」常落在 `AGENT` 全工具面；`scenario_projection` 不对 AGENT 收窄；主代理可自行串行查价，软委派可被忽略。
2. 流式传输重试不认 timeout；友好错误无中文分层超时文案。

目标：研究 Scenario 命中后强制 `DEEP_RESEARCH` 窄父面，迫使并行委派；LLM 超时无 progress 时重试一次并中文报错。

## 2. 范围

**做**：扩大研究意图正则；TurnPlanner 研究 Scenario 升级 DEEP_RESEARCH；父面 = web + subagent 控制 + 合成写工具，不含行情 MCP/CN；收紧委派文案；timeout 计入 transport retry + 友好错误。

**不做**：compaction 错误流持久化；多轮「写」续匹配；运行时 auto-DAG spawn；MCP 异步流式；拆除市场守卫。

## 3. 规则

1. `_DEEP_RESEARCH_INTENT_RE` / 路由器 `_DEEP_RE` 增加 `上下游`、`套利怎么做`、`研究…套利` 等。
2. matched 且 `allow_subagent` 的研究 Scenario：若 route 仍为 AGENT，升级为 DEEP_RESEARCH（`source=scenario_research`）。
3. 该路径 scenario 投影：Capability + subagent 控制 + `read_file`/`list_files`/`write_file`/`edit_file`/`todo_write`；**不**并回 `market_selection.allowed` 行情工具。
4. 委派政策：禁止主代理开场串行完成现货+期货+文献；≥2 独立分支必须先 `start_subagent`。
5. `APITimeoutError` / `timed out` → 可重试 transport（无 progress 最多一次）；友好错误含「模型接口超时」与 `llm_api` 层级提示。

## 4. 验收

见实施计划；聚焦 scenario/planner/harness + provider 超时测试全绿。须重启 sidecar 后复验沥青研究句右栏 ≥2 research 任务。
