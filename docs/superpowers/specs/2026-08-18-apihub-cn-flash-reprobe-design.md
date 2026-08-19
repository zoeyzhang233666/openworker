# ApiHub CN Flash 单独重跑（D-164）

**日期**：2026-08-18  
**状态**：已落地（Flash PASS，已写入对表）  
**范围**：D-163 长答协议下只重跑 `deepseek-v4-flash`。不放宽 200ms。不改默认模型、Fast Router、思考块、Intl。不重跑 Pro/GLM/Kimi。

## 背景

D-163：Flash 前两轮长答已增量（约 4.2–4.6s），第 3 次工具轮 `APITimeoutError`，N=3 未全过，默认对话仍 buffered。用户授权单独重跑 Flash。

## 协议

与 D-163 相同：N=3、长简报、≥200ms、结构化 `echo_probe`、无 salvage。夹具按模型合并，禁止用残缺画廊覆盖 Pro/GLM PASS。

PASS → 把 `(apihub.chem-cloud.cn, deepseek-v4-flash)` 写入对表。FAIL / ENV_BLOCKED → 对表不动 Flash。

## Live 结果（2026-08-18）

`CHEMCLAW_LIVE_APIHUB_CN=1` + `CHEMCLAW_LIVE_APIHUB_CN_MODELS=deepseek-v4-flash`，约 39s。

- `deepseek-v4-flash` **PASS**：三轮结构化 `echo_probe`；长答 420–440 个 `text_delta`，间隔约 4.7–5.1s；salvage 未触发。已写入对表。
- Pro / GLM 未重跑，夹具合并保留 D-163 PASS。
- `kimi-k3` 仍 FAIL。
