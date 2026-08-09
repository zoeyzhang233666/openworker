# 销售接触纪律（外贸转化首包）

## 草稿 ≠ 发送

- 产出主题/正文/跟进计划后，推荐动作最多到 `ready_for_human_send`。
- 不得暗示已发送、已成交、已寄样，或要求绕过审批。
- **禁止自动外发**。不得在未获用户明确发送指令时调用 `email_send`。
- 用户明确要求发送（含「提交发送审批」CTA）且门禁为 `ready_for_human_send`、收件邮箱可靠时：调用连接器 `email_send`（SMTP 在 Email 连接器，非新建 mail Provider）；仍须审批卡通过后才算发送成功。
- 邮件未连接时如实披露中文错误，引导用户在「连接」中配置 Email（IMAP/SMTP）。

## 岗位策略优先

- 无可靠联系人邮箱时：`recipient_email=null`，写清目标岗位（如 Purchasing Manager / Technical Buyer）与补证建议。
- 禁止用 `task-provided:`、`unknown:`、`placeholder:` 或 `example.com` 伪造成交邮箱。
- 禁止虚构电话模式（`+00`、`000-000`、`555-01`）。

## 多语言草稿

- `language` 与目标市场一致；德/英等可出对应语言草稿，但事实仍须有证据。
- 规格、别名、用途来自 `chem-product-intelligence`，不得臆造认证或牌号。

## 跟进计划

- 每步含日偏移、目的、草稿要点；含停止条件（无回复 N 天、明确拒绝、需改报价等）。
- 未发送前不得把跟进写成“第二次邮件已发出”。

## 质量门禁

运行 `chem-sales-quality-check` 的 `check_outreach.py`；`verdict=blocked` 时修订草稿，不得跳过门禁进入发送审批话术。
