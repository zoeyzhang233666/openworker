# ChemClaw 按需上下文与 ApiHub Flash 真流式设计

- 日期：2026-08-19
- 决策：D-165
- 状态：用户已批准，允许实现

## 1. 问题与目标

Router v5 的 rollout 只启用了配置默认值；真实 `SessionManager -> build_engine -> TurnEngine.run` 路径没有为每轮请求生成并应用 `ExecutionProfile`。因此问候虽然可被 `RequestRouter` 判为 `FAST_CHAT`，实际请求仍携带完整 system prompt、技能目录和 provider-visible 工具 schema。ApiHub Flash 的 exact-pair allowlist 只决定“带工具时可否真流式”，不能降低前置上下文或替代每轮路由。

D-165 的目标是建立一个深模块：调用方仍只调用 `TurnEngine.run(user_input)`，所有路由、prompt、Skill、工具和 reasoning 策略在一次 `TurnPlanner.plan(...) -> TurnPlan` 中完成。全新默认会话的问候必须零工具、零技能目录、直接流式，并把实际 prompt token 控制在 4k 内；不确定和有副作用的请求保守回退完整 Agent 能力。

## 2. 运行接口

`TurnPlan` 是不可变的本轮执行合同，至少包含：

- `decision`：路由来源、原因与守卫结果；
- `execution_profile`：迭代预算、工具启用和 Provider reasoning 请求意图；
- `tool_policy`：本轮显式工具约束；
- `prompt_profile`：legacy、FAST、KNOWLEDGE、VERIFIED/行情、定向 Agent、普通工作区、可视化工作区或 Deep；
- `show_reasoning`：是否把 Provider 已返回的 reasoning 实时展示，独立于 Provider 请求参数；
- `skill_names`：本轮可见的 Skill 元数据候选，不含完整指令正文。

`TurnPlanner` 持有 `RequestRouter`，以便同一会话延续 `last_route`。`TurnEngine.run()` 在写入本轮 user message 前生成 `_active_turn_plan`，整轮所有 model iteration 使用同一计划，并在结束时清除；retry 复用上次计划。显式传入的 legacy `execution_profile` 仍作为测试/直接调用 override。

## 3. 保守路由与投影

- 问候、感谢和身份询问使用 `FAST_CHAT`。
- 只有能正向证明无需工具的稳定知识才使用 `KNOWLEDGE`。
- 已有确定性实时 Provider 的查询使用 `VERIFIED` 与目标工具集合。
- 附件、工作区动作、Plan/Discuss、pending/durable resume、默认或强制 Skill、非默认 Persona、后台调度/自唤醒和任何不确定请求均使用 `AGENT` 或 `DEEP_RESEARCH`。
- 工具 registry 永不被投影永久修改；kill switch OFF 或无法安全分类时发送 legacy 全量 schema。

Prompt 按稳定顺序由 section 组装。FAST 只包含 ChemClaw 核心身份、默认中文、安全边界、用户规则和预算内记忆；不包含长任务、工具批处理、Mermaid、Chart、环境/AGENTS 或 Skill catalog。工作区、图表和领域指南只在相应 route/intent 下加入。

技能目录不再全量常驻：FAST/KNOWLEDGE 为零；显式/default Skill 保留；普通任务最多加入 8 个本地相关候选。`search_skills(query, limit)` 只返回启用 Skill 的名称和描述，完整正文仍由 `load_skill(name)` 在调用时读取最新有效版本。

## 4. Reasoning 与流式语义

`ExecutionProfile.reasoning_mode` 仅表达向 Provider 请求的模式。只有能力矩阵明确支持关闭 reasoning 时才发送关闭参数。`show_reasoning=True` 表示 Provider 只要产生 `reasoning_content`/`reasoning`，Engine 就立即广播 `reasoning_delta`；不得因为 FAST 请求了 off 就静默隐藏仍在计费的 reasoning。

FAST/KNOWLEDGE 在工具投影启用时发送 `tools=None`，因此走 OpenAI-compatible Provider 的 `direct` 真流式路径，不依赖 structured-tools allowlist。带工具路径继续使用 D-161—D-164 精确 `(hostname, model)` 对表；未知 host/model 保持 buffered + salvage-safe。

## 5. 兼容、回退与安全

- `request_routing_enabled=false`：不创建新计划，恢复 legacy 请求执行。
- `tool_projection_enabled=false`：保留路由观测，但发送全量 schema。
- `prompt_projection_enabled=false`：发送旧完整 prompt 与技能目录。
- 旧会话不重写已持久化 system message；新 prompt policy 只用于带版本标记的新会话。
- 任何投影都不能绕过 `PermissionEngine`、审批、MCP/connector 会话过滤或 durable pending 状态。
- 性能日志只记录枚举、计数、字节数和延迟；禁止记录 prompt、消息正文、工具结果或秘密。

## 6. 验收

全新默认会话、无附件、用户规则与相关记忆合计不超过 1k token 时，ApiHub Flash 连续 5 次“你好”须满足：实际 `prompt_tokens <= 4000`、provider-visible tools=0、skill catalog=0、`stream_mode=direct`、无 complete fallback、首个 reasoning 或 text 事件 P50<=3s / P95<=8s。长答须在完成前出现至少 3 个正文 delta。外部网络不可用只记 `ENV_BLOCKED`，不能替代离线回归。
