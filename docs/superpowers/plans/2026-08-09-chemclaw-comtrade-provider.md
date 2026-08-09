# ChemClaw Comtrade TradeFlowProvider（D-103）

**Goal:** 国家 / HS 贸易流只读查询，辅助选市场与出口叙事；**不**直接产买家名单。

**Architecture:**
- 平台 `coworker/trade/`：`ComtradeProvider` + Tool `lookup_trade_flow`
- UN Comtrade final-data API；SecretStore `comtrade:default`（`api_key`）
- Fixture 契约测试；挂外贸拓客 / 产品情报文档接线（不嵌客户端）

**Status (2026-08-09):** 已完成（D-103）。

## Tasks
- [x] `ComtradeProvider` + Fixture 契约测试
- [x] Tool `lookup_trade_flow` + `build_engine` 注册
- [x] 无密钥中文错误；结果含非买家警告
- [x] Skill/龙虾文档接线
- [x] D-103 / README / GATE / 规格

## Out of Scope
- TED 重做、买家爬取、CRM、海关企业级数据
