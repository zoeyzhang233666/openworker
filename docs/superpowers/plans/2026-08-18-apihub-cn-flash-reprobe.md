# ApiHub CN Flash-Only Reprobe Plan

**Goal:** Re-run D-163 long-answer live probe for `deepseek-v4-flash` only. Merge fixture. Allowlist only on PASS.

- [x] Merge helper keeps Pro/GLM rows; offline unit test.
- [x] Live N=3 Flash (`CHEMCLAW_LIVE_APIHUB_CN=1`, `CHEMCLAW_LIVE_APIHUB_CN_MODELS=deepseek-v4-flash`).
- [x] PASS → add pair; FAIL → leave Flash buffered. Docs D-164.
