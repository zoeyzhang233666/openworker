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
