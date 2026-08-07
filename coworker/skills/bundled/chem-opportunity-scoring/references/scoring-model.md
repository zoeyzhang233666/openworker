# 商机评分模型 chem-opportunity-fit@1.0.0

## 权重（合计 100）

| 维度 | 权重 |
| --- | --- |
| signal_recency | 25 |
| entity | 20 |
| sku_relevance | 25 |
| urgency | 15 |
| actionability | 15 |

等级到支持百分比：A=100、B=70、C=35、D=10。极性 supports 加分、contradicts 减分。未知维度不扣商业分，只增加 unscored_weight 并降低证据置信度。

## 状态门禁

- `Actionable` 要求：`entity_resolution=resolved`，至少一条正向无冲突主体信号，SKU 相关为 related，且至少一条信号有非空 `event_date`。
- `NeedsReview` / `Watch` 永不产出 `outreach_now`。
- `Rejected` → `exclude`。

## 来源与占位

source locator 规则与 Lead 评分一致；拒绝 `task-provided:` / `unknown:` / `placeholder:` 前缀。
