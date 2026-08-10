# ChemClaw 用法导读

本目录其余 `references/*.md` 保持 K-Dense 上游英文原文，便于溯源。

在 ChemClaw 中：

1. 仅在询盘/报价/规格数字出现单位或不确定度疑义时 `load_skill("uncertainty-and-units")`。
2. 优先用 `scripts/audit_units.py`（无第三方依赖）做静态单位审计。
3. 需要数值换算或不确定度传播时，确认环境已安装可选 extra `uncertainty`（`pint`、`uncertainties`）；否则向用户中文说明并停止数值 CLI，不要编造结果。
4. 不把输出当作 Lead 证据等级或 Fit 分；不自动外发、不写 CRM。

上游：K-Dense Scientific Agent Skills · MIT · 经 `D:\化工社skills合集` 引入。
