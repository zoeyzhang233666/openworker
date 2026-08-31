# ChemClaw 多平台 Channel 与文件传输实施计划（D-193）

规格：[2026-08-31-chemclaw-multichannel-file-transfer-design.md](../specs/2026-08-31-chemclaw-multichannel-file-transfer-design.md)

状态：**已实现（自动验收）**；真机租户验收仍为人工门禁。

## Task 1：统一合同与媒体安全

- 深化 `coworker/channels/` 的 Envelope、Capabilities、Status 与 Adapter 接口。
- 让附件进入 `MessageEvent`，落地安全下载、路径校验、MIME/扩展名/大小限制与 TTL 清理。
- 保留 D-188 的类型名和 `wecom:default` 兼容。
- 验收：合同序列化、附件不丢失、路径穿越/符号链接/超限测试通过。

## Task 2：Channel FIFO 与状态

- 在 `SessionManager` 建立按路由键的 FIFO worker 和全局并发上限。
- 普通 Channel 消息排队；明确 steering 命令才进入当前轮次。
- 增加消息去重、轮次超时、队列长度及无正文状态指标。
- 验收：同会话 5 条严格有序、10 会话并发互不串线、超时后队列继续。

## Task 3：企业微信补强

- SDK 精确锁定 1.0.8；用统一媒体管理器处理真实脱敏文本/图片/文件/混合帧。
- 补齐图片/文件上传、主动发送、中文文件名和可操作错误。
- 验收：DM、群 @、未 @、去重、双向文件 Fake Transport 契约通过。

## Task 4：飞书与钉钉

- 增加 descriptor/profile/config/adapter/mapping/sender；SDK lazy import。
- 飞书专用线程事件循环；钉钉 Stream 回调和 OpenAPI 媒体上传。
- 验收：DM、群 @、附件、断线/认证/限流 Fake Transport 契约通过。

## Task 5：官方个人微信 iLink

- 增加 QR 登录状态、凭据持久化/过期提示、长轮询、context token 和 CDN AES 文件处理。
- capability 固定 `group_chat=false`；不加载非官方微信注入库。
- 验收：扫码状态机、DM 路由、context token、加解密、双向文件契约通过。

## Task 6：平台无关外发与 UI 能力事实

- `send_message`/`send_file` 支持当前 Channel 默认目标和显式目标；文件保持独立审批。
- 连接列表输出 capabilities/status，UI 只展示适配器声明的真实能力。
- 更新 packaging、许可证和中文连接说明；所有 SDK 使用精确版本并进入 lock。

## Task 7：回归与灰度门禁

- 运行四平台定向测试、connector/session/send_file 回归、GUI 类型检查和冻结导入 smoke。
- 更新 `README.md`、`DECISIONS.md`、`DOMAIN.md` 与实际测试结果。
- 不在本任务构建正式安装程序；真实手机验收和正式安装包仍需用户明确操作/确认。
