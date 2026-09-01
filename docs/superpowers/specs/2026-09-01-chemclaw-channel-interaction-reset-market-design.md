# D-196/D-197：Channel 交互闭环、会话重置与行情执行放行设计

- 日期：2026-09-01
- 状态：用户已批准实施；D-197 在实施中按用户反馈修订为取消行情执行硬守卫

## 问题

1. Channel 后台轮次调用 `ask_user` 后，问题可能只留在电脑端 Inbox，消息端看不到或无法作答。
2. 普通 Channel FIFO 会把回答排在正在等待该回答的轮次之后，并受 300 秒普通轮次超时影响。
3. 官方个人微信扫码后账号级 allowlist 已写入 SecretStore，但 Gateway 仍使用扫码前缓存；`default` 账号还会绕过账号级授权。
4. Channel 没有清空上下文的会话命令。
5. 行情执行硬守卫会因旧 scope、durable resume 或动态 MCP 名称拒绝正确的现货调用。

## 设计

### Channel 问答

- `ask_user` Inbox item 在创建时记录精确 Channel target；同一个 Inbox item 仍是唯一状态源。
- 四个平台以纯文字显示完整问题、编号、说明、推荐和答题命令；回复先于普通路由被解析。
- 支持序号、标签、`/answer`、逗号多选；分组问题逐题推进，最终以 JSON answers 一次释放 Agent。
- 只接受同一 target 的已授权入站；冲突或无效答案不创建新 turn。
- approval/directory/plan 仅通知电脑端审批，不从普通 Channel 放权。

### 调度与重置

- 平台回调只负责快速入队；Coordinator 保持每 session FIFO。
- Inbox 有待处理项时延长普通轮次 deadline，不取消正在等待用户的 Agent。
- `/new` 与 `/reset` 建立新的持久 session 并切换 MentionSessionStore target 所有权；旧 session 保留。
- 自动管理群仅在 @ChemClaw 后重置；显式订阅桌面对话的群拒绝重置。
- 切换后撤销旧 target 文本 grant、interrupt 旧轮次、关闭旧 pending item；D-195 stream 和自动终态发送前校验 target 当前所有者。

### 个人微信

- 只要 `settings.accounts` 存在，`default` 也按 `accounts["default"]` 授权。
- 第一次授权失败的微信入站即时从 SecretStore 重载微信 settings 并重试。
- context token 继续在入队前持久化。
- 状态只增加最近 poll 时间、poll 消息数、最近有效入站时间，不记录消息正文和凭据。

### 行情策略（D-197 修订）

- 市场意图、工具投影和 prompt 仍用于优先选择现货/期货的正确来源。
- 执行阶段不再应用 `market-scope denied`；市场 turn 的 Scenario allowlist 也不作为第二层行情硬拒绝。
- PermissionEngine、工具自身校验与通用安全审批仍是最终权限边界。
- `MarketToolSelection.guard_tool` 只保留为兼容诊断接口；实际 Engine 不调用它拦截。

## 验收

- 四平台问答、分组、无效输入、跨会话拒绝、FIFO、人等超时、重置和旧回复抑制测试通过。
- 个人微信默认账号热授权与无敏感诊断通过。
- 现货 MCP、新闻 MCP 及 durable resume 不再产生 market-scope denied；非市场 Scenario guard 回归不变。
- D-192/D-193/D-195 定向回归通过；真机结果与外部 iLink 未投递明确区分。

