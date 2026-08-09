# 询盘转报价纪律

## 不编造价格

- 单价、数量必须来自用户输入或已审证据；缺失则 `NeedsReview` / `await_inputs`。
- 合计只通过平台 Tool `calculate_quote`；禁止心算改写 grand_total。

## 草稿 ≠ 发送

- `QuoteDraft` 仅供人工审阅；推荐动作最多到 `ready_for_human_review`。
- 不得宣称已报价发出、已成交；不接 SMTP。

## 与 MCP 边界

- 本包不依赖 `chem-inquiry-feed` / `chem-quote-monitor`。
- 询盘来源可以是用户粘贴文本、本地文件或对话字段。

## 占位与审批

- 拒绝 `task-provided:` / `unknown:` / `placeholder:` 伪 locator。
- 外发与 CRM 写入须走现有审批。
