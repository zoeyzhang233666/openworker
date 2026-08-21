# ChemClaw 期现套利双口径放行设计

- 日期：2026-08-21
- 决策：D-177
- 状态：已批准（随实施计划一并落地）
- 修订：D-166 默认单口径；本决策增加显式期现对照例外

## 1. 问题与目标

D-166 把「明确期货」收成单一 `CN_FUTURES` 口径，执行守卫会拦截 chem-data-hub `get_price_trend`。用户做甲醇期货产业链上下游套利、基差或「结合现货」分析时需要同时读取现货与国内期货，却收到「该工具与用户选择的现货/期货市场口径不一致」。

目标：在**明确期现对照意图**时，同一轮同时放行现货 MCP 与国内期货工具；纯单口径查价、裸品种澄清、禁止交叉替代的规则保持不变。

## 2. 领域

新增 `MarketIntentKind.CN_SPOT_FUTURES`（期现双口径）。`MarketToolSelection` 的 `scope_tools` 同时挂载 `CHEMICAL_SPOT` 与 `CN_FUTURES`；`intent.scope` 为 `None`；`allowed_tool_names` 为两套工具并集。`guard_tool` 在双口径下对并集内工具均放行。

双口径**不是**交叉替代：现货仍只来自 chem-data-hub；国内期货仍只来自 `lookup_cn_futures_*`；缺失时写 unavailable，不得用另一口径、Web 或 Yahoo 冒充。

## 3. 触发与不触发

在国内化工品种语境（有 CN 期货品种提及或合约代码），且非 WTI/Brent/A 股/期权优先分支时：

1. 同一句同时出现现货与期货限定（`现货`/`spot` 与 `期货`/`futures`）；或
2. 期现标记：`期现` / `基差` / `basis` / `cash-and-carry` 等；或
3. 期货（或合约代码）+（`套利` 或与价格/产业链相关的 `上下游`）

不触发（保持 D-166）：

- 「甲醇期货现在多少钱」→ 仅期货
- 「甲醇现货价格」→ 仅现货
- 「查甲醇价格」→ 仍澄清
- 仅区域现货套利、无期货限定 → 仍走现货

判定顺序：在单独的「仅现货」「仅 CN 期货」分支之前插入双口径分支。

## 4. Prompt 与 Scenario

`render_market_turn_context` 说明可同时调用两套工具，必须标注来源，禁止把期货价写成现货或反之。

含「产业链/深度研究」等时仍可走 `chemical_market_research`（D-172）；行情工具继续由 `market_selection` 投影与守卫负责，不新建 Scenario，不改 Capability 表。

## 5. 验收

- 「甲醇期货产业链上下游套利」「结合现货看甲醇期货基差」：SPOT 与 `lookup_cn_futures_ohlc` 均 allowed，且 `guard_tool` 均 True
- 纯期货/纯现货/裸甲醇行为与 D-166 回归一致
- 不开放 Web 作价格源；不占用 D-173
