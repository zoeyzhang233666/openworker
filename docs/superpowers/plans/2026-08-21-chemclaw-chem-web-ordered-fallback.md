# D-181 化工行情 Web 有序降级 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 化工现货/国内期货/期现双口径默认放行 Web 作结构化空结果后的有序降级，并更新 prompt/决策文档。

**Architecture:** 仅改 `coworker/market_intent.py` 的 `supplemental_web` 注入与 `render_market_turn_context`；投影层继续消费 `allowed_tool_names`；守卫继续拦错口径。

**Tech Stack:** Python, pytest

---

## Task 1: Spec + decision registration

- [x] Design + this plan under `docs/superpowers/`
- [x] Append D-181 to `docs/chemclaw/DECISIONS.md`；修订 D-166/D-177 Web 措辞指向 D-181
- [x] Top status in `docs/chemclaw/README.md` + `AGENTS.md` 门禁条

## Task 2: Failing tests (TDD)

- [x] `test_market_intent.py`：化工三口径 + 研究套利句 web ∈ allowed；prompt 含有序降级；交叉替代/Yahoo 仍拒
- [x] `test_prompt_projection.py` / `test_turn_planner.py` / `test_tool_projection.py` / `test_agent_harness_routing.py`：同步旧「禁 web」断言

## Task 3: Implementation

- [x] 化工路径始终 `_unique_available(_WEB_TOOLS, available)`；股/期权/纯 Yahoo 仍仅 `_DRIVER_RE`
- [x] 重写 spot / CN futures / dual / clarify 的 market-scope-policy 文案

## Task 4: Verification

- [x] 聚焦 pytest 全绿并写实 README 通过数（61 + 23）
