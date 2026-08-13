# ChemClaw Context Compaction Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make OPE-27 summaries model-budgeted and diagnosable, then preserve deterministic continuity before the final Trim fallback.

**Architecture:** Keep the existing `TurnEngine → compaction.py → ProviderClient` seam. Add pure summary-budget/projection/failure types in `compaction.py`, let the engine enforce timeout and log metadata, and extend the existing mechanical state into the deterministic fallback. Reuse the provider-prefixed `compaction_model`; do not add a second routing engine.

**Tech Stack:** Python 3.11, pytest, existing ProviderClient/SessionManager, React/TypeScript copy only.

## Global Constraints

- Canonical transcript is never deleted or rewritten; only the outbound view changes.
- Summary failure never opens a blocking retry question.
- User-facing copy remains Chinese by default.
- Do not log prompt text, summary text, tool results, or credentials.
- Preserve existing uncommitted work and stage only files in this plan.

---

### Task 1: Summary budget and classified failures

**Files:**
- Modify: `tests/test_compaction.py`
- Modify: `coworker/compaction.py`

**Interfaces:**
- Produces: `SummaryBudget`, `summary_budget()`, `estimate_summary_tokens()`, `SummaryFailure`.
- Changes: `summarizer_messages(..., budget=...)` and `summarize_span(..., budget=...)`.

- [x] Write failing tests that hand-check 16k/32k/128k budgets, Chinese-heavy projections, reasoning-only responses, empty responses, and length-truncated responses.
- [x] Run `python -m pytest tests/test_compaction.py -q` and confirm failures name the missing interfaces/behavior.
- [x] Implement conservative token estimation, bounded event projection, visible-text output control, and classified `SummaryFailure` metadata.
- [x] Re-run `tests/test_compaction.py` and keep all existing compaction tests green.

### Task 2: Timeout, structured diagnostics, and deterministic continuity

**Files:**
- Modify: `tests/test_compaction_engine.py`
- Modify: `coworker/compaction.py`
- Modify: `coworker/engine.py`
- Modify: `coworker/server/manager.py`
- Modify: `coworker/server/app.py`

**Interfaces:**
- Consumes: Task 1 `SummaryBudget` and `SummaryFailure`.
- Produces: `build_deterministic_state(messages, keep_tokens, prior)`.
- Settings: `timeout_seconds` default 90; optional `summary_input_tokens` override.

- [x] Write failing tests for reasoning-only retry metadata, timeout-to-fallback, no sensitive text in warning logs, settings validation, and deterministic preservation of latest todo/artifact/assistant conclusion.
- [x] Run the focused tests and confirm expected RED failures.
- [x] Resolve the summarizer model context from `providers.matrix`, enforce `asyncio.wait_for`, log only numeric/classification metadata, and call deterministic state after two failures.
- [x] Extend mechanical extraction for `todo_write`, structured `artifact_path` results, and recent assistant conclusions; preserve old `CompactionState` serialization.
- [x] Re-run `tests/test_compaction.py tests/test_compaction_engine.py`.

### Task 3: Settings guidance and project documentation

**Files:**
- Modify: `surfaces/gui/src/components/SettingsView.tsx`
- Modify: `surfaces/gui/src/i18n.tsx`
- Modify: `surfaces/gui/src/api.ts`
- Modify: `docs/chemclaw/README.md`
- Modify: `docs/chemclaw/DECISIONS.md`
- Modify: `docs/chemclaw/DOMAIN.md`

**Interfaces:**
- Exposes optional timeout/input fields through the existing settings API type without adding advanced GUI controls.

- [x] Update the model help text to recommend a stable non-reasoning summarizer and explain provider-prefixed routing; add Chinese/English i18n entries.
- [x] Record the implemented OPE-27 behavior as the next decision and update README/DOMAIN without disturbing unrelated user edits.
- [x] Run backend focused regression, GUI i18n/localization tests, and TypeScript typecheck/build command used by this repository.
- [x] Inspect `git diff --check`, the scoped diff, and `git status`; leave implementation uncommitted because relevant files already contain overlapping user changes.
