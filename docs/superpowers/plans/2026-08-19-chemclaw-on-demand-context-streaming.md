# D-165 按需上下文与 ApiHub Flash 真流式实施计划

**Goal:** 把 Router/Profile 接入所有 `TurnEngine.run()` 路径，并按本轮请求投影 prompt、Skills 与 tools；Provider reasoning 有则实时展示。

**Architecture:** 以 `TurnPlanner.plan(...) -> TurnPlan` 为唯一 seam。Engine 持有当前不可变计划，Provider、prompt assembler、Skill resolver 与 tool projector 只消费该计划；WebSocket、后台投递和自动化调用方不复制策略。

## Gate 1 — 每轮路由与 reasoning

- [x] 新增 `TurnPlan` / `TurnPlanner` 及接口测试。
- [x] `build_engine` 注入 planner，`TurnEngine.run` 激活/清除 per-turn plan，retry 复用。
- [x] pending、Persona、Skill、附件、后台与模式守卫保守回退 Agent。
- [x] reasoning 请求模式与展示模式解耦。
- [x] 本地 GUI WebSocket 验证问候实际 `FAST_CHAT + tools=None`；ApiHub `direct` live 见 Gate 3 PASS。

## Gate 2 — Prompt、Skill 与工具按需投影

- [x] 新增独立 `prompt_projection_enabled` kill switch（候选 ON）。
- [x] 拆分稳定 prompt profiles；FAST/KNOWLEDGE 排除重型指南与环境。
- [x] Skill catalog 按 route/相关性投影，普通候选最多 8 个，显式/default 始终保留。
- [x] 新增 `search_skills(query, limit<=8)` 元数据 Tool，`load_skill` 仍加载最新正文。
- [x] VERIFIED 与强意图 AGENT 使用正向工具能力包；未知动态工具回退全量 registry。
- [x] 新会话 prompt policy v1 标记；旧会话保持 legacy；重载保留标记。

## Gate 3 — 可观测性与验收

- [x] 记录 prompt/tool/skill 计数、实际 token、stream mode、首包、reasoning、retry/fallback。
- [x] 路由、投影、权限、审批、Memory、Skill、调度、Stop、压缩和 durable resume 回归；MCP 写凭据用例受 Windows ACL 环境阻塞，读路径通过。
- [x] 全新会话离线请求快照满足 4k 预算结构门禁。
- [x] ApiHub Flash GUI/WebSocket live N=5：PASS；问候 85 prompt tokens、tools/skills=0、direct=6/fallback=0、TTFT P50=2.88s/P95=6.88s；长答 745 个正文 delta。
- [x] 更新 README、DECISIONS、DOMAIN、AGENTS 与执行日志。
