# D-200：个人微信中途过程流实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 个人微信在最终回答前可见工具过程提示，并更早发出正文分段。

**Architecture:** 仅改 `SessionManager.deliver_to_session` 微信流编排：新增 `_weixin_progress`，在 `tool_started`/`error` 发多气泡过程消息；降低 `WEIXIN_STREAM_MIN_CHARS`。不改 iLink adapter API。

**Tech Stack:** Python asyncio、pytest、既有 Channel envelope 投递。

---

### Task 1: 规格与文档骨架

- [ ] `docs/superpowers/specs/2026-09-01-chemclaw-weixin-midturn-progress-design.md`
- [ ] 本计划文件

### Task 2: 失败测试先行

- [ ] 在 `tests/test_channel_interaction_d196.py` 增补：
  - 假 `engine.run`：`tool_started` ×2（同窗）→ 长 `assistant_delta` → `assistant_message`
  - 断言：progress「正在处理」→ 恰好一条「正在调用」→ stream_chunk → final 不重复前缀
  - 假 `engine.run`：`error` → 断言中文错误气泡

### Task 3: 实现 manager 微信过程流

- [ ] `_weixin_progress` + 节流状态
- [ ] `tool_started` 同时服务 wecom / weixin
- [ ] `error` 服务 weixin
- [ ] `WEIXIN_STREAM_MIN_CHARS = 80`

### Task 4: 回归与门禁文档

- [ ] 定向 pytest + D-199 子集
- [ ] `DECISIONS.md` D-200、`README.md`、`DOMAIN.md` 个人微信增量流段落
