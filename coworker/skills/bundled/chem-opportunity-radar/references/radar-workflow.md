# 商机雷达工作流规则

## 信号收集

只接受可回溯来源：用户文件、已打开网页 URL、公开招标/登记号。用户只说“最近有招标”时进入补证，不创建伪造信号。

`OpportunitySignal` 字段最小集：`signal_id`、`signal_type`、`summary`、`event_date`（可空）、`collected_at`、`source`、主体提示。缺 `event_date` 的事件不得支撑时效维度。

## TED 招标信号（平台 Tool）

- **默认路径**：调用 `search_tenders`（query / 可选 buyer_country / cpv）收集欧盟公开招标。
- 返回行已是 `signal_type=tender` 与 `signal_id=ted:<publication-number>`；`source.url` 必须保留。
- 不得改写或捏造 publication-number；empty/error 时进入补证或空清单 `complete`，不得假装有标。

## SAM.gov 招标信号（平台 Tool）

- **境外可选**：仅当用户明确要美国联邦标且已配置 `sam:default` 时调用 `search_sam_opportunities`。
- 返回行 `signal_id=sam:<noticeId>`；无 noticeId 的行不得编造；empty/error/未配置时如实披露并改走 TED/网页搜索，不以申请密钥为刚需。

## 归一与相关

主体归一与冲突规则复用 `chem-company-qualification` 精神；SKU/应用相关复用 `chem-product-intelligence`。集团/工厂/品牌保留关系。

## 评分与动作

调用 `chem-opportunity-scoring`（`chem-opportunity-fit@1.0.0`）。`Actionable` 才可建议 `outreach_now`；`NeedsReview` → `research_first`；空信号清单合法结束。

## 禁止

- 默认挂载或强依赖 MCP 询盘/新设 Skill（`chem-inquiry-feed`、`chem-newbiz-lead`）
- 占位 locator（`task-provided:` / `unknown:` / `placeholder:`）
- 自动外发或写 CRM
