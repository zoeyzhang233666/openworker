# 质量门禁规则（chem-content-quality@1.0.0）

## fact_integrity

- `immutable_facts` 中非空的 cas / purity / packaging / product_name 必须出现在输出中（原文提供才检查）。
- `numeric_claims` 中每条声明须在输出中保留（子串匹配）。
- 不得出现与 brief 冲突的改写数值（例如纯度从 99.5% 变成 99.9%）。

## policy_scan

- 任一 `severity=block` 的 policy hit → 不得 `pass`。
- `blocked` 若存在 block 且未改写干净。

## platform_fit

- 输出须包含平台要求的章节标题（如【标题】【正文】等），由调用方传入 `required_sections`。

## independent_expression

- 保守：仅当最长连续公共子串过长（排除纯规格短串）时标记需修订。
- 不得为降重修改事实字段。

## recommended_action

- `pass` → `ready_for_publish_review`
- 否则 → `revise` 或保持披露，禁止宣称已发布。
