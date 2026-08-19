# ApiHub CN 长答再验（D-163）

**日期**：2026-08-18  
**状态**：已落地（pro / glm-5.2 PASS；flash / kimi-k3 FAIL）  
**范围**：在 D-161 协议上把综合轮从「一句短确认」改成足够长的正文再测增量间隔。不放宽 ≥200ms 门槛。不改 Fast Router、龙虾等待、思考块收起、Intl。

## 背景

D-161 短答 live：`flash`/`pro`/`glm-5.2` 结构化工具与 `reasoning_delta` 已到达，salvage 未触发；综合轮多 chunk 但首末 `text_delta` 间隔约 60–90ms（个别 glm 轮次可超过 200ms，三轮未全过），判 `answer_burst`。用户授权「用更长回答再验一次」，不授权放宽 200ms。

短答无法区分「网关在攒齐后一次性倾倒」和「正文太短、增量墙钟不够」。长答后若间隔仍 <200ms，维持 buffered；若 N=3 全过，才把精确 `(host, model)` 写入 `_KNOWN_SAFE_COMPAT_PAIRS`。

## 不变

- 主机只认 `apihub.chem-cloud.cn`
- 画廊：`deepseek-v4-flash` / `deepseek-v4-pro` / `glm-5.2` / `kimi-k3`
- N=3；工具轮 `echo_probe`；观察器仍强制 `_iter_true_stream_chunks`
- PASS 门槛与 D-161 相同（结构化 `tool_calls`、无 salvage、≥2 个 `text_delta` 且首末 ≥200ms、无 progress 后断流）
- Kill switch OFF、Intl、自定义 host 仍 buffered
- ENV_BLOCKED 不改矩阵

## 变化

综合轮用户提示改为中文长简报：至少 12 句、至少 400 汉字；须复述 token；禁止再调工具。200ms 数值不动。

## 非目标

不改龙虾轮播、思考块 UI、流式出图、200ms 常数。

## Live 结果（2026-08-18）

`CHEMCLAW_LIVE_APIHUB_CN=1`，host `apihub.chem-cloud.cn`，N=3，约 438s。

- `deepseek-v4-pro` **PASS**：三轮长答 `text_delta` 间隔约 2.8–8.0s，salvage 未触发。已写入对表。
- `glm-5.2` **PASS**：间隔约 3.4–5.4s。已写入对表。
- `deepseek-v4-flash` **FAIL**：前两轮长答已增量（约 4.2–4.6s），第 3 次工具轮 `APITimeoutError`。保持 buffered。
- `kimi-k3` **FAIL**：超时 + 网关 400 未定价。保持 buffered。
