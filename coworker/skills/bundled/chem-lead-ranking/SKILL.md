---
name: chem-lead-ranking
description: Use when 需要为已核验的外贸化工客户计算可审计的商业匹配分、证据置信度、优先级或下一步动作；不适用于未核验候选，也不访问网页或外部服务。
---

# 化工客户确定性排序

仅消费 `Qualified`、`NeedsReview` 或 `Rejected` 的已核验 Lead、证据包和版本化规则输入。不得对 `Discovered` 候选评分，不得访问网页、发送消息、写 CRM 或猜测联系人、邮箱、采购量和分数。

先由上游将可追溯证据写成 `EvidenceItem`；六项特征只能引用 `evidence_ids`，不得提交模型自行选择的百分比。载入 Skill 后，运行时提供的绝对 `resources_path` 是脚本与合同的唯一定位根目录；再运行：

```powershell
python "$resources_path/scripts/score_lead.py" input.json --output score.json
```

输入和输出遵循 `$resources_path/schemas/` 中的严格 JSON 合同；固定评分模型见 `$resources_path/references/scoring-model.md`。模型可解释证据和缺口，但不得自由决定数值。未知特征只报告为未知并降低证据置信度，不作为商业匹配的负面事实；只有明确的反向证据才能扣减商业匹配。

不得编造 URL、文件路径、记录号或 `task-provided` 一类占位定位符。用户只描述了事实但未提供可回溯来源时，将其保留为待核验输入并返回上游补证；不得据此构造 `Qualified` 评分。交易、招标、扩产等事件没有明确 `event_date` 时，不得把采集时间当作事件时间，也不得引用到 `signal_recency`。

将 `recommended_action` 作为建议而非外部执行指令。任何联系、发送或写入仍需经过既有权限与审批。
