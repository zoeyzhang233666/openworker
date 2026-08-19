# ApiHub CN Structured-Tools Streaming Verify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Independently verify ApiHub CN gallery models for tools-enabled true streaming and allowlist only PASS `(host, model)` pairs.

**Architecture:** Keep salvage on the compat-buffered path. Add an exact-pair table beside the existing OpenAI/Azure prefix matrix. A live opt-in probe forces true-stream observation; production stays buffered until PASS pairs are copied into the table.

**Tech Stack:** Python, OpenAI Chat Completions SDK, pytest skipif live gate.

## Global Constraints

- Host allowlist is exact hostname `apihub.chem-cloud.cn` plus exact model id (no prefix, no “OpenAI-compatible”).
- Kill switch `structured_tools_true_streaming_enabled=False` always restores compat-buffered + salvage.
- Do not enable Intl / Ollama / DashScope / custom hosts.
- Live probe is opt-in (`CHEMCLAW_LIVE_APIHUB_CN=1`); default CI skips it.
- ENV_BLOCKED or FAIL must not mutate `_KNOWN_SAFE_COMPAT_PAIRS`.

---

### Task 1: Exact-pair table (empty until live PASS)

**Files:**
- Modify: `coworker/providers/openai_provider.py`
- Modify: `tests/test_providers.py`
- Test: `tests/test_apihub_cn_stream_capability.py`

- [x] Characterization: ApiHub CN four gallery models remain False on the empty table.
- [x] Monkeypatch one pair → true known-safe; wrong host / sibling model still False.
- [x] Fake gated stream: pair + kill switch ON + `base_url=https://apihub.chem-cloud.cn/v1` yields before upstream finishes.
- [x] Kill switch OFF with the same pair still buffers.

### Task 2: Live probe (skip by default)

**Files:**
- Create: `tests/apihub_cn_stream_probe.py`
- Create: `tests/test_apihub_cn_structured_stream_live.py`
- Test: `tests/test_apihub_cn_stream_capability.py` (verdict helpers, no network)

- [x] Classify tool/answer runs against D-161 PASS gates.
- [x] Live test skip unless `CHEMCLAW_LIVE_APIHUB_CN=1`.
- [x] Write `docs/chemclaw/fixtures/apihub_cn_stream_capability.json` (no secrets).

### Task 3: Copy only PASS pairs into production table

- [x] Fill `_KNOWN_SAFE_COMPAT_PAIRS` from the fixture.
- [x] Update matrix assertions for those models only.
- [x] Intl and `custom.example` remain False.

### Task 4: Docs

- [x] `docs/chemclaw/DECISIONS.md` D-161
- [x] `docs/chemclaw/README.md` and `AGENTS.md` gate line with per-model verdicts

---

## Live results (2026-08-18)

`CHEMCLAW_LIVE_APIHUB_CN=1`, host `apihub.chem-cloud.cn`, N=3, ~124s.

- `deepseek-v4-flash` **FAIL** `answer_burst` ×3 — structured `echo_probe` + streamed `reasoning_delta`; short-answer text deltas span ~90ms (<200ms).
- `deepseek-v4-pro` **FAIL** `answer_burst` ×3 — same pattern.
- `glm-5.2` **FAIL** `answer_burst` ×3 — same pattern (~60ms).
- `kimi-k3` **FAIL** `transport_error` + `no_structured_tool` — HTTP 400, model not priced on this hub.

Production `_KNOWN_SAFE_COMPAT_PAIRS` remains empty. Salvage path unchanged.

## D-163 long-answer re-probe (2026-08-18)

Same 200ms gate. Synthesis prompt ≥12 sentences / ≥400 汉字. Live ~438s:

- `deepseek-v4-pro` **PASS** — allowlisted
- `glm-5.2` **PASS** — allowlisted
- `deepseek-v4-flash` **FAIL** — two long answers streamed; 3rd tool round `APITimeoutError`
- `kimi-k3` **FAIL** — timeout + 400 unpriced
