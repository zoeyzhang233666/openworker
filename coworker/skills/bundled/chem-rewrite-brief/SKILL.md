---
name: chem-rewrite-brief
description: "Use when 需要把化工/精细化工/贸易素材整理成可约束后续平台改写的 RewriteBrief 事实合同；禁止把常识填进 immutable_facts。"
---

# 化工改写简报（事实合同）

将用户素材与目标平台整理为结构化 `RewriteBrief`。后续 Skill **不得突破**该合同。

## 职责

- 提取 `target_platform`（xiaohongshu / douyin / x）与体裁。
- 区分不可变事实 vs 可修辞部分。
- 未提供字段进入 `unknown_fields`；禁止用模型常识填 `immutable_facts`。
- 数字、CAS、规格、认证、纯度须逐字对齐原文；原文冲突须标记，不得自行择一。
- 缺关键信息时用 `ask_user`；禁止瞎编 CAS/纯度/认证。

## 输出

按 `schemas/rewrite-brief.schema.json` 产出 JSON。详见 `references/fact-boundary-rules.md`。

用户仅要求改写时，**不要**主动联网补产品事实。
