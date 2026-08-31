# ChemClaw 多平台 Channel 与文件传输设计（D-193）

状态：**已实现（自动验收）**；真机租户验收仍为人工门禁。

## 目标与边界

ChemClaw 继续以现有 `SessionManager`、`TurnEngine`、MCP、`PermissionEngine` 与审计为唯一运行时。Channel 只负责平台协议、消息规范化和收发，不引入 CowAgent、LangBot 或任何第二套 Agent/Session 循环。

正式能力：

- 企业微信智能机器人：私聊、群聊 @、图片/文件双向传输；若真实租户证明确无员工私聊能力，再以同一接口增加自建应用适配器。
- 飞书与钉钉：私聊、群聊 @、图片/文件双向传输。
- 个人微信：腾讯官方 iLink，私聊和图片/文件双向传输；群聊固定不支持。
- 文件外发必须由用户明确要求并调用 `send_file`；生成产物不会自动发送。

## 深模块边界

`coworker.channels` 是稳定边界，吸收平台差异：

- `ChannelAdapter.start()/stop()/status()/send(envelope)`；旧 `BasePlatformAdapter.connect()/disconnect()/send(text)` 作为兼容壳。
- `InboundEnvelope` 包含 platform/account/conversation/user/chat/message/reply/context/attachments。
- `OutboundEnvelope` 包含 progress/final/error/text/image/file 与幂等键。
- `ChannelCapabilities` 是 UI 和运行时的唯一能力事实，不从 `two_way` 猜测文件、群聊或主动推送能力。
- 规范路由键为 `(platform, account_id, conversation_id)`；目标 token 兼容旧 `wecom:<conversation>`，多账号使用 `platform:<account>/<conversation>`。

## 会话与并发

- Channel 普通消息进入每会话 FIFO；相同会话严格串行，不同会话在全局 semaphore 下并行。
- 现有 GUI、self-wake 与 subagent 汇合语义不被全局改写。只有明确的停止/补充命令允许 steering；普通 Channel 消息不再注入当前轮次。
- 每轮有超时；超时、异常和取消均必须释放队列并继续下一条。
- 入站按 `(platform, account_id, message_id)` 有 TTL 去重；出站以幂等键抑制重复发送。
- 状态只记录认证/连接状态、最近收发时间、队列长度、重连次数和最近错误；不记录消息正文或 Secret。

## 媒体安全

- 入站附件完整传到 `MessageEvent`，由 `ChannelMediaManager` 下载或接收字节并保存到会话附件目录。
- 文件名必须取 basename 并清理控制字符；最终路径必须位于附件根目录内；拒绝符号链接、非普通文件、超限、扩展名/MIME 冲突和路径穿越。
- `send_file` 只读取当前会话 workspace 或显式 roots 中的普通非符号链接文件，继续使用独立 `requires_approval=True` 权限面。
- 平台适配器负责上传、平台加解密与平台大小限制，错误转换为不含凭据的中文可操作信息。
- 入站临时附件按 TTL 清理；工作区生成物不自动删除。

## 平台实现

- 企业微信锁定 `wecom-aibot-sdk==1.0.8`，继续使用 WebSocket；兼容旧 `wecom:default`，账号默认为 `default`。
- 飞书锁定 `lark-oapi`，WebSocket 客户端在专用线程/事件循环运行，事件映射后进入统一 Gateway。
- 钉钉锁定 `dingtalk-stream`，Stream 回调只做 ACK、映射和投递；OpenAPI 上传/发送封装在适配器中。
- 个人微信不引入非官方注入框架，直接实现腾讯 `openclaw-weixin` iLink 所需的二维码、长轮询、`context_token`、CDN AES-128-ECB 和文件收发。

## 来源与许可证

- CowAgent `ed5bb344cfe42cee443c8266ba47ee666d8d7471`（MIT）：仅参考/裁剪平台事件与媒体协议实现。
- dsh-wecom（MIT）：仅参考 FIFO、文件路径安全和状态指标。
- Tencent `openclaw-weixin`（MIT）：个人微信 iLink 的协议权威来源。
- LangBot（Apache-2.0）：保留 D-188 的适配层形态参考。
- 不复制 AstrBot（AGPL）或 WeChatFerry。

## 验收与回退

自动验收包含四平台 Fake Transport 契约、附件安全、重复投递、同会话顺序、跨会话并行、超时续跑、配置兼容和冻结导入 smoke。真实手机验收需要用户的平台租户/账号，在自动验收通过后逐个平台灰度执行。

每个平台有独立 enable/profile；关闭或删除单个平台凭据不得影响 GUI、其他 Channel 或既有 Slack/Telegram。旧 `wecom:default` 无迁移即可继续读取。
