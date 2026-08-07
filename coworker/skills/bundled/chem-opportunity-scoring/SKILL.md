---
name: chem-opportunity-scoring
description: "Use when 需要对已规范化的化工商机信号计算可审计的商机分、证据置信度或下一步动作；不适用于无来源口述，也不访问网页或外部服务。"
---

# 化工商机确定性评分

仅消费已规范化的 `OpportunitySignal` 与商机草稿输入。不得访问网页、发送消息、写 CRM，不得猜测联系人、成交概率或分数。

载入本 Skill 后，用运行时返回的绝对 `resources_path` 执行：

```powershell
python "$resources_path/scripts/score_opportunity.py" input.json --output score.json
```

输入输出遵循 `$resources_path/schemas/`；固定模型见 `$resources_path/references/scoring-model.md`。权重固定为时效 25 / 主体 20 / SKU 相关 25 / 紧迫度 15 / 可行动性 15（`chem-opportunity-fit@1.0.0`）。

不得编造 URL、文件路径、记录号或 `task-provided` 一类占位定位符。用户只口述“有招标/询盘”但未提供可回溯来源时，保持 `NeedsReview`/`Watch`，不得标为 `Actionable`。事件缺少明确 `event_date` 时，信号时效计为 0，不得用采集时间冒充事件时间。
