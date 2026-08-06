# ChemClaw Agent Runtime UX 提速 — 实施计划（里程碑 D）

> **For agentic workers:** A–C 已在 2026-08-06 落地（见 D-075）。本文件只拆 **里程碑 D**。按任务顺序执行；每个 Task 先写失败测试再改代码。

**规格**：[`docs/superpowers/specs/2026-08-06-chemclaw-agent-runtime-ux-design.md`](../specs/2026-08-06-chemclaw-agent-runtime-ux-design.md)

---

### Task 1: 压缩/等待状态中文化与时间线区分

**Files:**
- Modify: `surfaces/gui/src/components/Transcript.tsx`（或步骤组渲染处）
- Modify: `surfaces/gui/src/interfaceMessages.ts`
- Test: `surfaces/gui/src/components/Transcript.test.tsx`

**Steps:**
1. 将 `COMPACTING` / trim notice 映射为「正在摘要上下文…」「摘要失败，已硬裁继续」。
2. 工具全部结束后、下一轮模型未返回前，状态文案为「等待模型回复…」，勿继续强调 MCP。
3. 跑定向前端测试。

---

### Task 2: 研究智能体 Plan-then-Act 提示强化

**Files:**
- Modify: `coworker/personas/builtin/chain-lobster.md`
- Modify: `coworker/agent.py`（可选全局一句）
- Test: 既有 `test_chain_lobster.py` / prompt 快照类测试

**Steps:**
1. 要求阶段开始先 `todo_write` 3–7 步；同阶段只读 MCP 尽量同一轮批量提出。
2. 禁止为本地预览启动 http.server / browser（A 已写；此处复核）。

---

### Task 3:（可选）引擎侧轻量计划门闩

**Files:**
- Modify: `coworker/engine.py`
- Test: 新测「首轮长研究无 todo 时注入提醒」

仅在 Task 2 提示词不足时启用；默认不阻塞 turn。

---

### Task 4: 文档闭环

更新 `docs/chemclaw/README.md` 与 `DECISIONS.md`（D-076 若新增行为）。
