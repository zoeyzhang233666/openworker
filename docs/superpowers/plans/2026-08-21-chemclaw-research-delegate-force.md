# D-184：研究套利强制委派 + LLM 超时可重试 — 实施计划

> 计划稿标题曾用 D-183；仓库 D-183 已用于思考收起连续性，本刀决策号为 **D-184**。

## 任务

1. 登记 DECISIONS / README / AGENTS；落盘本 design。
2. TDD：沥青/甲醇研究句 → matched + eligible + DEEP_RESEARCH + 父无行情工具 + 有 start_subagent；纯查价不变；timeout 可重试 + 中文错误。
3. 实现 matcher / router / planner / delegation / provider / errors。
4. 聚焦 pytest 全绿并更新 README 状态条。

## 验收

见 design §4 与 Cursor 计划附件验收标准（决策号读作 D-184）。
