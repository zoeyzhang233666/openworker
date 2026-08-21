# D-187：双模式停止 + 主任务超时可恢复 — 实施计划

## 任务

1. 登记 DECISIONS / README / AGENTS / DOMAIN；落盘 design。
2. TDD：immediate / wrap_up；read≥300；timeout+tool → EF。
3. 实现 manager.stop(mode)、接线、provider、engine。
4. 聚焦 pytest 全绿并更新 README 状态条。

## 验收

见 design §4 与产品决定：手动立刻停；智能体/系统先收尾；超时可 salvage。
