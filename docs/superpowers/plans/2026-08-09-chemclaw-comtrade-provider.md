# ChemClaw Comtrade TradeFlowProvider Implementation Plan（待点名后实现）

> 队列 C；**未获用户「开始实现 Comtrade」前不写业务代码。**

**Goal:** 国家 / HS 贸易流只读查询，辅助选市场与出口叙事；**不**直接产买家名单。

**Architecture（拟定）：**
- 平台 `coworker/trade/`：`ComtradeProvider` + Tool `lookup_trade_flow`
- UN Comtrade API（密钥进 SecretStore）；Fixture 契约测试
- 挂外贸拓客 / 产品情报 references，不写进 Skill 客户端

**验收：** 无密钥中文错误；有密钥返回规范化流量指标 + 来源；禁止把贸易流行当作成交买家。

**Out of Scope：** TED、买家爬取、CRM。
