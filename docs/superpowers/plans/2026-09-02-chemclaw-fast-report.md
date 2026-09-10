# D-201：快速问答与分阶段市场报告实施计划

## 已实施

- [x] 分离 `TurnOrigin` 与 display-only `source`；普通 Channel 入站按 `user` 路由。
- [x] 增加 `chemical_market_report`、化工现货品名/资讯 Capability 与三轮快速摘要 Profile。
- [x] 增加 `MarketSeriesAggregator`，禁止摘要阶段 shell/临时脚本。
- [x] 通过 BackgroundTask `market_report` Profile 生成 `report.md`，复用 Channel HTML/PNG 富内容交付。
- [x] 增加跨平台进度 upsert、个人微信增量降级、180/240 秒报告收尾，以及 Channel 300 秒超时的 15 秒收尾宽限。
- [x] 修正 Shell timeout outcome 与取消 Trace。

## 验证

- 定向单元/集成回归覆盖周报 Scenario、Channel 来源不再强制 Agent、行情聚合、Shell timeout、取消 Trace 与既有 D-196 Channel 测试。
- 真实 ApiHub CN + chem-data-hub 五轮基准和各 Channel 真机进度验收仍须在重启 sidecar 后执行。
