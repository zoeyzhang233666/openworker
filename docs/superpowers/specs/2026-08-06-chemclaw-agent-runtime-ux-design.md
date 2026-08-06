# ChemClaw Agent Runtime 体验与提速（对标桌面端）

**日期**：2026-08-06  
**状态**：规格已批准进入实施（A–C 已在同日落地；本节为里程碑 D 中期方向）  
**范围**：在 OpenWorker 内核上渐进增强（D-031），不整体替换为 OpenCode Runtime。

## 背景

长程化工研究对话出现：MCP 串行空转、上下文压缩失败显示「摘要不可用」、任务进度空壳、本地浏览器自检浪费回合、产物 md 芯片点不开。根因是 Runtime 策略 + 模型调用模式 + UX 缺口叠加，而非单一 MCP 故障。

## 目标

对标 Claude Code / Codex 桌面端的**交互契约**（非抄实现）：

1. 少而准的工具回合；只读查询可并行。
2. 压缩/等待状态对用户可见，避免误判死机。
3. 工作记忆外置且可读；最终产物一键预览。
4. 失败快速降级，不撞已知安全墙（`file://` / loopback）。

## 已落地（A–C，参见 D-075）

- 产物错误中文化并区分缺失类型。
- 禁止用浏览器验证本地产物；强化 `artifact:` 交付链接。
- 只读 MCP → `risk_level=low`，授权后可并行；默认超时 30s（可用 `CHEMCLAW_MCP_TOOL_TIMEOUT` 覆盖）。
- MCP 大回包结构化摘要；`extract_working_state` 记录 MCP 查询。
- Trim 摘要中文化。
- **（2026-08-06 产品决定）** 已撤销用户可见任务进度文件 `._chemclaw/task-progress.md` 与「查看任务进度」入口、引擎自动落盘/MCP 批次追加；压缩续跑改回仅依赖 `<compacted-history>` 等既有通道。

## 里程碑 D：可见计划与运行态（待实现）

### 借鉴来源

| 项目 | 借鉴点 |
|---|---|
| [OpenCode](https://github.com/anomalyco/opencode) | Session compaction epoch、工具结算、压缩进度事件 |
| [Cline](https://github.com/cline/cline) | Plan-then-Act：先可见计划再批量执行 |
| [Aider](https://github.com/Aider-AI/aider) | 严格上下文预算 |
| [Goose](https://github.com/block/goose) | MCP 挂载节制，避免工具 schema 撑爆上下文 |

### 产品行为

1. **研究类智能体默认 Plan-then-Act**  
   - 首轮或阶段开始时用 `todo_write` / 简短计划气泡列出 3–7 步（用户可见）。  
   - 同一阶段内批量只读 MCP，再写阶段结论，最后一份交付产物。

2. **压缩进度可见**  
   - 引擎已有 `COMPACTING` 事件；GUI 显示「正在摘要上下文…」/「摘要失败，已硬裁继续」。  
   - 避免长时间只显示「正在等待 Agent…」。

3. **工具时间线状态机**  
   - 区分：`执行中` / `等待模型` / `正在压缩` / `等待审批`。  
   - 「Waiting for Agent」不得在工具已结束后仍暗示工具卡住。

### 非目标

- 不替换 TurnEngine 为 OpenCode 嵌入 Runtime。  
- 不放开 SSRF / loopback 浏览器防护。  
- 不引入第二套对话系统。

### 验收标准（D）

- [ ] 压缩期间 UI 有明确中文状态，且与工具执行态可区分。  
- [ ] 产业链龙虾长程任务默认先 todo/计划再批量 MCP（提示词 + 可选引擎轻约束）。  
- [ ] 回归：既有 compaction / MCP / 产物测试仍通过。

## 后续实施

见 [2026-08-06-chemclaw-agent-runtime-ux.md](../plans/2026-08-06-chemclaw-agent-runtime-ux.md)。
