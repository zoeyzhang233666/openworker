# ChemClaw Performance Router v5 — Cross-Window Execution Log

> **用途**：跨 Cursor Auto 窗口交接索引。每个 HARD STOP 追加一条，不覆盖旧条目。  
> **真相优先级**：当前仓库已批准治理/设计约束 + Git/工作区真实状态 **优先于** 本日志。三者冲突时 STOP，不得猜测。  
> **Plan**：[`2026-08-13-chemclaw-performance-router-v5.md`](./2026-08-13-chemclaw-performance-router-v5.md)  
> **执行语义**：Section 65 是唯一允许的自动实施顺序；HARD STOP A–G 不得在同一次 Agent run 中连续跨越。

## 恢复顺序（每个新 Cursor run）

```text
AGENTS.md / 当前已批准治理与设计
↓
Git SHA / status / log / current implementation
↓
v5 Plan
↓
本 execution log
```

## 条目模板（复制后填写）

```text
### Run / HARD STOP ID
- Start SHA:
- End/checkpoint SHA:
- Start git status --short:
- User-existing dirty changes:
- Governance/design files re-read:
- Allowed Section 65 step range:
- Expected files/symbols:
- Actual changed files:
- git diff --stat:
- Key diff summary:
- PASS:
- EXISTING FAIL:
- NEW FAIL:
- NOT RUN:
- ENV BLOCKED:
- request_routing_enabled built-in/test values:
- tool_projection_enabled built-in/test values:
- structured-tools streaming built-in/test values:
- emergency finalization built-in/test values:
- legacy provider-visible schema snapshot/parity:
- Critical Product Smoke:
- Rollback point:
- Remaining risks:
- Next run allowed range:
```

---

## Log entries（按时间追加）

### BOOTSTRAP — Plan 入库 + Execution Log 建立（2026-08-13）

- **Run / HARD STOP ID**: `BOOTSTRAP`（非 HARD STOP A–G；仅文档交接基建）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（本 run 未改业务代码；无 checkpoint commit）
- **Start git status --short**（摘要）:
  - 已修改：`AGENTS.md`、`coworker/agents/cowork.py`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/README.md`、`surfaces/gui/src/components/Sidebar.tsx`、`surfaces/gui/src/personaScope.ts`、`tests/test_persona_registry.py`
  - 未跟踪（节选）：`._chemclaw/`、`.local/`、`.pytest-basetemp/`、`.pytest-tmp/`、`.vscode/`、`surfaces/gui/src/personaScope.test.ts`、`uv.lock` 等
  - `git diff --stat HEAD`（用户已有改动）：7 files, +33/−20
- **User-existing dirty changes**: **是** — 主要为 D-131 默认智能体自称 ChemClaw 相关未提交改动；**后续 HARD STOP 不得覆盖/吸收这些改动**
- **Governance/design files re-read**: `docs/chemclaw/README.md`、`docs/superpowers/specs/2026-07-29-chemclaw-product-design.md`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/DOMAIN.md`、本 v5 Plan（源文件 + 入库副本）
- **Allowed Section 65 step range**: **无实施授权** — 本 run 仅允许 Plan 原样入库 + 建立本 log
- **Expected files/symbols**:
  - `docs/superpowers/plans/2026-08-13-chemclaw-performance-router-v5.md`
  - `docs/superpowers/plans/2026-08-13-chemclaw-performance-router-v5-execution-log.md`
  - （可选）`docs/chemclaw/README.md` 状态一句
- **Actual changed files**: 上述计划文件入库/新建；README 状态补充
- **git diff --stat**: 见本 run 结束后工作区（相对 BOOTSTRAP 前新增 plan 文件）
- **Key diff summary**:
  - 自 `d:\ChemClaw_Cursor_Auto_Safe_v5.md` **原样复制** Plan（SHA256 `A7B5FB1DD1DEF9665F90F8FAA44927F56BEF58ED817D0E3FFA76051AB21BDAC1`，128117 bytes，hash match）
  - 新建本 execution log
- **PASS**: Plan 入库 + hash 一致；execution log 建立
- **EXISTING FAIL**: not recorded（本 run 未跑测试）
- **NEW FAIL**: none
- **NOT RUN**: 全部 Section 65 / 业务测试
- **ENV BLOCKED**: n/a
- **request_routing_enabled built-in/test values**: 尚未引入（预期 built-in 全程 OFF 至独立 rollout）
- **tool_projection_enabled built-in/test values**: 尚未引入（预期 built-in 全程 OFF 至独立 rollout）
- **structured-tools streaming built-in/test values**: 尚未引入（预期 built-in 全程 OFF）
- **emergency finalization built-in/test values**: 尚未引入（预期 built-in 全程 OFF）
- **legacy provider-visible schema snapshot/parity**: 未做（HARD STOP D 前要求）
- **Critical Product Smoke**: 未做
- **Rollback point**: HEAD `1f6b01b`；用户 dirty 改动仍在工作区；本 BOOTSTRAP 仅新增文档，可用删除这两个 plan 文件回退文档侧
- **Remaining risks**:
  - 工作区非干净；HARD STOP A 起必须把用户已有 dirty 与本 Plan 改动严格隔离
  - 尚未开始 Section 65；Router/streaming 优化均未落地
- **Next run allowed range**: **仅 HARD STOP A = Section 65 steps 1–3**（baseline / compatibility characterization）；完成后必须 STOP，不得进入 step 4+

---

### HARD STOP A — Baseline / Compatibility Characterization（2026-08-13）

- **Run / HARD STOP ID**: `HARD STOP A`（Section 65 steps 1–3 only）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty，避免混入）
- **Start git status --short**（摘要）:
  - 用户已修改：`AGENTS.md`、`coworker/agents/cowork.py`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/README.md`、`surfaces/gui/src/components/Sidebar.tsx`、`surfaces/gui/src/personaScope.ts`、`tests/test_persona_registry.py`
  - 未跟踪（节选）：`._chemclaw/`、`.local/`、`.pytest-*`、`docs/superpowers/plans/2026-08-13-chemclaw-performance-router-v5*.md`、`surfaces/gui/src/personaScope.test.ts`、`uv.lock`
- **User-existing dirty changes**: **是** — D-131 自称 ChemClaw 等相关未提交改动；本 run **未覆盖/吸收**
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、`docs/superpowers/specs/2026-07-29-chemclaw-product-design.md`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/DOMAIN.md`、v5 Plan（Hard-Stop Protocol / 12 保险 / §65–69）、本 execution log
- **Allowed Section 65 step range**: **steps 1–3 only** → HARD STOP A
- **Expected files/symbols**:
  - characterization/regression tests only（`tests/test_providers.py`、`tests/test_provider_router.py`）
  - 文档：`docs/chemclaw/README.md`、本 execution log
  - **禁止**：`openai_provider.py` 生产逻辑、Router、budget、tool projection、Emergency Finalization、true streaming
- **Actual changed files**:
  - `tests/test_provider_router.py`（+Qwen/Hermes XML、unknown filter、parameters alias、structured-skips-salvage）
  - `tests/test_providers.py`（+stream salvage / no-tools gate / malformed `_raw`）
  - `docs/chemclaw/README.md`（HARD STOP A 状态）
  - `docs/superpowers/plans/2026-08-13-chemclaw-performance-router-v5-execution-log.md`（本条目）
- **git diff --stat**（本 run 测试侧）: `tests/test_provider_router.py` +79；`tests/test_providers.py` +44
- **Key diff summary / Step 2 行为刻画（以当前代码为准）**:
  - **Streaming**: `_collect_stream_chunks` **完整缓冲**后再 yield；`tools` 开启时 content delta 仍会进入 buffered `text_delta` 列表，最终 `AssistantTurn` 经 `_maybe_salvage_tool_calls` 后可清空 text 并填充 `tool_calls`
  - **Retry**: stream 侧最多 **3** 次 attempt（transport/`incomplete chunked read`/`Connection error`）；失败后 fallback `complete()`；**无** semantic-progress gate（有 partial 仍可整段重试）——属后续 HARD STOP B 范围
  - **Salvage gate**: 仅当 `tools` 非空且无 structured `tool_calls` 且 text 非空；成功则 `text=None` + `call_salvaged_*`
  - **Formats**: `<tool_call>{json}`、Qwen/Hermes `<function=…><parameter=…>`、embedded `{"name","arguments"|"parameters"}`、`toolname { stewed args}`/`[args]`；unknown tool name 过滤；structured 已存在则不 salvage
  - **SDK client**: `_stream_client` 生产路径每 stream 新建客户端；injected test client 复用；未改 `max_retries`/timeout 接管
- **PASS**:
  - Baseline targeted（改前）: `tests/test_providers.py` + `tests/test_provider_router.py` → **67 passed**
  - Post-characterization targeted: **75 passed**（+8 characterization）
  - Full（`--deselect tests/test_server.py::test_ws_session_persisted_while_parked_on_approval`）: **1504 passed**, 2 skipped, 1 deselected
- **EXISTING FAIL**（full deselected run，32；未为本 Plan 修复）:
  - bedrock×7（缺 boto3/botocore）
  - chain_lobster×2（`chem-price-daily` 期望集漂移）
  - `test_git_log_errors_outside_repo`、`test_workspace_trust_is_canonical_and_user_owned`（Win symlink 权限）
  - `test_new_tools_error_when_not_connected`（中文文案）
  - `test_durable_resume_approval_executes_tool`
  - `test_context_outside_git_repo`（worktree 仍是 git）
  - export_* / opportunity_radar bytecode×3
  - fake_slack×2
  - `test_platform_rewrite_pack_seeds_and_session_loads`
  - server artifact/token/ws/approval/trust/grants/google×8
  - slack_relay timeout×3
  - `test_ui_refresh_cross_cutting_e2e`
- **NEW FAIL**: **none**（仅新增通过的 characterization tests；未改生产代码）
- **NOT RUN**: Section 65 steps 4+；HARD STOP B–G；Router / true streaming / Emergency Finalization
- **ENV BLOCKED**:
  - **Hang**: `tests/test_server.py::test_ws_session_persisted_while_parked_on_approval` 在本机单独/套件中均无限挂起（CPU 停滞）；全量连续跑被其卡住。指纹用 `--deselect` 该用例完成。记为既有环境/套件阻塞，**非本 run 引入**
- **request_routing_enabled built-in/test values**: 尚未引入（OFF）
- **tool_projection_enabled built-in/test values**: 尚未引入（OFF）
- **structured-tools streaming built-in/test values**: 尚未引入（OFF；仍 compat-buffered）
- **emergency finalization built-in/test values**: 尚未引入（OFF）
- **legacy provider-visible schema snapshot/parity**: 未做（HARD STOP D 前要求）
- **Critical Product Smoke**: 未做
- **Rollback point**:
  - HEAD 仍为 `1f6b01b`
  - 本 run 改动获取：`git diff -- tests/test_providers.py tests/test_provider_router.py`；README/execution-log 手工还原状态句
  - 丢弃本 run：`git checkout -- tests/test_providers.py tests/test_provider_router.py`（**勿** checkout 用户 D-131 文件）
- **Remaining risks**:
  - 用户 dirty 与 Plan 改动并存；下一段须继续隔离
  - full suite 需 deselect 挂起用例才可跑完
  - streaming 仍整段缓冲；textual salvage 路径上 buffered `text_delta` 仍会携带原始 blob（最终 turn 已 salvage）——HARD STOP B true-streaming 时必须保留兼容保护
- **Next run allowed range**: **仅 HARD STOP B = Section 65 steps 4–8**（`tools=None` true streaming / retry-before-progress / stream timeout+max_retries=0 / non-stream SDK retry ownership / provider targeted tests）；完成后必须 STOP

---

### HARD STOP B — Provider Streaming / Retry Boundary（2026-08-13）

- **Run / HARD STOP ID**: `HARD STOP B`（Section 65 steps 4–8 only）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty，避免混入）
- **Start git status --short**（摘要）:
  - 用户已修改：`AGENTS.md`、`coworker/agents/cowork.py`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/README.md`、`surfaces/gui/src/components/Sidebar.tsx`、`surfaces/gui/src/personaScope.ts`、`tests/test_persona_registry.py`
  - HARD STOP A 未提交：`tests/test_providers.py`、`tests/test_provider_router.py`、v5 plan/log
  - 未跟踪（节选）：`._chemclaw/`、`.local/`、`.pytest-*`、`surfaces/gui/src/personaScope.test.ts`、`uv.lock`
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、产品设计、`DECISIONS.md`、`DOMAIN.md`、v5 Plan（§4–7 / Hard-Stop B / §65–66）、本 execution log；Git 交叉验证 HARD STOP A characterization 存在
- **Allowed Section 65 step range**: **steps 4–8 only** → HARD STOP B
- **Expected files/symbols**:
  - `coworker/providers/openai_provider.py`：`_sdk_client_kwargs`、`_make_sdk_client(streaming_retry_owned=)`、`_iter_true_stream_chunks`、`_collect_stream_chunks` progress/salvage-safe、`MAX_STREAM_ATTEMPTS=2`、progress-gated retry
  - `tests/test_providers.py` / `tests/test_provider_router.py`
  - 文档：`docs/chemclaw/README.md`、本 execution log
  - **禁止**：reasoning/budget、Router、Tool Projection、structured-tools true streaming、Emergency Finalization、risky built-in defaults
- **Actual changed files**（本 run）:
  - `coworker/providers/openai_provider.py`
  - `tests/test_providers.py`
  - `tests/test_provider_router.py`（`test_base_url_passed_to_sdk` 断言兼容 timeout / non-stream 无 max_retries）
  - `docs/chemclaw/README.md`
  - 本 execution log
- **git diff --stat**: 见本 run 结束后工作区（相对 HARD STOP A：新增 provider 生产改动 + 定向测试）
- **Key diff summary**:
  - **Step 4**: `tools is None` → `_iter_true_stream_chunks` 逐 chunk yield；`tools` 开启 → 继续 `_collect_stream_chunks` compat-buffered；salvage 成功时丢弃 text_delta，避免工具调用文本泄漏到 UI
  - **Step 5**: `provider_progress_seen`（text/reasoning/structured tool/textual candidate）后禁止 regenerate；无 progress 才允许重试
  - **Step 6**: stream client `timeout`（15/120/30/15）+ `max_retries=0`；`MAX_STREAM_ATTEMPTS=2`；无 progress 耗尽后才 `complete()` fallback
  - **Step 7**: `_ensure_client` / complete 路径 `streaming_retry_owned=False`，不强制 `max_retries=0`
  - **Step 8**: 定向测试覆盖真流式、salvage 不泄漏、各 progress 类型不重试、SDK ownership 分离
- **PASS**: targeted `tests/test_providers.py` + `tests/test_provider_router.py` → **83 passed**（`--basetemp=.pytest-basetemp/hard-stop-b2`）
- **EXISTING FAIL**: 本 run 未重跑全量；沿用 HARD STOP A 记录的既有失败/挂起用例指纹
- **NEW FAIL**: **none**（定向套件全绿）
- **NOT RUN**: Section 65 steps 9+；HARD STOP C–G；full pytest；Router / budget / Emergency Finalization
- **ENV BLOCKED**: 系统 Temp `pytest-of-EDY` PermissionError → 使用 worktree `--basetemp`（与 A 类似环境约束）
- **request_routing_enabled built-in/test values**: 尚未引入（OFF）
- **tool_projection_enabled built-in/test values**: 尚未引入（OFF）
- **structured-tools streaming built-in/test values**: 尚未引入（OFF；tools 路径仍 compat-buffered）
- **emergency finalization built-in/test values**: 尚未引入（OFF）
- **legacy provider-visible schema snapshot/parity**: 未做（HARD STOP D 前要求）
- **Critical Product Smoke**: 未做
- **Rollback point**:
  - HEAD 仍为 `1f6b01b`
  - 丢弃本 run provider 改动：`git checkout -- coworker/providers/openai_provider.py`（若需连同 A 的测试断言一并回退，再处理 `tests/test_providers.py` / `tests/test_provider_router.py` 中 B 段断言）
  - **勿** checkout 用户 D-131 文件
- **Remaining risks**:
  - 用户 dirty 与 Plan 改动并存；下一段须继续隔离
  - tools-enabled 仍整段缓冲（刻意）；structured-tools true streaming 未开
  - 未跑全量 pytest；progress 后 transport 失败改为直接 raise（不再 regenerate/fallback）
- **Next run allowed range**: **仅 HARD STOP C = Section 65 steps 9–15**（reasoning-mode plumbing + soft budget；Emergency Finalization 仍 OFF；legacy path inert）；完成后必须 STOP

---

### HARD STOP C — Reasoning / Soft-Budget Boundary（2026-08-13）

- **Run / HARD STOP ID**: `HARD STOP C`（Section 65 steps 9–15 only）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty + A/B 未提交改动，避免混入）
- **Start git status --short**（摘要）:
  - 用户已修改：`AGENTS.md`、`coworker/agents/cowork.py`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/README.md`、`surfaces/gui/src/components/Sidebar.tsx`、`surfaces/gui/src/personaScope.ts`、`tests/test_persona_registry.py`
  - HARD STOP A/B 未提交：`coworker/providers/openai_provider.py`、`tests/test_providers.py`、`tests/test_provider_router.py`、v5 plan/log
  - 未跟踪（节选）：`._chemclaw/`、`.local/`、`.pytest-*`、`surfaces/gui/src/personaScope.test.ts`、`uv.lock`
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、产品设计、`DECISIONS.md`、`DOMAIN.md`、v5 Plan（§8–12 / Phase 8 / Hard-Stop C / §65）、本 execution log；Git 交叉验证 HARD STOP A/B 产物存在
- **Allowed Section 65 step range**: **steps 9–15 only** → HARD STOP C
- **Expected files/symbols**:
  - `coworker/config.py`：`max_iterations=150`；`agent_target_iterations=32`；`deep_research_target_iterations=50`；`verified_max_iterations=6`；`request_routing_enabled=False`；`emergency_finalization_enabled=False`
  - `coworker/execution_profile.py`：`RequestRoute`、`ExecutionProfile`、`BudgetPhase`、thresholds/guidance、`make_execution_profile`、`apply_reasoning_mode_settings`
  - `coworker/engine.py`：可选 `execution_profile`；legacy-inert；outbound-only budget guidance；FAST_CHAT suppress REASONING_DELTA
  - `coworker/providers/base.py`：capability flags plumbing
  - tests：`test_execution_profile.py`、`test_engine_budget.py`、`test_config.py` 默认断言
  - **禁止**：Router semantics / `request_router.py` / tool projection / structured-tools true streaming / EF enablement / 改 `max_iterations` 默认值为 32/50
- **Actual changed files**（本 run）:
  - `coworker/config.py`
  - `coworker/execution_profile.py`（新）
  - `coworker/engine.py`
  - `coworker/providers/base.py`
  - `tests/test_execution_profile.py`（新）
  - `tests/test_engine_budget.py`（新）
  - `tests/test_config.py`
  - `docs/chemclaw/README.md`
  - 本 execution log
- **git diff --stat**: 见本 run 结束后工作区（相对 HARD STOP B：新增 profile/budget plumbing + 定向测试）
- **Key diff summary**:
  - **Step 9**: `reasoning_mode` on `ExecutionProfile`；engine 在有 profile 时可选 patch settings；`reasoning_mode=off` 抑制用户可见 `REASONING_DELTA`；无 profile 时不改 legacy reasoning
  - **Step 10–13**: `Config.max_iterations` 仍 **150**；公开 soft/hard 字段 32/50/6；`make_execution_profile` 将 soft target `min(target, max_iterations)`；VERIFIED `min(verified_max, max_iterations)`
  - **Step 14**: soft-target 驱动 Explore→Converge→Deliver（+ Extended）；guidance **仅 outbound** `<system-context>`，不写 `engine.messages`
  - **Step 15**: legacy-inert 测试证明：无 `ExecutionProfile` 时不注入 32/50/phase/新 reasoning；显式 profile 才激活；EF built-in **OFF**
- **PASS**:
  - `tests/test_execution_profile.py` + `tests/test_engine_budget.py` + `tests/test_config.py`（除 symlink）→ budget/config 定向绿
  - 合计定向+回归：`test_engine` / `test_engine_stop` / `test_compaction` / `test_compaction_engine` / `test_durable_resume` / budget → **84 passed**
- **EXISTING FAIL**:
  - `tests/test_config.py::test_workspace_trust_is_canonical_and_user_owned`（Win symlink 权限）— HARD STOP A 已记
  - `tests/test_durable_resume.py::test_durable_resume_approval_executes_tool`（Inbox pending）— HARD STOP A 已记
- **NEW FAIL**: **none**
- **NOT RUN**: Section 65 steps 16+；HARD STOP D–G；full pytest；Router / tool projection / structured-tools true streaming / EF enablement
- **ENV BLOCKED**: 无新增（沿用 basetemp worktree 约定）
- **request_routing_enabled built-in/test values**: **built-in OFF**；本段仅 Config 字段 + inert 证明；无 Router 接线
- **tool_projection_enabled built-in/test values**: 尚未引入（OFF）
- **structured-tools streaming built-in/test values**: 尚未引入（OFF）
- **emergency finalization built-in/test values**: **built-in OFF**；`ExecutionProfile.emergency_finalization_enabled` 字段存在但默认 False；无 finalization 新语义
- **legacy provider-visible schema snapshot/parity**: 未做（HARD STOP D 前要求）
- **Critical Product Smoke**: 未做
- **Rollback point**:
  - HEAD 仍为 `1f6b01b`
  - 丢弃本 run：删除 `coworker/execution_profile.py`、`tests/test_execution_profile.py`、`tests/test_engine_budget.py`；`git checkout -- coworker/config.py coworker/engine.py coworker/providers/base.py tests/test_config.py`（**勿** checkout 用户 D-131 或 A/B provider 文件）
- **Remaining risks**:
  - 用户 dirty 与 A/B/C Plan 改动并存；下一段须继续隔离
  - soft-budget 仅在显式 profile 下生效；Router 尚未接线，生产路径仍 100% legacy
  - EF / tool projection / structured streaming 仍未实现
- **Next run allowed range**: **仅 HARD STOP D = Section 65 steps 16–33**（Router skeleton + guards + routes + classifier + ExecutionProfile 接线；此时仍不做 aggressive tool filtering）；完成后必须 STOP

---

### HARD STOP D — Router Semantics Before Tool Projection（2026-08-13）

- **Run / HARD STOP ID**: `HARD STOP D`（Section 65 steps 16–33 only）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty + A/B/C 未提交改动，避免混入）
- **Start git status --short**（摘要）:
  - 用户已修改：`AGENTS.md`、`coworker/agents/cowork.py`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/README.md`、`surfaces/gui/src/components/Sidebar.tsx`、`surfaces/gui/src/personaScope.ts`、`tests/test_persona_registry.py`
  - HARD STOP A/B/C 未提交：provider/engine/config/execution_profile + 定向测试 + v5 plan/log
  - 未跟踪（节选）：`._chemclaw/`、`.local/`、`.pytest-*`、`surfaces/gui/src/personaScope.test.ts`、`uv.lock`
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**（仅更新 README/AGENTS 门禁状态句与 execution log）
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、产品设计、`DECISIONS.md`、`DOMAIN.md`、v5 Plan（§14–26 / Hard-Stop D / §65 steps 16–33 / §40 test matrix）、本 execution log；Git 交叉验证 HARD STOP A/B/C 产物存在
- **Allowed Section 65 step range**: **steps 16–33 only** → HARD STOP D
- **Expected files/symbols**:
  - `coworker/request_router.py`：guards / pure-answer / routes / classifier / legacy_fallback / `decision_to_execution_profile` / `resolve_execution_profile`
  - `coworker/tool_policy.py`：`TurnToolPolicy` + `network_scope`/`usage_class` helper + pure `filter_tool_names`（**未接入 engine projection**）
  - `coworker/agent.py`：可选 `execution_profile=` 传入 TurnEngine（无 schema 裁剪）
  - tests：`test_request_router.py`、`test_tool_policy.py`、`test_legacy_tool_schema_snapshot.py`
  - snapshot：`docs/superpowers/plans/fixtures/hard-stop-d-legacy-tool-schema-snapshot.json`
  - **禁止**：Step 34+ tool projection、structured-tools true streaming、EF enablement、`request_routing_enabled` built-in ON
- **Actual changed files**（本 run）:
  - `coworker/request_router.py`（新）
  - `coworker/tool_policy.py`（新）
  - `coworker/agent.py`（可选 `execution_profile` 形参）
  - `tests/test_request_router.py`（新）
  - `tests/test_tool_policy.py`（新）
  - `tests/test_legacy_tool_schema_snapshot.py`（新）
  - `docs/superpowers/plans/fixtures/hard-stop-d-legacy-tool-schema-snapshot.json`（新）
  - `docs/chemclaw/README.md`、`AGENTS.md`（门禁状态）
  - 本 execution log
- **git diff --stat**: 见工作区（相对 HARD STOP C：新增 router/policy + 测试 + snapshot；agent.py +5 行）
- **Key diff summary**:
  - **Step 16**: `RequestRouter` / `route_request`；`Config.request_routing_enabled` built-in **False** → 返回 `None`（legacy-inert）
  - **Steps 17–20**: Pending-State / Persona·Forced-Skill / Product-Action / Pure-Answer **正向白名单**（不得靠「没命中关键词」推 tools=None）
  - **Steps 21–22**: `NO_TOOLS` / `NO_SEARCH` / `NO_EXTERNAL_NETWORK` 正交；集中 `classify_tool`；禁网时 REMOTE+UNKNOWN 剔除、LOCAL file/memory 保留（helper 级，未投影）
  - **Steps 23–28**: FAST_CHAT / KNOWLEDGE / VERIFIED / AGENT / DEEP_RESEARCH 本地门 + risk gate
  - **Step 29**: continuation inheritance（谢谢等纯问候不 sticky）
  - **Steps 30–32**: tiny classifier（≤1 call / 5s timeout）；failure → `legacy_fallback` **AGENT**，**永不默认 KNOWLEDGE**
  - **Step 33**: `decision_to_execution_profile` / `resolve_execution_profile` 接线 hard/soft；AGENT/DEEP `allowed_tool_names=None`（全量 legacy）
  - **NOT Step 34**: 无 per-turn tool projection；无 provider-visible schema 裁剪
- **PASS**:
  - `tests/test_tool_policy.py` + `tests/test_request_router.py` + `tests/test_legacy_tool_schema_snapshot.py` + budget/config（deselect symlink）→ **84 passed**
  - engine/stop/compaction/resume + `test_build_engine_chat` → **71 passed**
- **EXISTING FAIL**:
  - `tests/test_durable_resume.py::test_durable_resume_approval_executes_tool`（Inbox pending）— HARD STOP A/C 已记
  - `tests/test_config.py::test_workspace_trust_is_canonical_and_user_owned`（Win symlink）— 本段 deselect
- **NEW FAIL**: **none**
- **NOT RUN**: Section 65 steps 34+；HARD STOP E–G；full pytest；structured-tools true streaming；EF enablement；aggressive tool filtering
- **ENV BLOCKED**: 无新增（沿用 basetemp worktree 约定）
- **request_routing_enabled built-in/test values**: **built-in OFF**；测试显式 ON 覆盖矩阵；OFF 时 `route_request`/`resolve_execution_profile` → `None`
- **tool_projection_enabled built-in/test values**: **尚未引入**（本段刻意不做 Step 34）
- **structured-tools streaming built-in/test values**: 尚未引入（OFF；tools 路径仍 compat-buffered）
- **emergency finalization built-in/test values**: **built-in OFF**（未改）
- **legacy provider-visible schema snapshot/parity**: **已记录** — `docs/superpowers/plans/fixtures/hard-stop-d-legacy-tool-schema-snapshot.json`（cowork / chat / chain-lobster；含 tool_names + schema fingerprints）。HARD STOP E 必须对比 projection 后结果。
- **Critical Product Smoke**: 未做（属 HARD STOP E Gate）；本段自动化矩阵覆盖 greeting/knowledge/CAS/safety/memory/schedule/file/persona/skill/pending/no-network+local/classifier timeout/ambiguous short command
- **Rollback point**:
  - HEAD 仍为 `1f6b01b`
  - 丢弃本 run：删除 `coworker/request_router.py`、`coworker/tool_policy.py`、`tests/test_request_router.py`、`tests/test_tool_policy.py`、`tests/test_legacy_tool_schema_snapshot.py`、`docs/superpowers/plans/fixtures/hard-stop-d-legacy-tool-schema-snapshot.json`；`git checkout -- coworker/agent.py`（仅本段 +5 行）；手工还原 README/AGENTS/execution-log 本条目
  - **勿** checkout 用户 D-131 或 A/B/C 文件
- **Remaining risks**:
  - Router 未自动挂入每会话生产路径（kill switch OFF + resolve 需显式调用）；开启 ON 后仍须 Step 34 projection 与 Capability Gate
  - 启发式门对未来未知产品动词依赖 legacy_fallback；须保持「不确定不裁能力」
  - 用户 dirty 与 A–D Plan 改动并存
- **Next run allowed range**: **仅 HARD STOP E = Section 65 steps 34–39**（`tool_projection_enabled` kill switch 默认 OFF + per-turn projection + Capability Preservation Gate + schema parity 对比）；完成后必须 STOP。**不得在同一次 run 开启 structured-tools true streaming 或 EF。**

---

### HARD STOP E — Capability Preservation Gate（2026-08-13）

- **Run / HARD STOP ID**: `HARD STOP E`（Section 65 steps 34–39 only）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty + A–D 未提交改动，避免混入）
- **Start git status --short**（摘要）:
  - 用户已修改：`AGENTS.md`、`coworker/agents/cowork.py`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/README.md`、`surfaces/gui/src/components/Sidebar.tsx`、`surfaces/gui/src/personaScope.ts`、`tests/test_persona_registry.py`
  - HARD STOP A–D 未提交：provider/engine/config/execution_profile/request_router/tool_policy + 定向测试 + v5 plan/log + legacy snapshot
  - 未跟踪（节选）：`._chemclaw/`、`.local/`、`.pytest-*`、`surfaces/gui/src/personaScope.test.ts`、`uv.lock`
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**（仅更新 README/AGENTS 门禁状态句与 execution log）
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、产品设计、`DECISIONS.md`、`DOMAIN.md`、v5 Plan（§27–28 / §53A / Hard-Stop E / §65 steps 34–39）、本 execution log；Git 交叉验证 HARD STOP D 产物与 `hard-stop-d-legacy-tool-schema-snapshot.json` 存在
- **Allowed Section 65 step range**: **steps 34–39 only** → HARD STOP E
- **Expected files/symbols**:
  - `coworker/config.py`：`tool_projection_enabled=False`（built-in OFF；与 routing 独立）
  - `coworker/tool_projection.py`：`project_provider_visible_schemas` / `select_verified_tool_names`
  - `coworker/engine.py` / `coworker/agent.py`：per-turn schema projection（不 unregister/rebuild registry）
  - `coworker/request_router.py`：VERIFIED 定向 `allowed_tool_names`
  - `coworker/tool_policy.py`：ChemClaw 本地工具分类补全（避免 NO_EXTERNAL_NETWORK 静默丢本地能力）
  - tests：`test_tool_projection.py`、`test_tool_projection_parity.py`、`test_capability_preservation_gate.py`
  - **禁止**：structured-tools true streaming、EF enablement、改任何 risky built-in default 为 ON
- **Actual changed files**（本 run）:
  - `coworker/tool_projection.py`（新）
  - `coworker/config.py`、`coworker/engine.py`、`coworker/agent.py`、`coworker/request_router.py`、`coworker/tool_policy.py`
  - `tests/test_tool_projection.py`、`tests/test_tool_projection_parity.py`、`tests/test_capability_preservation_gate.py`（新）
  - `tests/test_config.py`、`tests/test_request_router.py`
  - `docs/chemclaw/README.md`、`AGENTS.md`、本 execution log
- **git diff --stat**: 见工作区（相对 HARD STOP D：新增 projection 模块 + engine 接线 + parity/gate 测试）
- **Key diff summary**:
  - **Step 34**: `tool_projection_enabled` kill switch built-in **OFF**；OFF 时即使挂 FAST_CHAT profile 也恢复 legacy full schema；ON + pure FAST/KNOWLEDGE → `tools=None`
  - **Step 35**: VERIFIED `select_verified_tool_names`（CAS→`lookup_chemical_identity` 等）；不确定/无交集 → `None`（全量保留）
  - **Step 36**: AGENT/DEEP `allowed_tool_names=None` → 保守全量 legacy
  - **Step 37**: ToolPolicy 终滤（`filter_tool_names` / classify_tool）；补全 `list_files`/`run_shell`/`replace_in_file` 等本地分类
  - **Step 38**: UNKNOWN custom：普通 AGENT 保留；`NO_EXTERNAL_NETWORK` 剔除；parity 对比 HARD STOP D snapshot
  - **Step 39**: Capability Preservation Gate 自动化套件 + kill-switch 矩阵；Critical Product Smoke **未在真实 GUI 全跑**
- **PASS**:
  - projection/parity/gate/policy/router/config 定向：`tests/test_tool_projection*.py` + `test_capability_preservation_gate.py` + `test_tool_policy.py` + `test_request_router.py` + `test_config`（deselect symlink）→ **91 passed**
  - Capability Gate suites（memory/skills/ask/plan/resume/automation/wake/connectors/mcp/persona/permissions/engine/providers）：**293 passed**, 1 existing fail
  - compaction + legacy snapshot + execution_profile：**51 passed**
- **EXISTING FAIL**:
  - `tests/test_durable_resume.py::test_durable_resume_approval_executes_tool`（Inbox pending）— HARD STOP A/C/D 已记；**非本段引入**
  - `tests/test_config.py::test_workspace_trust_is_canonical_and_user_owned`（Win symlink）— deselect
- **NEW FAIL**: **none**
- **NOT RUN**: Section 65 steps 40+；HARD STOP F–G；full pytest；structured-tools true streaming；EF；真实 GUI Critical Product Smoke
- **ENV BLOCKED**:
  - Critical Product Smoke（真实 ChemClaw surface）：普通聊天 / Memory 写入 / forced Skill / ask_user·plan·resume / Scheduling·Self-wake / persona / 不要联网+本地文件 / connector·MCP — **ENV BLOCKED — manual validation pending**（本 Auto run 无交互 GUI 会话）
- **request_routing_enabled built-in/test values**: **built-in OFF**；测试显式 ON/OFF 矩阵（与 projection 交叉）
- **tool_projection_enabled built-in/test values**: **built-in OFF**；测试显式 ON/OFF；OFF→parity 对齐 HARD STOP D snapshot；ON→FAST `tools=None` / VERIFIED 子集 / AGENT 全量
- **structured-tools streaming built-in/test values**: **尚未引入**（OFF；tools 路径仍 compat-buffered）
- **emergency finalization built-in/test values**: **built-in OFF**（未改）
- **legacy provider-visible schema snapshot/parity**: **已对比** — `tool_projection_enabled=false` 与 HARD STOP D snapshot 的 cowork/chat tool_names + schema fingerprints 一致；ON 路径不永久删 registry
- **Critical Product Smoke**: **automated gate passed; manual validation pending**（不得宣称完全验收）
- **Rollback point**:
  - HEAD 仍为 `1f6b01b`
  - 丢弃本 run：删除 `coworker/tool_projection.py`、`tests/test_tool_projection.py`、`tests/test_tool_projection_parity.py`、`tests/test_capability_preservation_gate.py`；`git checkout -- coworker/config.py coworker/engine.py coworker/agent.py tests/test_config.py tests/test_request_router.py`（仅本段相关 hunk）；手工还原 `coworker/request_router.py` / `coworker/tool_policy.py` 本段改动与 README/AGENTS/execution-log 本条目
  - **勿** checkout 用户 D-131 或 A–D 无关文件
- **Remaining risks**:
  - projection 仅在测试/显式 ON 时生效；生产 built-in 仍 OFF，真实会话仍 100% legacy schema
  - VERIFIED 启发式子集可能过窄/过宽；不确定时回退全量
  - Critical Product Smoke 需人工 GUI 补验后方可宣称完全验收
  - 用户 dirty 与 A–E Plan 改动并存
- **Next run allowed range**: **仅 HARD STOP F = Section 65 steps 40–42**（structured-tools true streaming known-safe + kill switch；built-in 仍 OFF）。**不得在同一次 run 实现/启用 Emergency Finalization。**

---

**HARD STOP E reached — downstream phases NOT started.**

（在下方追加下一个 HARD STOP 条目）

### HARD STOP F — Structured-Tools Streaming Boundary（2026-08-13）

- **Run / HARD STOP ID**: `HARD STOP F`（Section 65 steps 40–42 only）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty + A–E 未提交改动，避免混入）
- **Start git status --short**（摘要）:
  - 用户已修改：`AGENTS.md`、`coworker/agents/cowork.py`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/README.md`、`surfaces/gui/src/components/Sidebar.tsx`、`surfaces/gui/src/personaScope.ts`、`tests/test_persona_registry.py`
  - HARD STOP A–E 未提交：provider/engine/config/execution_profile/request_router/tool_policy/tool_projection + 定向测试 + v5 plan/log + legacy snapshot
  - 未跟踪（节选）：`._chemclaw/`、`.local/`、`.pytest-*`、`surfaces/gui/src/personaScope.test.ts`、`uv.lock`
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**（仅更新 README/AGENTS 门禁状态句与 execution log）
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、产品设计、`DECISIONS.md`、`DOMAIN.md`、v5 Plan（§4 / §41 / Hard-Stop F / §65 steps 40–42）、本 execution log HARD STOP E 条目
- **HARD STOP E gate precondition**: **NEW FAIL = none**（E 日志）；Critical Product Smoke 仍为 `automated gate passed; manual validation pending` — 不阻塞本段（用户已显式授权 F）
- **Allowed Section 65 step range**: **steps 40–42 only** → HARD STOP F
- **Expected files/symbols**:
  - `coworker/config.py`：`structured_tools_true_streaming_enabled=False`（built-in OFF）
  - `coworker/providers/openai_provider.py`：`is_known_safe_structured_tools_streaming` / `_should_true_stream_with_tools`；`stream()` 路径选择；内部 kwarg pop 不泄漏到 API
  - `coworker/engine.py` / `coworker/agent.py`：把 Config kill switch 传入 `provider.stream(...)`
  - tests：providers ON/OFF + known-safe matrix + salvage 回归；config/capability gate 断言 built-in OFF
  - **禁止**：Emergency Finalization 实现/启用；改任何 risky built-in default 为 ON
- **Actual changed files**（本 run）:
  - `coworker/config.py`、`coworker/providers/openai_provider.py`、`coworker/engine.py`、`coworker/agent.py`
  - `tests/test_providers.py`、`tests/test_config.py`、`tests/test_capability_preservation_gate.py`
  - `docs/chemclaw/README.md`、`AGENTS.md`、本 execution log
- **git diff --stat**: 见工作区（相对 HARD STOP E：openai_provider known-safe 分支 + config/engine/agent 接线 + F 定向测试）
- **Key diff summary**:
  - **Step 40**: tools-enabled + kill switch ON + known-safe → `_iter_true_stream_chunks`（即时 text/reasoning + split structured tool args 累积）；`tools=None` 仍始终真流式（HARD STOP B 不变）
  - **Step 41**: `structured_tools_true_streaming_enabled` kill switch；测试显式 ON/OFF；未知/custom host 即使 ON 也走 compat-buffered
  - **Step 42**: OFF → 无缝恢复 `_collect_stream_chunks` + `_maybe_salvage_tool_calls`；Qwen/Hermes/Ollama/bare JSON/toolname/unknown filter/malformed `_raw`/retry-after-progress/usage-only heartbeat 回归
- **Known-safe matrix**（本阶段）：
  - **允许**: model 名（去 provider 前缀后）以 `gpt-4`/`gpt-5`/`o1`/`o3`/`o4` 开头，且 `base_url` 为 `None` / `api.openai.com` / `*.openai.azure.com`
  - **不允许（compat-buffered + salvage-safe）**: 任意其他 OpenAI-compatible host（ApiHub / DeepSeek / Qwen DashScope / Ollama / custom.example / tokenfoundryx 等），即使 model 字符串像 `gpt-*`
- **Unknown/custom behavior**: kill switch 任意 → 仍 `_collect_stream_chunks`；textual salvage 与进度门控 retry 保持 HARD STOP B 语义
- **PASS**:
  - F 定向 8 tests：**8 passed**
  - `tests/test_providers.py` + `test_provider_router.py` + `test_config`（symlink EXISTING）+ `test_capability_preservation_gate` + `test_engine_stop` → **112 passed**, 1 existing fail
  - salvage/stream 关键字子集：**43 passed**
- **EXISTING FAIL**:
  - `tests/test_config.py::test_workspace_trust_is_canonical_and_user_owned`（Win symlink 权限）— HARD STOP A/E 已记；**非本段引入**
- **NEW FAIL**: **none**
- **NOT RUN**: Section 65 steps 43+；HARD STOP G；full pytest；EF；真实 GUI Critical Product Smoke；risky default rollout
- **ENV BLOCKED**: 系统 Temp `pytest-of-EDY` PermissionError → 继续用 worktree `--basetemp`（与 A–E 相同）
- **request_routing_enabled built-in/test values**: **built-in OFF**（未改）
- **tool_projection_enabled built-in/test values**: **built-in OFF**（未改）
- **structured-tools streaming built-in/test values**: **built-in OFF**；测试显式 ON（known-safe 真流式）/ OFF（compat-buffered + salvage）
- **emergency finalization built-in/test values**: **built-in OFF**（未实现/未启用）
- **legacy provider-visible schema snapshot/parity**: 本段未改 projection；仍以 HARD STOP E 为准
- **Critical Product Smoke**: 仍为 **automated gate passed; manual validation pending**（E 遗留；本段未宣称完全验收）
- **Rollback point**:
  - HEAD 仍为 `1f6b01b`
  - 丢弃本 run：还原 `coworker/config.py` / `openai_provider.py` / `engine.py` / `agent.py` 中 F 相关 hunk；还原 `tests/test_providers.py` F 测试块、`tests/test_config.py` 与 `tests/test_capability_preservation_gate.py` 的 structured-streaming 断言；还原 README/AGENTS/execution-log 本条目
  - **勿** checkout 用户 D-131 或 A–E 无关文件
- **Remaining risks**:
  - known-safe 矩阵刻意保守；Azure 非 gpt-/o- 部署名不会开启真流式
  - known-safe 真流式路径不做 textual salvage（假定 structured tool_calls）；误判进矩阵会有 UI 泄漏风险 — 故默认 OFF + 窄 allowlist
  - 生产 built-in 仍 OFF，真实会话 tools 路径仍 100% compat-buffered，直至独立 rollout
- **Next run allowed range**: **仅 HARD STOP G = Section 65 steps 43–45**（Emergency Finalization + Stop/pending guards；built-in 仍 OFF）。**不得在同一次 run 做 instrumentation / final regression / default enablement。**

---

**HARD STOP F reached — downstream phases NOT started.**

（在下方追加下一个 HARD STOP 条目）

### HARD STOP G — Emergency Finalization Boundary（2026-08-13）

- **Run / HARD STOP ID**: `HARD STOP G`（Section 65 steps 43–45 only）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty + A–F 未提交改动，避免混入）
- **Start git status --short**（摘要）:
  - 用户已修改：`AGENTS.md`、`coworker/agents/cowork.py`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/README.md`、`surfaces/gui/src/components/Sidebar.tsx`、`surfaces/gui/src/personaScope.ts`、`tests/test_persona_registry.py`
  - HARD STOP A–F 未提交：provider/engine/config/execution_profile/request_router/tool_policy/tool_projection + 定向测试 + v5 plan/log + legacy snapshot
  - 未跟踪（节选）：`._chemclaw/`、`.local/`、`.pytest-*`、`surfaces/gui/src/personaScope.test.ts`、`uv.lock`
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**（仅更新 README/AGENTS 门禁状态句与 execution log）
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、产品设计、`DECISIONS.md`、`DOMAIN.md`、v5 Plan（§13 / Hard-Stop G / §65 steps 43–45）、本 execution log HARD STOP F 条目
- **HARD STOP F gate precondition**: **NEW FAIL = none**（F 日志）；用户已显式授权 G
- **Allowed Section 65 step range**: **steps 43–45 only** → HARD STOP G
- **Expected files/symbols**:
  - `coworker/config.py`：`emergency_finalization_enabled=False`（built-in OFF；字段已在 C/F 引入）
  - `coworker/engine.py`：`_should_emergency_finalize` / `_emergency_finalize`；hard ceiling 一次 tools-disabled model-only call；`status=max_iterations_exceeded` + `best_effort_finalized=true`
  - `coworker/agent.py`：Config kill switch 接线
  - `coworker/execution_profile.py`：profile 字段门控（FAST/KNOWLEDGE 强制 False）
  - tests：`test_emergency_finalization.py` + engine/stop/plan/resume 回归
  - **禁止**：Step 46+ instrumentation/cleanup/final regression；改任何 risky built-in default 为 ON
- **Actual changed files**（本 run）:
  - `coworker/engine.py`、`coworker/agent.py`
  - `tests/test_emergency_finalization.py`（新）
  - `docs/chemclaw/README.md`、`AGENTS.md`、本 execution log
- **git diff --stat**: 见工作区（相对 HARD STOP F：engine EF + agent 接线 + G 定向测试）
- **Key diff summary**:
  - **Step 43**: hard ceiling + kill switch ON + 普通可终结 → 一次 `_emergency_finalize`（`tools=None`；outbound-only EF prompt；不回 agent loop；忽略模型仍返回的 tool_calls）
  - **Step 44**: guards — `_cancel` / unanswered trailing tool calls（ask_user·approval·plan·directory / durable resume）→ 不触发；kill switch OFF → legacy `max_iterations_exceeded`（无 `best_effort_finalized`）；profile 门控（FAST 强制 OFF；AGENT profile ON 可覆盖 engine flag）
  - **Step 45**: engine / stop / plan / resume / ask_user / budget / config / capability gate 定向回归
- **PASS**:
  - EF 定向 8 tests：**8 passed**
  - engine + stop + budget + plan + durable + ask_user + config（symlink deselect）+ execution_profile + capability gate + EF：**86 passed**, 1 existing fail, 1 deselected
- **EXISTING FAIL**:
  - `tests/test_durable_resume.py::test_durable_resume_approval_executes_tool`（Inbox pending）— HARD STOP A/C/D/E 已记；**非本段引入**
  - `tests/test_config.py::test_workspace_trust_is_canonical_and_user_owned`（Win symlink）— deselect
- **NEW FAIL**: **none**
- **NOT RUN**: Section 65 steps 46+；instrumentation；full pytest；risky default rollout；真实 GUI Critical Product Smoke
- **ENV BLOCKED**: 系统 Temp `pytest-of-EDY` PermissionError → 继续用 worktree `--basetemp`（与 A–F 相同）
- **request_routing_enabled built-in/test values**: **built-in OFF**（未改）
- **tool_projection_enabled built-in/test values**: **built-in OFF**（未改）
- **structured-tools streaming built-in/test values**: **built-in OFF**（未改）
- **emergency finalization built-in/test values**: **built-in OFF**；测试显式 ON（一次 model-only finalization）/ OFF（legacy hard-limit）
- **legacy provider-visible schema snapshot/parity**: 本段未改 projection；仍以 HARD STOP E 为准
- **Critical Product Smoke**: 仍为 **automated gate passed; manual validation pending**（E 遗留；本段未宣称完全验收）
- **Rollback point**:
  - HEAD 仍为 `1f6b01b`
  - 丢弃本 run：还原 `coworker/engine.py` / `coworker/agent.py` 中 G 相关 hunk；删除 `tests/test_emergency_finalization.py`；还原 README/AGENTS/execution-log 本条目
  - **勿** checkout 用户 D-131 或 A–F 无关文件
- **Remaining risks**:
  - 生产 built-in 仍 OFF，真实会话撞 hard ceiling 仍为旧 hard-limit（无 best-effort 回答），直至独立 rollout
  - EF prompt 依赖 outbound 末条 user message 的 system-context 注入；无 user 消息时提示可能落空（正常 run 路径总有 user turn）
  - 用户 dirty 与 A–G Plan 改动并存
- **Next run allowed range**: **仅 Section 65 steps 46–55**（batching/duplicate-tool/instrumentation + targeted/full regression + manual smoke；须新独立授权）。**不得**在同一次 run 修改 risky built-in defaults。

---

**HARD STOP G reached — downstream phases NOT started.**

（在下方追加下一个 HARD STOP 条目）

### FINAL REGRESSION 46–55 — Batching / Duplicate / Instrumentation + Full Regression（2026-08-13）

- **Run / HARD STOP ID**: `FINAL REGRESSION 46–55`（Section 65 steps 46–55 only；非 default enablement）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty + A–G 未提交改动，避免混入）
- **Start git status --short**（摘要）:
  - 用户已修改：`AGENTS.md`、`coworker/agents/cowork.py`、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/README.md`、`surfaces/gui/src/components/Sidebar.tsx`、`surfaces/gui/src/personaScope.ts`、`tests/test_persona_registry.py`
  - HARD STOP A–G 未提交：provider/engine/config/execution_profile/request_router/tool_policy/tool_projection + 定向测试 + v5 plan/log + legacy snapshot + EF
  - 未跟踪（节选）：`._chemclaw/`、`.local/`、`.pytest-*`、`surfaces/gui/src/personaScope.test.ts`、`uv.lock`
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**（仅更新 README/AGENTS 门禁状态句与 execution log）
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、产品设计、`DECISIONS.md`、`DOMAIN.md`、v5 Plan（Phase 10–12 / §65 steps 46–55 / §56–64G smoke / Definition of Done）、本 execution log HARD STOP G 条目
- **HARD STOP G gate precondition**: **NEW FAIL = none**（G 日志）；用户已显式授权 46–55
- **Allowed Section 65 step range**: **steps 46–55 only** → final regression；**禁止** risky built-in default ON / rollout steps 56–59
- **Expected files/symbols**:
  - Step 46：`coworker/agent.py` `_TOOL_BATCHING_GUIDANCE` 注入 system instructions
  - Step 47：`coworker/engine.py` `_recent_tool_signatures` / `_DUPLICATE_TOOL_WARNING`（outbound-only；不硬禁）
  - Step 48：`coworker/turn_instrumentation.py` + engine/provider 安全日志（无 secrets/全文 prompt）
  - Steps 49–55：targeted / compaction / capability / full pytest / `git diff --check` / manual diff / smoke A–P
- **Actual changed files**（本 run）:
  - `coworker/agent.py`、`coworker/engine.py`、`coworker/providers/openai_provider.py`
  - `coworker/turn_instrumentation.py`（新）
  - `tests/test_tool_batching_and_duplicate.py`、`tests/test_turn_instrumentation.py`（新）
  - `docs/chemclaw/README.md`、`AGENTS.md`、本 execution log
- **git diff --check**: **PASS**（本 run 相关文件；无 whitespace error）
- **Key diff summary**:
  - **46**: 通用 Tool efficiency batching guidance 追加到所有 persona system prompt（小范围）
  - **47**: 完全相同 name+args 连续 ≥3 次 → 下一轮 outbound `<system-context>` 警告；不同 args 不触发；不硬禁止
  - **48**: turn / model_call / provider_stream 结构化日志；禁记 api_key/prompt/messages/tool_result 等；Router OFF 时 route 字段为空
- **PASS**:
  - Steps 46–48 定向：`test_tool_batching_and_duplicate` + `test_turn_instrumentation` → **10 passed**
  - Step 49 targeted v5 核心：providers/router/policy/projection/profile/budget/EF/legacy snapshot → **200 passed**
  - Step 49b engine/stop/config/capability_gate（deselect symlink）→ **40 passed**, 1 deselected
  - Step 50 compaction：`test_compaction` + `test_compaction_engine` + `test_compaction_smoke` → **43 passed**
  - Step 51 capability suites（memory/skills/ask/plan/resume/automation/wake/connectors/mcp/persona/permissions）→ **177 passed**, 1 existing fail
  - Step 52 full pytest（`--deselect tests/test_server.py::test_ws_session_persisted_while_parked_on_approval`）→ **1635 passed**, 2 skipped, 1 deselected, **32 failed（全部 EXISTING）**
  - Step 53 `git diff --check` → **PASS**
  - Step 54 manual diff review → **PASS**（见下）
  - Automated router matrix（routing/projection **显式 ON**；built-in 仍 OFF）对 smoke 提示词 A/B/C/D/E/F/G/J/K/L/M/O/P → 分类符合预期；OFF → `None` inert
- **EXISTING FAIL**（full；与 HARD STOP A 指纹一致的 32；非本 run 引入）:
  - bedrock×7（缺 boto3/botocore）
  - chain_lobster×2（`chem-price-daily` 期望集漂移）
  - `test_git_log_errors_outside_repo`、`test_workspace_trust_is_canonical_and_user_owned`（Win symlink 权限）
  - `test_new_tools_error_when_not_connected`（中文文案）
  - `test_durable_resume_approval_executes_tool`
  - `test_context_outside_git_repo`（worktree 仍是 git）
  - export_* / opportunity_radar bytecode×3
  - fake_slack×2
  - `test_platform_rewrite_pack_seeds_and_session_loads`
  - server artifact/token/ws/approval/trust/grants/google×8
  - slack_relay timeout×3
  - `test_ui_refresh_cross_cutting_e2e`
- **NEW FAIL**: **none**
- **NOT RUN**: Section 65 steps 56–59 default enablement rollout；真实 GUI 交互式 live-model smoke（见 ENV BLOCKED）
- **ENV BLOCKED**:
  - Manual Smoke A–P（真实 ChemClaw GUI + live model + 路由日志观测）：**ENV BLOCKED — manual validation pending**（本 Auto run 无交互 GUI 会话；不得宣称产品面完全验收）
  - full suite hang：`test_ws_session_persisted_while_parked_on_approval` 继续 `--deselect`（HARD STOP A 已记）
  - 系统 Temp PermissionError → worktree `--basetemp`
- **request_routing_enabled built-in/test values**: **built-in OFF**；测试/矩阵显式 ON；未改 default
- **tool_projection_enabled built-in/test values**: **built-in OFF**；测试显式 ON/OFF；未改 default
- **structured-tools streaming built-in/test values**: **built-in OFF**（未改）
- **emergency finalization built-in/test values**: **built-in OFF**（未改）
- **legacy provider-visible schema snapshot/parity**: 本段未改 projection 语义；仍以 HARD STOP E 为准
- **Critical Product Smoke**: **automated gate + router matrix passed; manual GUI validation pending**
- **Manual diff review（Step 54）**:
  - 仅 46–48 相关：batching 文案注入、duplicate 计数/outbound 警告、instrumentation 模块与日志接线
  - **无** unrelated cleanup；**无** risky default 翻转；**无** silent capability 删除（registry/schema 未裁；guidance 仅追加）
  - 用户 D-131 dirty 文件未并入本 run 逻辑改动
- **Rollback point**:
  - HEAD 仍为 `1f6b01b`
  - 丢弃本 run：删除 `coworker/turn_instrumentation.py`、`tests/test_tool_batching_and_duplicate.py`、`tests/test_turn_instrumentation.py`；还原 `coworker/agent.py` / `coworker/engine.py` / `coworker/providers/openai_provider.py` 中 46–48 hunk；还原 README/AGENTS/execution-log 本条目
  - **勿** checkout 用户 D-131 或 A–G 无关文件
- **Remaining risks**:
  - 生产 built-in 仍 OFF，真实会话仍 100% legacy（无 Router/Projection/structured streaming/EF）
  - Manual GUI smoke A–P 尚未补验
  - 用户 dirty 与 A–G+46–55 Plan 改动并存；正式 commit 须用户点名且隔离 D-131
- **Next run allowed range**: **仅 V5 POST-REGRESSION ROLLOUT**（steps 56–59；一次一个故障域；须新独立授权）。**不得**在无授权时改任何 risky built-in default。

---

**FINAL REGRESSION 46–55 completed. Default enablement rollout NOT started.**

---

### POST-REGRESSION ROLLOUT Step 56 — `request_routing_enabled` candidate ON（2026-08-13）

- **Run / HARD STOP ID**: `ROLLOUT Step 56 only`（独立授权；禁止 Step 57+）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty + A–G/46–55 未提交改动，避免混入）
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、`DECISIONS.md`、`DOMAIN.md`、v5 Plan §65 Step 56 / POST-REGRESSION ROLLOUT STOP、本 execution log FINAL REGRESSION 条目
- **Allowed Section 65 step range**: **step 56 only**
- **Expected files/symbols**:
  - `coworker/config.py`：`request_routing_enabled` built-in `False` → `True`
  - 默认值断言测试同步；其余三个 risky defaults 保持 `False`
- **Actual changed files**（本 run）:
  - `coworker/config.py`
  - `tests/test_config.py`、`tests/test_request_router.py`、`tests/test_capability_preservation_gate.py`、`tests/test_execution_profile.py`、`tests/test_engine_budget.py`
  - `docs/chemclaw/README.md`、`AGENTS.md`、本 execution log
- **Key diff summary**:
  - 仅翻转 `request_routing_enabled` built-in default 为候选 ON
  - `tool_projection_enabled` / `structured_tools_true_streaming_enabled` / `emergency_finalization_enabled` **仍 OFF**
  - 显式 `request_routing_enabled=False` 仍可恢复 `route_request` → `None`（legacy-inert）
  - `build_engine` 仍不自动调用 `resolve_execution_profile`（需调用方传入 `execution_profile`）；本步不扩接线 scope
- **PASS**:
  - Router + pending/product-action + projection/policy/config/budget 定向：`test_request_router` + `test_capability_preservation_gate` + `test_config`（deselect symlink）+ `test_execution_profile` + `test_engine_budget` + `test_tool_projection` + `test_tool_policy` → **100 passed**, 1 deselected
  - Capability smoke：memory/skills/ask/plan/resume/automation/wake/connectors/mcp/persona/permissions/engine_stop → **187 passed**, 1 existing fail
  - 直接冒烟：`Config()` 默认 ON；pending_ask_user → `pending_state`/`AGENT`；写文件类 → `product_action`；问候 → `FAST_CHAT` 0 classifier；显式 OFF → `None`
- **EXISTING FAIL**:
  - `tests/test_durable_resume.py::test_durable_resume_approval_executes_tool`（与 FINAL REGRESSION 46–55 / HARD STOP A 指纹一致；文件无 `request_routing` 引用）
- **NEW FAIL**: **none**
- **NOT RUN**: Step 57–59；真实 GUI live-model smoke A–P
- **ENV BLOCKED**:
  - Manual GUI smoke A–P：**ENV BLOCKED — manual validation pending**
  - 系统 Temp PermissionError → worktree `--basetemp`
- **request_routing_enabled built-in/test values**: **built-in 候选 ON**（Step 56）；测试仍覆盖显式 OFF
- **tool_projection_enabled built-in/test values**: **built-in OFF**（未改）
- **structured-tools streaming built-in/test values**: **built-in OFF**（未改）
- **emergency finalization built-in/test values**: **built-in OFF**（未改）
- **Critical Product Smoke**: automated router/capability gate **passed**；manual GUI **pending**
- **Rollback point**:
  - 将 `coworker/config.py` `request_routing_enabled` 恢复 `False`，并还原本 run 默认值断言测试与 README/AGENTS/execution-log 本条目
  - **勿** checkout 用户 D-131 或无关 A–G 文件
- **Remaining risks**:
  - 会话路径若未显式传入 `execution_profile`，真实 turn 仍可能走 legacy（Config 默认 ON 主要激活 `route_request(Config())` / 调用方门控）
  - Manual GUI smoke 仍未补验
  - projection / structured streaming / EF 仍 OFF，尚未获得其收益或风险
- **Next run allowed range**: **仅 Step 57**（`tool_projection_enabled` OFF→候选 ON）且须**新独立授权**。本 run **STOP**。

---

**ROLLOUT Step 56 completed. Step 57 NOT started.**

---

### POST-REGRESSION ROLLOUT Step 57 — `tool_projection_enabled` candidate ON（2026-08-13）

- **Run / HARD STOP ID**: `ROLLOUT Step 57 only`（独立授权；禁止 Step 58+）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty + A–G/46–56 未提交改动，避免混入）
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、`DECISIONS.md`、`DOMAIN.md`、v5 Plan §65 Step 57 / POST-REGRESSION ROLLOUT STOP、本 execution log Step 56 条目
- **Step 56 precondition**: **稳定通过**（NEW FAIL = none；projection/streaming/EF 仍 OFF）
- **Allowed Section 65 step range**: **step 57 only**
- **Expected files/symbols**:
  - `coworker/config.py`：`tool_projection_enabled` built-in `False` → `True`
  - 默认值断言测试同步；structured streaming / EF 保持 `False`
- **Actual changed files**（本 run）:
  - `coworker/config.py`
  - `coworker/agent.py`、`coworker/request_router.py`、`coworker/tool_projection.py`（注释同步）
  - `tests/test_config.py`、`tests/test_capability_preservation_gate.py`
  - `docs/chemclaw/README.md`、`AGENTS.md`、本 execution log
- **Key diff summary**:
  - 仅翻转 `tool_projection_enabled` built-in default 为候选 ON
  - `structured_tools_true_streaming_enabled` / `emergency_finalization_enabled` **仍 OFF**
  - 显式 `tool_projection_enabled=False` 仍恢复 legacy full provider-visible schema（含 FAST_CHAT）
  - 默认 ON + FAST → `tools=None`；AGENT 保留 unknown custom tool
- **PASS**:
  - legacy schema parity + projection/policy/router/config/profile：`test_tool_projection_parity` + `test_tool_projection` + `test_legacy_tool_schema_snapshot` + `test_capability_preservation_gate` + `test_tool_policy` + `test_request_router` + `test_config`（deselect symlink）+ `test_execution_profile` → **100 passed**, 1 deselected
  - Capability smoke：memory/skills/ask/plan/resume/automation/wake/connectors/mcp/persona/permissions/engine_stop → **187 passed**, 1 existing fail
  - 直接冒烟：`Config()` projection ON；streaming/EF OFF；OFF→legacy full schema；ON+FAST→`tools=None`；AGENT 保留 unknown tool；`不要联网`+本地文件用例已在 `test_request_router` 覆盖并通过
- **EXISTING FAIL**:
  - `tests/test_durable_resume.py::test_durable_resume_approval_executes_tool`（与 FINAL REGRESSION 46–55 / Step 56 指纹一致；非本段引入）
- **NEW FAIL**: **none**
- **NOT RUN**: Step 58–59；真实 GUI live-model smoke A–P
- **ENV BLOCKED**:
  - Manual GUI smoke A–P：**ENV BLOCKED — manual validation pending**
  - 系统 Temp PermissionError → worktree `--basetemp`
- **request_routing_enabled built-in/test values**: **built-in 候选 ON**（Step 56；未改）
- **tool_projection_enabled built-in/test values**: **built-in 候选 ON**（Step 57）；测试仍覆盖显式 OFF→legacy parity
- **structured-tools streaming built-in/test values**: **built-in OFF**（未改）
- **emergency finalization built-in/test values**: **built-in OFF**（未改）
- **legacy provider-visible schema snapshot/parity**: **PASS** — 显式 OFF 与 HARD STOP D/E 路径一致；ON 路径不永久删 registry
- **Critical Product Smoke**: automated parity/capability gate **passed**；manual GUI **pending**
- **Rollback point**:
  - 将 `coworker/config.py` `tool_projection_enabled` 恢复 `False`，并还原本 run 默认值断言测试与 README/AGENTS/execution-log 本条目
  - **勿** checkout 用户 D-131 或无关 A–G 文件
- **Remaining risks**:
  - 会话路径若未显式传入 `execution_profile` / 投影门控，真实 turn 仍可能走 legacy full schema
  - Manual GUI smoke 仍未补验
  - structured streaming / EF 仍 OFF，尚未获得其收益或风险
- **Next run allowed range**: **仅 Step 58**（structured-tools true streaming known-safe 候选 ON）且须**新独立授权**。本 run **STOP**。

---

**ROLLOUT Step 57 completed. Step 58 NOT started.**

---

### POST-REGRESSION ROLLOUT Step 58 — `structured_tools_true_streaming_enabled` known-safe candidate ON（2026-08-13）

- **Run / HARD STOP ID**: `ROLLOUT Step 58 only`（独立授权；禁止 Step 59）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty + A–G/46–57 未提交改动，避免混入）
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、`DECISIONS.md`、`DOMAIN.md`、v5 Plan §65 Step 58 / POST-REGRESSION ROLLOUT STOP、本 execution log Step 57 条目
- **Step 57 precondition**: **稳定通过**（NEW FAIL = none；streaming/EF 当时仍 OFF）
- **Allowed Section 65 step range**: **step 58 only**
- **Expected files/symbols**:
  - `coworker/config.py`：`structured_tools_true_streaming_enabled` built-in `False` → `True`
  - known-safe matrix 不变；unknown/custom 仍 compat-buffered + salvage-safe
  - 默认值断言测试同步；`emergency_finalization_enabled` 保持 `False`
- **Actual changed files**（本 run）:
  - `coworker/config.py`、`coworker/engine.py`（注释）
  - `tests/test_config.py`、`tests/test_capability_preservation_gate.py`、`tests/test_providers.py`（docstring）
  - `docs/chemclaw/README.md`、`AGENTS.md`、本 execution log
- **Key diff summary**:
  - 仅翻转 `structured_tools_true_streaming_enabled` Config built-in default 为候选 ON
  - `is_known_safe_structured_tools_streaming` 矩阵未扩大：stock OpenAI / Azure GPT-/o-family only
  - ApiHub / Ollama / DashScope / arbitrary custom host：**即使开关 ON 也走 buffered + salvage**
  - 显式 `structured_tools_true_streaming_enabled=False` 仍无缝回到 compat-buffered + textual salvage
  - `emergency_finalization_enabled` **仍 OFF**
  - TurnEngine ctor 默认仍 `False`（单测隔离）；生产经 `build_engine` 读 Config
- **PASS**:
  - structured streaming + salvage + kill switch + Stop/EF guards：`test_providers` + `test_provider_router` + `test_config`（deselect symlink）+ `test_capability_preservation_gate` + `test_engine_stop` + `test_emergency_finalization` → **120 passed**, 1 deselected
  - engine / budget smoke：`test_engine` + `test_engine_budget` → **23 passed**
  - 直接冒烟：`Config()` streaming ON；EF OFF；routing/projection 仍 ON
- **EXISTING FAIL**: none in this targeted set（symlink deselect；durable_resume approval 未本段复跑，指纹仍属既有 EXISTING）
- **NEW FAIL**: **none**
- **NOT RUN**: Step 59；真实 GUI live-model smoke A–P；full pytest
- **ENV BLOCKED**:
  - Manual GUI smoke A–P：**ENV BLOCKED — manual validation pending**
  - 系统 Temp PermissionError → worktree `--basetemp`
- **request_routing_enabled built-in/test values**: **built-in 候选 ON**（Step 56；未改）
- **tool_projection_enabled built-in/test values**: **built-in 候选 ON**（Step 57；未改）
- **structured-tools streaming built-in/test values**: **built-in 候选 ON**（Step 58；known-safe only）；测试仍覆盖显式 OFF→compat-buffered + salvage；unknown host ON→仍 buffered
- **emergency finalization built-in/test values**: **built-in OFF**（未改）
- **legacy provider-visible schema snapshot/parity**: 未本段复跑（Step 57 已绿；本段未改 projection）
- **Critical Product Smoke**: automated structured/salvage/Stop gate **passed**；manual GUI **pending**
- **Rollback point**:
  - 将 `coworker/config.py` `structured_tools_true_streaming_enabled` 恢复 `False`，并还原本 run 默认值断言测试与 README/AGENTS/execution-log 本条目
  - **勿** checkout 用户 D-131 或无关 A–G 文件
- **Remaining risks**:
  - ChemClaw 默认模型为 ApiHub `deepseek-v4-flash` → **不在 known-safe 矩阵**，生产默认路径仍 buffered（本开关主要惠及 stock OpenAI/Azure GPT-/o）
  - Manual GUI smoke 仍未补验
  - EF 仍 OFF，尚未获得其收益或风险
- **Next run allowed range**: **仅 Step 59**（Emergency Finalization 候选 ON）且须**新独立授权**。本 run **STOP**。

---

**ROLLOUT Step 58 completed. Step 59 NOT started.**

### POST-REGRESSION ROLLOUT Step 59 — `emergency_finalization_enabled` candidate ON（2026-08-13）

- **Run / HARD STOP ID**: `ROLLOUT Step 59 only`（独立授权；四开关最后一故障域；禁止额外架构修改）
- **Start SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`
- **End/checkpoint SHA**: `1f6b01b72aa16cf461e1a0040ea46dbf3ad67f26`（**无 checkpoint commit** — 工作区含用户 D-131 dirty + A–G/46–58 未提交改动，避免混入）
- **User-existing dirty changes**: **是** — D-131 等相关未提交改动；本 run **未覆盖/吸收**
- **Governance/design files re-read**: `AGENTS.md`、`docs/chemclaw/README.md`、`DECISIONS.md`、`DOMAIN.md`、v5 Plan §65 Step 59 / POST-REGRESSION ROLLOUT STOP、本 execution log Step 58 条目
- **Step 58 precondition**: **稳定通过**（NEW FAIL = none；EF 当时仍 OFF）
- **Allowed Section 65 step range**: **step 59 only**
- **Expected files/symbols**:
  - `coworker/config.py`：`emergency_finalization_enabled` built-in `False` → `True`
  - 默认值断言 / soft-budget 在 EF ON 下的 hard+1 finalization 断言同步
  - **禁止**：新架构；扩大 known-safe；改其它开关
- **Actual changed files**（本 run）:
  - `coworker/config.py`
  - `tests/test_config.py`、`tests/test_capability_preservation_gate.py`、`tests/test_execution_profile.py`、`tests/test_emergency_finalization.py`、`tests/test_engine_budget.py`
  - `docs/chemclaw/README.md`、`AGENTS.md`、本 execution log
- **Key diff summary**:
  - 仅翻转 `emergency_finalization_enabled` Config built-in default 为候选 ON
  - AGENT/DEEP/VERIFIED profile 镜像 Config → EF ON；FAST/KNOWLEDGE **仍强制 OFF**
  - TurnEngine ctor 默认仍 `False`（单测隔离）；生产经 `build_engine` 读 Config
  - 显式 `emergency_finalization_enabled=False` / kill switch OFF → 仍 legacy hard-limit（无 `best_effort_finalized`）
  - soft-budget 回归：hard ceiling 工具轮次不变 + 额外一次 model-only finalization（`calls == hard+1`，`best_effort_finalized=True`）
  - Stop / unanswered trailing tool calls（ask_user·approval·plan·directory）/ durable resume pending → **不**触发 EF
  - unfinished side-effect：finalization `tools=None` 且忽略模型仍返回的 tool_calls（不执行）
- **PASS**:
  - hard-ceiling + Stop + pending + durable + standing approvals + EF + config/profile/capability：
    `test_emergency_finalization` + `test_engine_budget` + `test_engine_stop` + `test_execution_profile` + `test_engine` + `test_ask_user_upgrades` + `test_plan_mode` + `test_durable_resume` + `test_standing_approvals` + `test_config`（deselect symlink）+ `test_capability_preservation_gate`
    → **102 passed**, 1 existing fail, 1 deselected
- **EXISTING FAIL**:
  - `tests/test_durable_resume.py::test_durable_resume_approval_executes_tool`（Inbox pending）— HARD STOP A/C/D/E/G / Step 56–58 已记；指纹不变；**非本段引入**
- **NEW FAIL**: **none**
- **NOT RUN**: 额外架构；合集 P0；真实 GUI live-model smoke A–P；full pytest
- **ENV BLOCKED**:
  - Manual GUI smoke A–P：**ENV BLOCKED — manual validation pending**
  - 系统 Temp PermissionError → worktree `--basetemp`
- **request_routing_enabled built-in/test values**: **built-in 候选 ON**（Step 56；未改）
- **tool_projection_enabled built-in/test values**: **built-in 候选 ON**（Step 57；未改）
- **structured-tools streaming built-in/test values**: **built-in 候选 ON**（Step 58；known-safe only；未改）
- **emergency finalization built-in/test values**: **built-in 候选 ON**（Step 59）；测试仍覆盖显式 OFF→legacy hard-limit；Stop/pending guards
- **legacy provider-visible schema snapshot/parity**: 未本段复跑（未改 projection）
- **Critical Product Smoke**: automated EF/Stop/pending/resume gate **passed**；manual GUI **pending**
- **Rollback point**:
  - 将 `coworker/config.py` `emergency_finalization_enabled` 恢复 `False`，并还原本 run 默认值/soft-budget 断言与 README/AGENTS/execution-log 本条目
  - **勿** checkout 用户 D-131 或无关 A–G/56–58 文件
- **Remaining risks**:
  - Manual GUI smoke 仍未补验
  - 真实 hard-ceiling 路径现会多一次 model-only finalization（成本/延迟）；kill switch 可立即回退
  - ApiHub 默认模型仍不在 structured streaming known-safe；与 EF 正交
- **Next run allowed range**: **无自动后续 Section 65 步骤**。四开关独立 rollout **全部完成**。下一刀须**新独立授权**（合集 P0 / 其它产品门禁）。本 run **STOP**。

---

**ROLLOUT Step 59 completed. V5 POST-REGRESSION ROLLOUT (56–59) COMPLETE. No further automatic phases.**

