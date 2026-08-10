# chem-sales-quality@1.0.0

## 硬拒绝

- 收件人邮箱匹配占位模式：`task-provided:`、`unknown:`、`placeholder:`、`example.com` 测试箱当作成交邮箱、明显假地址（无 `@` 却声称 email）
- 正文或字段含虚构电话模式：`+00`、`000-000`、`555-01`
- 无 `price_evidence_ids` 却出现具体单价/总价数字承诺（简单货币金额正则且 `has_price_claim=true`）
- 宣称已发送/已成交/已寄样（`already_sent` / `already_won` / `sample_shipped` 类短语）
- 要求用户绕过审批或忽略权限

## 通过条件

- `channel` 合法；`body`/`subject` 非空
- `recipient_role` 非空；`recipient_email` 可为 null（岗位策略）
- 无硬拒绝项 → `verdict=pass`，`recommended_action=ready_for_human_send`
- `ready_for_human_send` 仅表示可提交人工**发送**审批，不等于已调用 `email_send`
- 另可在同一轮或后续轮助手文案中给出 `ready_for_crm_write`（HubSpot 笔记写入审批门禁，D-105）；不等于已调用 `hubspot_log_note`，且不替代发送门禁
- 另可给出 `ready_for_crm_create_contact`（HubSpot 创建联系人审批门禁，D-109）；须已有可靠 email；不等于已调用 `hubspot_create_contact`
