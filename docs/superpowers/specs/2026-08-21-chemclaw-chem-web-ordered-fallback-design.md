# ChemClaw 化工行情 Web 有序降级设计

- 日期：2026-08-21
- 决策：D-181
- 状态：已批准（随实施计划一并落地）
- 依据：甲醇期货产业链套利真机日志；用户确认 MCP/API 空结果允许联网补价

## 1. 问题与目标

D-166/D-177 把「禁止用网页冒充结构化行情」实现成化工现货/国内期货/期现双口径下 **默认 block `web_search`/`web_fetch`**。真机研究任务（产业链/套利方法）与 MCP 空数组（醋酸/PP 现货）因此无法合法联网，子代理反复撞守卫。

目标：保留市场守卫的错口径与交叉替代禁令；化工三口径下 **始终放行 Web 作有序降级**（先结构化，空了再网页并标来源）。

## 2. 范围

**做**：化工 `CHEMICAL_SPOT` / `CN_FUTURES` / `CN_SPOT_FUTURES` 及对应澄清默认 `web_is_supplemental`；重写 `render_market_turn_context`；修订 D-166/D-177 Web 条款；翻转相关测试。

**不做**：拆除市场守卫；A 股/期权网页补价；子代理 TTL；行情缓存；后台 tool result 全文；扩容 chem-data-hub 品种。

## 3. 规则

1. 解析到化工现货、国内期货或期现双口径时，`allowed` 并入 `web_search`/`web_fetch`（不再仅依赖驱动/新闻正则）。
2. Prompt：先调用投影的结构化工具；缺失或空结果才可用 Web 补价或补研究知识；每条 Web 数字须标明网址与时间；不得把 Web 写成 chem-data-hub/交易所官方；不得用现货价顶期货或相反；国内化工对仍禁 Yahoo 冒充。
3. A 股/期权/仅 Yahoo 全球期货路径保持原「驱动才补 Web」语义（本刀不改 D-152）。
4. 子代理经 D-179 继承父 `allowed`（含 Web），可合法联网。

## 4. 验收

见实施计划；聚焦 `test_market_intent` 与受影响的 projection/planner 测试全绿。
