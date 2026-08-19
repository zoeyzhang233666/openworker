# D-166 化工现货与期货路由纠偏实施计划

**Goal:** 让明确现货稳定选择 chem-data-hub，让明确期货选择正确市场，并在裸品种问价时先澄清。

**Architecture:** `resolve_market_tools(...) -> MarketToolSelection` 是行情语义深模块；`TurnPlanner` 只消费结果并写入不可变 `TurnPlan`，Engine 只执行计划中的口径守卫。

## Gate 1 — 领域与选择 seam

- [x] 写入 D-166 规格、计划、决策和领域术语。
- [x] 国内期货品种检测复用权威 symbol 目录。
- [x] 新增 `MarketIntent` / `MarketToolSelection` 与动态 MCP 元数据识别。

## Gate 2 — Planner、Prompt 与执行守卫

- [x] VERIFIED 工具投影改用市场选择结果。
- [x] `TurnPlan` 携带市场意图与分口径 Tool 集合。
- [x] 待澄清请求使用 `ask_user`；执行层在回答前后强制正确口径。
- [x] Prompt 明确现货优先和 unavailable 语义。

## Gate 3 — 回归与真实链路

- [x] 路由、投影、Engine、Prompt、MCP、CN 行情与 D-165 回归通过。
- [x] GUI 验证原油现货、甲醇现货、甲醇期货、裸甲醇澄清的实际 Tool 事件。
- [x] 更新 README、DECISIONS、DOMAIN、AGENTS 与执行日志。
