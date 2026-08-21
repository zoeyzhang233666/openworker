# ChemClaw 研究效率首包硬伤修复设计

- 日期：2026-08-21
- 决策：D-179
- 状态：已批准（随实施计划一并落地）
- 依据：甲醇期货产业链上下游套利研究复盘日志

## 1. 问题与目标

研究子智能体在长工具链后失败于 ApiHub「Upstream rejected…invalid」、父子市场口径不一致、OHLC `TOOL_FINISHED` 事件名被品种名覆盖、以及 Windows 编码/`grep` 缺失导致 extract 脚本空转，使同类任务远慢于 Claude Code。

目标：父子口径一致；invalid 请求压缩重试一次并可 salvage；事件流工具名正确；research 可 `grep`；Windows shell 默认 UTF-8；cowork 优先读工具挖中文文本。

## 2. 范围

**做**：市场口径继承、provider invalid 重试/salvage、chart sidecar 键名、research `grep`、shell UTF-8、cowork 提示。

**不做**：MCP 价格超时/缓存、主会话全量 tool-trace、独立 wall-time 预算（第二刀）。

## 3. 设计

### 3.1 市场口径继承

`start_subagent` 从父 `TurnEngine` 快照 `market_selection`（含 D-177 `CN_SPOT_FUTURES`）写入 task metadata。子引擎注入 `_inherited_market_selection`；规划时优先使用继承选择，禁止因短 task 回落 CLARIFY 或单口径。子任务显式限定只能收紧 ⊆ 继承面，不可放宽。

### 3.2 Upstream invalid 恢复

新增 `is_retryable_provider_reject`（匹配 upstream rejected / request as invalid）。捕获后强制 compact 一次再 stream；仍失败则 Emergency Finalization（tools off）+ 中文友好错误。research 指令：先 `write_file` 报告，再短气泡收尾。

### 3.3 Chart sidecar

`chart_finished_sidecar` 用 `series_name` 代替顶层 `name`。GUI 把 `series_name` 映射进 preview JSON 的 `name`，短引用匹配不变。

### 3.4 效率补丁

research allowlist 增加 `grep`；Windows shell 设 `PYTHONUTF8`/`PYTHONIOENCODING` 与 Console UTF-8；cowork：UTF-8 文本优先 `grep`/`read_file`，禁止为中文匹配手写 PowerShell 单行。

## 4. 验收

见实施计划验收标准；聚焦测试全绿；不削弱 D-166 交叉替代禁令。
