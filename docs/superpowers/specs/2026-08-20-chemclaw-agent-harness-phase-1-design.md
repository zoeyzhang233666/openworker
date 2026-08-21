# ChemClaw Agent Harness Phase 1 设计规格（D-169）

**状态：已批准，已实施（候选 ON，待独立验收）**

> 2026-08-20 D-170 修订：用户侧“活动/执行诊断”页面无直接业务价值，已删除页面和入口；本规格的后端 Scenario/Capability、Preview/Trace API 与执行守卫继续有效。

## 目标

在现有单一 `TurnEngine` 执行链路上增加声明式 Scenario、业务 Capability、执行预览、内容无关 Turn Trace 和 ToolOutcome 兼容层。D-165 的 `TurnPlanner` 继续是唯一逐轮规划接缝，D-166 的市场口径守卫和 `PermissionEngine` 继续拥有执行权威。

## 边界

- 不引入第二套 Agent Loop、Session、Memory、Permission 或 MCP runtime。
- 不泛化 `explore`，不实现 BackgroundTaskManager、Hook Bus、Verifier、Room、企业微信、插件热加载或自动 Memory extraction。
- 不替换 `MCPManager`、`ToolRegistry`、现有 Event contract 或 GUI 通信协议。
- `scenario_resolution_enabled` 关闭时恢复 D-165/D-166 当前规划、投影与执行行为。

## 单一执行链路

`ScenarioResolver → CapabilityResolver → TurnPlanner → Tool Projection → TurnEngine → 市场守卫 → TurnPlan allowlist guard → PermissionEngine → ToolRegistry`

Scenario 和 Capability 是深模块：上层只依赖 `resolve()` 结果，精确工具绑定、动态 MCP metadata、readiness 和声明式 fallback 保持在模块内部。Scenario 不直接保存工具名。

## 内置模型

所有公开配置与结果模型使用 Pydantic v2，`frozen=True`、`extra="forbid"`，并包含 `version=1`。

- `ScenarioSpec`：分类、示例、必需/可选能力、输出契约、fallback、Subagent 资格和优先级。
- `CapabilitySpec` / `CapabilityProvider`：业务能力及 provider binding、权威性、时效、成本、风险和 fallback 元数据。
- `ScenarioResolution` / `CapabilityResolution`：匹配来源、置信度、候选、readiness 和最终工具集合。
- `TurnPlanPreview`：Scenario、route、能力 readiness、选择/阻止工具、Skill、fallback、预计模型调用数、Subagent 和 warnings。
- `ToolOutcome`：兼容原始工具结果的标准状态摘要。
- `TurnTrace`：仅保存标识、名称、计数、token、阶段耗时、fallback、Outcome 分类和状态。

## 首批目录

Scenario：`chemical_spot_price`、`cn_futures_market`、`chemical_identity`、`chemical_company_research`、`chemical_market_research`。

Capability：`market.price.chemical_spot`、`market.price.cn_futures.quote`、`market.ohlc.cn_futures`、`chem.identity`、`company.identity`、`research.web.search`、`research.web.fetch`、`interaction.clarify`。

## 匹配和歧义

优先级为有效显式 `scenario_id`、D-166 市场/化学确定性 adapter、示例与规则 matcher、General ChemClaw 回落。高置信自动匹配阈值为 `top >= 0.80` 且领先第二名至少 `0.15`；中置信返回 2–3 个候选；低于 `0.50` 不强行分类。

“甲醇最近走势”由市场 adapter 固定返回现货/国内期货澄清，不能被通用 matcher 覆盖。无效显式 Scenario 在 REST 返回 422，在 WS 返回 `input_rejected`。

## 投影、守卫和兼容

- 完整 Scenario 且所有 required capabilities ready 时，Provider 只看到解析出的业务工具和必要控制工具。
- 歧义时只投影 `ask_user` 等必要控制工具。
- required capability 不可用时不开放未声明 Web、期货或现货替代源。
- 无 Scenario 匹配时沿用当前 verified/agent capability pack。
- 通用 allowlist guard 位于市场守卫之后、权限审批之前，并与 Scenario 开关绑定。
- Tool callable 和 `ToolRegistry.execute()` 返回值不变；模型继续看到原始 payload，GUI/Trace 只消费标准 Outcome 摘要。

## Preview、Trace 和 API

Preview 调用真实 Planner/Resolver，但不追加消息、不执行工具、不写 Audit/Trace。已初始化 session 使用 live ToolRegistry；MCP readiness 区分 configured、ready 和 unavailable。

Turn Trace 写入 `coworker.db` 的独立 `turn_traces` 表，与合规 Audit 分离。禁止保存提示词、消息正文、推理、工具参数和工具结果。保留 30 天、全局最多 5000 条，追加后增量清理，列表 API 单次最多 500 条。普通 turn、retry 和 durable resume 各建一条记录，retry 通过 `parent_trace_id` 关联。

接口：

- `GET /v1/scenarios?session_id=...`
- `POST /v1/sessions/{session_id}/plan-preview`
- `GET /v1/turn-traces?session_id=...&limit=...`
- `GET /v1/turn-traces/{trace_id}`

WS `user_message` 增加可选 `scenario_id`；`turn_start` / `turn_end` 只增加向后兼容字段。

## GUI

复用现有“活动”页，提供“工具活动 / 执行诊断”双视图。诊断视图支持 session、请求文本、可选显式 Scenario、仅预览和最近 Trace。首版不增加主页 Scenario 卡片、搜索工作台或用户切 Agent 流程。

## 验收

- 五个核心路由、歧义、fallback、Outcome、Preview 无副作用和内容无关 Trace 均有自动化测试。
- 开关 OFF 与 D-165/D-166 行为一致。
- 现有 Python、GUI 回归和 D-166 聚焦用例通过；组合测试污染必须明确记录。
- 确定性 Scenario/Capability Resolution 1000 次 P95 小于 10 ms；缓存 session 且无 classifier 的 Preview P95 小于 50 ms。
