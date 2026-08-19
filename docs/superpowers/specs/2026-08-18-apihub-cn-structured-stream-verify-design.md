# ApiHub CN 带工具真流式单独验证（D-161）

**日期**：2026-08-18  
**状态**：已落地（live 无 PASS，对表空）  
**范围**：只扩大 `is_known_safe_structured_tools_streaming` 的精确 `(host, model)` 对表。不改 Fast Router、龙虾等待、思考块收起、Intl、Ollama、DashScope。

## 背景

`structured_tools_true_streaming_enabled` 已候选 ON，但 known-safe 仅官方 OpenAI/Azure 的 GPT-/o 族。生产默认 `apihub-cn:deepseek-v4-flash` 以及 ApiHub CN 画廊另外三个模型走 `compat_buffered`。真流式路径不做 textual salvage；未验证就放行会把工具调用正文泄漏到 UI。

## 对象

主机只认 `apihub.chem-cloud.cn`。模型各自独立判定：

- `deepseek-v4-flash`
- `deepseek-v4-pro`
- `glm-5.2`
- `kimi-k3`

用户把 `apihub-cn` 的 endpoint 改到其他 host 时，即使模型名相同也不进白名单。

## 探针

Opt-in：`CHEMCLAW_LIVE_APIHUB_CN=1`。密钥：`SecretStore` `provider:apihub-cn` 或 env `APIHUB_CN_API_KEY`。CI 默认 skip。

每个模型 N=3。观察器强制走 `_iter_true_stream_chunks`（绕过生产矩阵），以记录网关原生行为。生产路径在写入对表前保持 buffered。

1. 工具轮：无副作用 `echo_probe(token)`，必须调用。
2. 综合轮：仍 `tools!=None`，把工具结果塞回，要求一句短确认。

## PASS（须全部成立）

- 3 次工具轮都得到结构化 `tool_calls`（名称 `echo_probe`），`_maybe_salvage_tool_calls` 不会触发
- 工具轮 `content` 不含可 salvage 的工具正文
- 综合轮至少 2 个 `text_delta`，且首末 delta 墙钟间隔 ≥200ms
- 3 次均无 semantic progress 之后的 `incomplete chunked read` / connection error
- 若最终 `turn.reasoning` 非空，则必须出现过 `reasoning_delta`；没有 reasoning 不算失败

任一失败 → 该对 `FAIL`，保持 buffered。无密钥 / 429 / 网关不可达 → `ENV_BLOCKED`，不改矩阵。

## Live 结果（2026-08-18 短答）

四模型均 **FAIL**，当时对表为空：`flash`/`pro`/`glm-5.2` 为短答 `answer_burst`（结构化工具与 reasoning 已流式到达）；`kimi-k3` 为网关 400 未定价。

长答再验见 **D-163**（不放宽 200ms）：`deepseek-v4-pro` / `glm-5.2` PASS 已进对表。

## 生产矩阵

```text
_KNOWN_SAFE_COMPAT_PAIRS: frozenset[tuple[str, str]]
```

仅探针 `PASS` 的 `(apihub.chem-cloud.cn, 裸模型名)` 写入。Kill switch OFF 仍 buffered。官方 OpenAI/Azure + GPT-/o 前缀规则不变。

## 非目标

首 token 前龙虾轮播、工具执行间隙空白、流式中出图、无 `reasoning_content` 时的灰色思考。本刀只解除 ChemClaw 对带工具 LLM 生成的整轮缓冲（且仅限 PASS 对）。
