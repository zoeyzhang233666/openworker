# D-205：OpenCode Go 会话 Header 兼容设计

## 问题与目标

OpenAI provider 配置自定义端点 `https://opencode.ai/zen/go/v1` 时走 Chat Completions。OpenCode Go 要求同一对话的请求携带稳定的 `x-opencode-session`，而 ChemClaw 已由 `SessionManager → build_engine → engine.audit_context["session_id"]` 持有稳定会话 ID。

本次直接复用该 ID，不生成新 ID，不增加 User-Agent，不改变 retry、streaming、tool-call 或其他 provider 行为。

## 设计

- `TurnEngine` 在每次 provider stream 调用中附带仅供 ChemClaw provider transport 使用的内部参数 `_opencode_session_id`。
- `ProviderRouter` 消费该参数；只有目标客户端是 `OpenAIProvider`（Chat Completions）时才继续传递，其他 provider 不可见该参数。
- `OpenAIProvider` 在构造 SDK 请求前弹出内部参数。仅当解析后的 hostname 为 `opencode.ai`，且规范化 path 为 `/zen/go/v1` 或其子路径时，使用 OpenAI SDK per-request `extra_headers` 注入 `x-opencode-session`。
- stream 重试复用同一 SDK kwargs；stream transport 全部失败转 `complete()` 时显式传回已消费的 session ID，保证 fallback header 不丢失。
- 官方 OpenAI Responses、Azure、Ollama、DeepSeek 官方及其他 OpenAI-compatible endpoint 不自动注入该 header。

## 验收与回退

- 覆盖 stream、complete、stream→complete fallback。
- 同一 session 多次调用值一致，不同 session 值可不同。
- 内部参数不进入 SDK API request kwargs/body；普通兼容端点无自动 header。
- 运行 provider、router、engine 定向测试。
- 回退只需撤销 D-205 的内部参数传递、endpoint helper 与测试，不涉及持久数据迁移。
