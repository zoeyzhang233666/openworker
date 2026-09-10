# D-205：OpenCode Go 会话 Header 兼容实施计划

## 实施

- [x] 从 `TurnEngine.audit_context["session_id"]` 向 provider transport 传递内部会话参数。
- [x] 在 `ProviderRouter` 隔离非 Chat Completions provider。
- [x] 在 `OpenAIProvider` 精确识别 OpenCode Go endpoint，并为 stream/complete 注入 per-request header。
- [x] 保证 stream transport fallback 到 complete 时保留 session ID。
- [x] 补齐 endpoint 隔离、稳定性、差异性、body 清洁与 fallback 测试。
- [x] 运行 provider/router/engine 定向回归并更新项目控制台。

## 验证结果

- `python -m pytest tests/test_providers.py tests/test_provider_router.py tests/test_engine.py -q --basetemp=.pytest-d205-escalated -p no:cacheprovider`：124 passed。
- `python -m compileall -q coworker/providers/openai_provider.py coworker/providers/router.py coworker/engine.py`：通过。
- 当前虚拟环境未安装 Ruff/Black，未执行可选格式检查器。

## 非目标

- 不增加 User-Agent。
- 不修改 provider 配置 UI、凭据格式、共享 SDK client 默认 header 或模型路由。
- 不构建安装程序、不合并 `main`。
