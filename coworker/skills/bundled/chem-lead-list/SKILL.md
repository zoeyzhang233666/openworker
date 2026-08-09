---
name: chem-lead-list
description: "Use when 外贸或内贸拓客已有评分结果，需要产出可经营的客户清单 Markdown/CSV（可联系/待补查/已排除）。"
---

# 客户清单交付

把已核验/已评分 Lead 收成可继续经营的清单，而不是长篇研究报告。使用平台 Tool `format_lead_list` 生成 Markdown 与 CSV；**不**自动外发、不写 CRM。

## 输入

- 来自 `chem-lead-ranking` / 拓客 Run 的企业、双分、匹配原因、证据摘要、风险缺口、建议动作。
- `sales_status`：`new` / `needs_review` / `contactable` / `contacted` / `replied` / `opportunity` / `excluded`。
- 已排除必须保留 `exclude_reason`，防止重复搜索。

## 纪律

- 无可靠联系人时只写岗位策略，不编造姓名/邮箱。
- 拒绝 `task-provided:` 占位 locator。
- 清单是人工经营对象；发送须另走审批（本 Skill 不提供发送）。

合同见 `schemas/lead-list.schema.json`。详见 `references/lead-list-discipline.md`。
