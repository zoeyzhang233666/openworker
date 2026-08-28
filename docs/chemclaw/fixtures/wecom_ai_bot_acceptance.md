# D-188 真人验收清单（企业微信智能机器人）

规格：`docs/superpowers/specs/2026-08-26-chemclaw-wecom-ai-bot-channel-design.md`

## 前置

1. ChemClaw 运行环境已装 messaging（含 `wecom-aibot-sdk>=1.0.8`）。开发态：`.\.venv\Scripts\python.exe -m pip install "wecom-aibot-sdk>=1.0.8"` 或 `pip install -e ".[messaging]"`
2. 企业微信管理后台创建智能机器人，开启 **API 模式 · 长连接**，复制 Bot ID / Secret
3. **重启** ChemClaw sidecar 后打开「连接」

## 清单

- [ ] 连接设置出现「企业微信」卡片，向导说明无需公网 URL
- [ ] 填入 bot_id/secret 后连接成功；断连后可再连
- [ ] 错误凭据或未装 SDK 时显示中文错误（无凭据明文进日志）
- [ ] 私聊机器人一轮问答，回复经 `send_message` / live WS 回到同一会话
- [ ] 群聊 @ChemClaw 一轮有应答；未 @（若平台仍推送）不误答
- [ ] 未在允许名单的用户消息被 park，可用 Capture / Allow
- [ ] 入站后可见「ChemClaw 正在处理…」回执（可用 `CHEMCLAW_WECOM_ACK=0` 关闭）
- [ ] 断网后重连，再发消息仍可达

## 自动化（已跑）

```text
pytest tests/test_wecom_channel.py → 22 passed
pytest connectors 子集（list/descriptors/make_adapter）→ 4 passed
vitest ConnectorIcon.test.tsx（含 wecom logo）
```
