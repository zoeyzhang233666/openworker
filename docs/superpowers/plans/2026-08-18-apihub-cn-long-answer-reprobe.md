# ApiHub CN Long-Answer Reprobe Implementation Plan

**Goal:** Re-run D-161 live gallery with a long synthesis prompt. Copy only PASS `(host, model)` pairs into `_KNOWN_SAFE_COMPAT_PAIRS`. Do not lower the 200ms gate.

## Task 1: Long answer prompt + offline lock

**Files:** `tests/apihub_cn_stream_probe.py`, `tests/test_apihub_cn_stream_capability.py`

- [x] `ANSWER_USER_PROMPT` is long-form (no “one short sentence”); `MIN_ANSWER_DELTA_SPAN_MS` stays 200.
- [x] Offline unit tests still pass; new test asserts prompt is long-form.

## Task 2: Live N=3

- [x] `CHEMCLAW_LIVE_APIHUB_CN=1` against product `secrets.json`.
- [x] Write `docs/chemclaw/fixtures/apihub_cn_stream_capability.json` (`prompt_variant=long_answer`).

## Task 3: Allowlist + docs

- [x] Fill `_KNOWN_SAFE_COMPAT_PAIRS` from fixture PASS only (`deepseek-v4-pro`, `glm-5.2`).
- [x] D-163 in DECISIONS / README / AGENTS; D-161 spec notes the re-probe.
