# ChemClaw 双模式停止 + 主任务超时可恢复设计

- 日期：2026-08-21
- 决策：D-187
- 状态：已批准（随实施计划一并落地）

## 1. 问题与目标

研究子任务被 `stop` 后常在约 3 秒内 `force-cancelled`，智能体/系统停任务时来不及写部分报告。主任务长轮频繁 `APITimeoutError: Request timed out.`（流式 read=120s），即使用户未点停止也会裸 ERROR。

目标：用户手动停止立刻硬停；智能体/系统停止先催收尾；主/子超时加长等待，有工具产物时 EF salvage。

## 2. 范围

**做**：`stop(mode=immediate|wrap_up)`；GUI immediate；`background_task_stop`/系统 wrap_up；流式 read≥300s；timeout + 已有工具 → 一次 EF。

**不做**：空闲看门狗、硬 TTL 主动杀任务、拆除市场守卫、改 ApiHub 网关。

## 3. 设计

### 3.1 双模式 stop

| mode | 调用方 | 行为 |
|------|--------|------|
| `immediate` | GUI 右栏、HTTP 用户入口默认 | cancel + stop + 等 ~3s → force-cancel；无 wrap-up steer |
| `wrap_up` | `background_task_stop`、前台超时系统停 | steer 收尾 + `wrap-up requested`；等 ~90s；再 hard stop。Shell 退化为 immediate |

### 3.2 超时

- Provider 流式 `read=300`
- Engine：`is_provider_timeout` 且本轮有 tool/部分正文且 EF on → 一次 `_emergency_finalizing` salvage

## 4. 验收

见实施计划与 Cursor 计划附件。
