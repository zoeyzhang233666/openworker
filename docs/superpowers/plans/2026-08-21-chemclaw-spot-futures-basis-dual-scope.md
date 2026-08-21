# D-177 期现套利双口径放行 — 实施计划

- 日期：2026-08-21
- 规格：`docs/superpowers/specs/2026-08-21-chemclaw-spot-futures-basis-dual-scope-design.md`
- 状态：已落地

## 步骤

1. `MarketIntentKind.CN_SPOT_FUTURES` + `_wants_spot_futures_dual` + `_resolved_dual_selection`
2. `guard_tool` / `tools_for_scope(None)` 并集放行；`render_market_turn_context` 双口径政策
3. 测试：`test_market_intent` 套利/基差/现货+期货 + Engine 双 Tool 不拦截
4. 文档：DECISIONS / DOMAIN / README；修订 D-166「默认单口径」表述

## 验证

```text
pytest tests/test_market_intent.py \
  tests/test_engine.py::test_market_guard_allows_spot_and_futures_for_basis_arb \
  tests/test_engine.py::test_market_guard_rejects_futures_after_spot_was_selected \
  tests/test_engine.py::test_market_guard_allows_selected_spot_after_ask_user \
  tests/test_engine.py::test_market_guard_survives_durable_resume_of_pending_clarification \
  tests/test_scenario_resolver.py tests/test_turn_planner.py tests/test_tool_projection.py
→ 54 passed
```
