# Phase 6：企业微信智能机器人 — 实施计划

- 日期：2026-08-26
- 决策：D-188
- 规格：`docs/superpowers/specs/2026-08-26-chemclaw-wecom-ai-bot-channel-design.md`

## 步骤

1. **文档**：规格 + 本计划 + `DECISIONS` D-188 + `README` 门禁。
2. **`coworker/channels/`**：`models.py`、`mappings.py`、`__init__.py`；帧 fixture → `MessageEvent` 单测。
3. **Connector**：`descriptors` 增加 `wecom`；`config.PLATFORMS`；`make_adapter`；`WecomBotAdapter`；`senders` + `_resolve_token`；optional `wecom` extra。
4. **GUI**：logo registry、中英向导文案（descriptor instructions + i18n 若需）。
5. **出站/回执**：入站 progress ack；`send_message` 走 live WS。
6. **测试**：`tests/test_wecom_channel.py`；聚焦 gateway/connectors 不破。

## 回退

- Descriptor `available=False` 或移除 `make_adapter("wecom")` 分支；关掉 optional extra。
- OFF：SecretStore 去掉 `wecom:default` 即停 listener。

## 测试命令

```text
pytest tests/test_wecom_channel.py tests/test_connectors.py -q --tb=line
python -m compileall -q coworker/channels coworker/connectors/wecom_bot.py
```

## 真人验收清单

- [ ] 企微后台创建智能机器人，API 模式·长连接，复制 bot_id/secret
- [ ] ChemClaw 连接页连接成功，gateway 日志无凭据明文
- [ ] 私聊一轮问答
- [ ] 群聊 @ChemClaw 一轮；未 @ 不响应
- [ ] 错误凭据中文提示；断网后重连
