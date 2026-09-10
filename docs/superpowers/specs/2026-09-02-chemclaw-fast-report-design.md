# D-201：快速问答与分阶段市场报告设计

## 目标

普通 Channel 用户消息与桌面用户消息采用同一 TurnOrigin=`user` 路由，不因展示来源卡片降级为全工具 Agent。化工市场周报、日报、月报先在受限工具面生成快速摘要，再异步完成 `report.md` 和 Channel 富内容交付。

## 接缝

- `TurnOrigin` 是 Planner 的执行来源；`source` 继续只是持久化/GUI 展示 sidecar。
- `chemical_market_report` 是确定性 Scenario，前台使用 `REPORT_SUMMARY` 提示和三轮上限；不得开放 shell、写文件或 Skill。
- `MarketSeriesAggregator` 是原始行情回包到有界摘要/ChartSpec 的深模块；模型不读取大回包或编写解析脚本。
- 后台报告复用既有 BackgroundTask/Subagent Runtime；`market_report` Profile 只允许报告所需的网页、共享工作区和已继承 chem-data-hub 工具。
- `Gateway.upsert_progress()` 是各 Channel 的进度交付接缝：企微优先流式原位刷新，个人微信明确为增量气泡，其他适配器有编辑能力时更新，否则降级。

## 时限与终止

前台摘要最多三轮模型调用；后台在 180 秒请求收尾、240 秒强停。Channel FIFO 到期先注入收尾请求并给 15 秒宽限，取消时必发终态；Trace 将取消记为 interrupted，Shell `timed_out` 记为 failed。
