---
name: uncertainty-and-units
description: "Use when 询盘规格、报价、检测或工艺数字涉及物理单位换算、测量不确定度、有效数字或数量级合理性检查；不用于拓客 Lead 评分，也不访问外网。"
license: MIT
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
  chemclaw-source: "D:/化工社skills合集 (K-Dense scientific-agent-skills mirror)"
---

# 单位与不确定度（ChemClaw）

上游为 K-Dense `uncertainty-and-units`（MIT），经化工社开放技能库合集引入 ChemClaw。用于**销售辅助的计量与数字可信**，不是科研主轴，也**不得**写入 Lead Fit / 拓客评分主流程。

载入后，运行时给出的绝对 `resources_path` 是脚本与 references 的唯一定位根。需要跑脚本时用 Shell（须既有权限/审批），例如：

```powershell
python "$resources_path/scripts/audit_units.py" --help
python "$resources_path/scripts/convert_units.py" --help
```

## ChemClaw 边界

- **适用**：询盘数量单位、浓度/纯度换算核对、检测报告不确定度表述、报价相关数字的数量级 sanity check。
- **不适用**：企业发现、主体核验、Lead 排序、商机评分、自动发邮件/写 CRM。
- **禁止编造**：不得用本 Skill「补全」缺失单价、数量或规格；缺字段仍走 `NeedsReview`。
- **无网络**：脚本应本地运行；不要为跑本 Skill 去下载额外数据源。
- **依赖**：`scripts/audit_units.py` 仅标准库。单位换算/不确定度传播等数值 CLI 需要可选依赖 `pint`、`uncertainties`（见 `pyproject.toml` extra `uncertainty`）。缺依赖时用中文说明并降级到文字规则与 `audit_units`，不要假装已算出数值。
- 上游英文 references 仍在 `references/`；ChemClaw 用法见 `references/chemclaw-usage.md`。

## 工作原则（摘要）

1. 输入带单位，只在输出处去单位。
2. 先写清测量/换算模型，再计算。
3. 每个带不确定度的输入尽量有估计值、标准不确定度、分布与自由度。
4. 先圆整不确定度，再圆整对应有效位；写明 `±` 是标准还是扩展（含 `k`）。
5. 量纲正确仍可能不合理：做数量级/无量纲数核对。

详细方法与库用法见上游 `references/*.md`。报价合计仍必须走平台 Tool `calculate_quote`，本 Skill 只辅助单位与不确定度，不替代计算器。
