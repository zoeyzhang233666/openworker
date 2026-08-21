# ChemClaw Agent Harness Phase 1 实施计划（D-169）

**规格：** `docs/superpowers/specs/2026-08-20-chemclaw-agent-harness-phase-1-design.md`

**状态：实施完成，待独立验收**

1. 在开关 OFF 可回退前提下新增 Scenario/Capability Pydantic 模型、内置 Registry、Matcher、Resolver 与 ToolOutcome。
2. 将解析结果接入唯一 `TurnPlanner`，由 Tool Projection 消费 Capability Resolution，并在市场守卫后增加受控 allowlist guard。
3. 新增内容无关 TurnTrace recorder/store，接入普通 turn、retry、resume 和后台投递。
4. 增加 Scenario list、Plan Preview、Trace list/detail REST API，扩展 WS `scenario_id` 与 turn 摘要。
5. 曾在现有活动页增加执行诊断双视图、Preview 表单和 Trace 列表；该用户侧页面后按 D-170 用户决定删除，后端 API 保留。
6. 新增 Registry、Matcher、五条核心路由、fallback/outcome、Preview、Trace、REST/WS、GUI 和 OFF parity 测试。
7. 运行聚焦回归、D-166 94 项、Python/GUI 全量与性能基准；通过后将开关作为候选 ON，并更新 README、DECISIONS、DOMAIN、TESTING。

实施过程中保留 D-168 的全部未提交改动，尤其不恢复 `LeadsWorkbench` 和 `requestLeadFollowup`，对 `App.tsx`、`i18n.tsx` 与 ChemClaw 文档只做局部增量修改。

## 实施结果

- 已按规格完成 Scenario/Capability/ToolOutcome/TurnTrace 深模块、Planner/Projection/Guard 接线和 REST/WS；最初的 GUI 执行诊断按 D-170 用户反馈移除，未引入新依赖或第二套 Agent Loop。
- `scenario_resolution_enabled` 已作为独立候选 ON 开关；OFF parity 有测试覆盖。
- 聚焦 Python 170 passed；GUI 诊断/鉴权/恢复/i18n 34 passed；Vite build 通过；两项本地性能门槛通过。
- Python/GUI 全量仍暴露实施前已存在的 Windows ACL、组合 WebSocket 停滞、D-168 中文断言和 UpdateBanner 时序问题；未通过放宽断言、恢复用户改动或隐藏失败处理。
- D-168 原有修改及 `.vscode/`、`uv.lock`、D-168 计划文档均保留，未被 D-169 覆盖。
