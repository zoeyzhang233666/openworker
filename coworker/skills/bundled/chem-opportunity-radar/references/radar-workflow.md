# 商机雷达工作流规则

## 信号收集

只接受可回溯来源：用户文件、已打开网页 URL、公开招标/登记号。用户只说“最近有招标”时进入补证，不创建伪造信号。

`OpportunitySignal` 字段最小集：`signal_id`、`signal_type`、`summary`、`event_date`（可空）、`collected_at`、`source`、主体提示。缺 `event_date` 的事件不得支撑时效维度。

## 归一与相关

主体归一与冲突规则复用 `chem-company-qualification` 精神；SKU/应用相关复用 `chem-product-intelligence`。集团/工厂/品牌保留关系。

## 评分与动作

调用 `chem-opportunity-scoring`（`chem-opportunity-fit@1.0.0`）。`Actionable` 才可建议 `outreach_now`；`NeedsReview` → `research_first`；空信号清单合法结束。

## 禁止

- 默认挂载或强依赖 MCP 询盘/新设 Skill（`chem-inquiry-feed`、`chem-newbiz-lead`）
- 占位 locator（`task-provided:` / `unknown:` / `placeholder:`）
- 自动外发或写 CRM
