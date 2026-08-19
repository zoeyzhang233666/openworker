# ChemClaw 化工现货与期货路由纠偏设计

- 日期：2026-08-19
- 决策：D-166
- 状态：用户已批准，允许实现

## 1. 问题与目标

D-165 把每轮工具投影接入生产入口后，旧的关键词规则开始真实裁剪工具：普通“价格”只留下 Web，而“甲醇”等期货品种别名会在用户明确写“现货”时仍选择国内期货工具。与此同时，chem-data-hub 的动态 MCP Tool 不在静态 VERIFIED 工具表内，因而被裁掉。

D-166 的目标是把“市场口径”从品种识别中分离：明确现货只能读取 chem-data-hub，明确期货才读取对应交易市场；同时存在现货与期货口径的裸品种问价必须先澄清。Web 可补充新闻和驱动证据，但不能替代结构化行情价格。

## 2. 领域与接口

新增不可变 `MarketIntent` 与 `MarketToolSelection`，作为行情意图到 Provider-visible Tool 的唯一 seam。`MarketIntent` 表达非行情、化工现货、国内期货、全球期货、上市证券和待澄清；`MarketToolSelection` 同时返回候选 Tool、分口径 Tool 集合、澄清选项和能力可用状态。

判定优先级固定为：

1. 明确“现货/spot”或“期货/合约”等市场口径；
2. 交易所、连续/主力合约和标准代码；
3. 权威品种名与别名；
4. 同时存在多种口径时进入澄清，不以品种名猜市场。

国内期货品种检测复用 `coworker.cn_market.symbols` 的目录，不在路由层维护第二份甲醇/液化气等正则清单。chem-data-hub Tool 通过 MCP 元数据中的 server capability 与远端 Tool 名 `get_price_trend` 识别，兼容连字符和下划线规范化。

## 3. 工具与执行策略

- 化工现货：只暴露 chem-data-hub `get_price_trend`。缺失时工具集合为空并报告 unavailable，禁止回退 Web、Yahoo 或期货。
- 国内期货：普通查价/走势暴露 quote + daily OHLC；分钟、L1、保证金仅在用户明确需要时增加。
- WTI/Brent 与 `CL=F`/`BZ=F`：使用 Yahoo OHLC。
- 新闻、事件或驱动分析：可在正确价格 Tool 之外增加 Web；Web 不得成为价格源。
- 待澄清：暴露 `ask_user` 与可能的市场工具集合，但 Engine 在澄清前禁止行情 Tool 执行；回答后只放行所选口径，之后仍经过原权限与审批。

`TurnEngine.run()` 外部接口不变。`TurnPlan` 增加市场意图/策略；每轮澄清解析状态是临时执行状态，不修改不可变计划，也不扩大权限。

## 4. Prompt 与失败语义

VERIFIED 行情 prompt 先说明市场口径，再说明品种和图表：用户写“现货”时，甲醇、原油等别名不能覆盖口径；国内期货示例必须包含“期货”或合约代码。chem-data-hub 不可用或返回空数据时分别说明“连接未提供现货工具”或“暂无现货数据”，不得联网补价。

## 5. 验收

- 原油现货、甲醇现货只调用 chem-data-hub MCP。
- 甲醇期货、MA 合约只调用国内期货工具。
- WTI/Brent 期货只调用 Yahoo OHLC。
- 裸甲醇/原油问价先澄清，澄清前零行情调用，澄清后只放行所选口径。
- MCP 缺失或空结果不触发 Web/期货补价。
- Router/Projection kill switch、权限审批、D-165 FAST、CN 行情与 Chart 行为保持兼容。
