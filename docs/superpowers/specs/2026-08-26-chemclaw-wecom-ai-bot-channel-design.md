# ChemClaw Phase 6：企业微信智能机器人 Channel 设计

- 日期：2026-08-26
- 决策：D-188
- 状态：已批准（随实施一并落地）

## 1. 问题与目标

ChemClaw「连接」页仅有海外 IM（Slack/Telegram 等），国内企业用户无法在企业微信里与 ChemClaw 对话。Phase 6 首版接入**企业微信智能机器人（API 模式 · WebSocket 长连接）**，桌面端无需公网回调 URL。

## 2. 已锁定决策

- **形态**：智能机器人长连接（`wss://openws.work.weixin.qq.com`）；**不做**自建应用 HTTP 回调、群机器人 Webhook、客服、飞书/钉钉。
- **架构**：复用现有 `coworker/connectors` Gateway / `BasePlatformAdapter` / `MessageEvent`（对齐 Slack Socket Mode）；薄层 `coworker/channels/` 仅放统一消息模型与映射。
- **禁止**：第二套 SessionManager；LangBot/CowAgent Agent runtime；Channel 用户默认获得本机 Shell/文件/CRM。

## 3. Donor 审计

| Donor | 固定版本 | 吸收 | 不引入 | 许可 |
|-------|----------|------|--------|------|
| LangBot | `08307790e55a0d82db073025fd39ca3ee0a8f04c`（`wecombot` adapter 形态） | Adapter/Gateway 分层、群聊 @、事件映射思路 | Agent/RAG/Plugin runtime | Apache-2.0 |
| wecom-aibot-sdk | **1.0.8**（optional extra `wecom`） | WS 认证、心跳、流式回复、主动 `send_message`、文件解密 | 业务 Agent | MIT |

## 4. 消息合同

### 4.1 `InboundMessage` / `OutboundMessage`

见 `coworker/channels/models.py`。字段对齐交接文档 Phase 6：`channel`、`conversation_id`、`user_id`、`message_id`、`text`、`mentions`、`attachments`、`metadata`；出站含 `kind`（progress/final/error）、`reply_to`。

### 4.2 映射

WeCom WS 帧 → `InboundMessage` → 现有 `MessageEvent`/`SessionSource`（`platform="wecom"`）。

- 群聊：`chat_type=group`；未 @ 机器人则丢弃（`mentions_me=False` 且非私聊）。
- 私聊：`chat_type=dm`。
- `chat_id`：优先会话 `chatid` / `conversation_id`；缺省回落 userid。
- 幂等：以 frame `msgid` / `req_id` 为 `message_id`。

## 5. 连接与凭据

- Connector id：`wecom`；SecretStore：`wecom:default` → `{bot_id, secret, enabled, allowed_users, account}`。
- GUI：连接设置可连可断；向导说明开启 API 模式·长连接、粘贴 bot_id/secret、**无需公网 URL**。
- Allowlist：空 = 拒收并 park（对齐 Telegram/Slack）。
- Optional dep：`pip install coworker[wecom]` → `wecom-aibot-sdk>=1.0.8`；未安装时 connect 失败并中文提示。

## 6. 出站与长任务

- `send_message` target：`wecom:{chat_id}`；经 live adapter（WS `send_message`），非 HTTP bot_token。
- 入站后立即发 progress 回执「ChemClaw 正在处理…」（流式中间帧或主动推送）；终态由会话 `send_message` 或 adapter 终帧发送。
- 流式：SDK `reply_stream` 可用时优先；否则缓冲一次发送。

## 7. 安全

- SecretStore 存凭据；禁止进日志与模型上下文。
- 附件：下载解密后写入会话安全目录；大小/类型上限；拒绝路径穿越。
- Channel 用户不提升 PermissionEngine 能力面。
- 群/私聊 session 隔离；跨渠道合并须显式映射（首版不做）。

## 8. 非目标

飞书、钉钉、自建应用回调、内网穿透、云 relay、Room、改 Agent Loop / 市场口径。

## 9. 验收

见实施计划：映射单测、adapter mock、connect REST、GUI 卡片、真人企微清单。
