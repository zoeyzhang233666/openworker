---
name: chem-sales-quality-check
description: "Use when 需要在发送前对化工外贸开发信/跟进草稿做确定性质量门禁；拒绝虚构联系人、价格与绕过审批的话术。"
---

# 销售输出质量门禁

对 `OutreachDraft`（及可选 FollowupPlan）做确定性检查。不访问网页、不发送邮件、不写 CRM。

载入后用绝对 `resources_path` 执行：

```powershell
python "$resources_path/scripts/check_outreach.py" draft.json --output gate.json
```

规则集 `chem-sales-quality@1.0.0`。通过才输出 `ready_for_human_send`；否则 `blocked` 并列出违规项。`ready_for_human_send` 仅表示可提交人工发送审批，**不等于**已调用 `email_send` 或已外发。详见 `references/quality-rules.md`。
