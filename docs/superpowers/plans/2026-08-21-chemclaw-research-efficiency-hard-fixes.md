# D-179 研究效率首包硬伤修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix research-subagent efficiency hard bugs from the methanol arbitrage retrospective so ChemClaw wastes fewer rounds and can salvage long turns.

**Architecture:** Inherit parent `MarketToolSelection` via background-task metadata; treat ApiHub generic invalid as compact-retryable; stop OHLC product labels from overwriting `TOOL_FINISHED.name`; give research `grep` and Windows UTF-8 shell defaults.

**Tech Stack:** Python TurnEngine / SubagentRuntime, React GUI App.tsx, pytest + vitest.

## Global Constraints

- Do not weaken D-166/D-177 market guards (no cross-substitution).
- Do not add `run_shell` to research allowlist.
- Do not implement MCP price timeouts, full tool-trace, or wall-time budgets in this cut.
- First-party errors remain zh-CN where newly surfaced.

---

## Task 1: Spec + decision registration

- [x] Design + this plan exist under `docs/superpowers/`.
- [x] Append D-179 to `docs/chemclaw/DECISIONS.md` and top status to `docs/chemclaw/README.md`.

## Task 2: Sidecar name collision (TDD)

- [x] Failing test: merged `TOOL_FINISHED` keeps tool name; sidecar has `series_name`.
- [x] Change `chart_finished_sidecar`; map in `ohlcChartPreviewFromEvent`.
- [x] Pass focused engine + GUI chart tests.

## Task 3: Market scope inheritance (TDD)

- [x] Snapshot parent selection into task metadata on `start_subagent`.
- [x] Child engine applies inherited selection in `_activate_plan` / guard.
- [x] Tests: parent dual scope → child allows spot + CN futures; no widen beyond parent.

## Task 4: Invalid provider reject retry (TDD)

- [x] `is_retryable_provider_reject` + engine compact-once retry.
- [x] Second failure → EF salvage path + Chinese friendly error.
- [x] Research instructions: write report file before short final bubble.

## Task 5: grep + UTF-8 + cowork hint

- [x] research allowlist includes `grep`.
- [x] Windows PersistentShell UTF-8 env + console encoding init.
- [x] cowork instructions prefer `grep`/`read_file` for UTF-8 text.

## Task 6: Verification

- [x] Focused pytest suites green (35 focused + 40 broad subagent/EF/cohort).
- [x] README status updated with real pass counts.
