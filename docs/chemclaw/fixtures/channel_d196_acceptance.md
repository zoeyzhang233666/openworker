# D-196/D-197/D-198 Channel 真机验收记录

- 日期：2026-09-01
- 代码自动验证：D-198 单文件 31 passed；D-193/D-195/D-197 组合 170 passed, 1 skipped；桌面 WS/Inbox/ask_user 补充 34 passed, 1 deselected（可写 basetemp）；Python compileall 通过。
- 安装包：未构建。
- `main`：未合并。
- 开发 sidecar：D-198 完成后已于 2026-09-01 从当前 worktree 隐藏重启；`/v1/health=ok`，8765 正常监听，Vite 1420 返回 HTTP 200。
- Channel 启动摘要：企微与个人微信均为 `connected/authenticated`、queue=0、无 runtime error；个人微信 `streaming=true`、`streaming_mode=incremental_messages`、最近 poll messages=0，须用户从真实微信发消息后完成入站验收。

## 重启后真机清单

| 项目 | 操作 | 期望 | 实际结果 |
|---|---|---|---|
| 企微选项 | 发送“甲醇多少钱”，桌面卡片出现后在企微回复 `1` | 企微必达完整现货/期货选项；同一轮继续回答 | 用户于 D-196 后真机复现 FAIL：只有“正在处理”无选项；D-198 已定位桌面闭包覆盖并自动回归，待重启复验 |
| 个人微信选项 | 发送“甲醇多少钱”，桌面卡片出现后在微信回复 `1` | 微信必达完整编号选项；同一轮继续回答 | D-198 自动回归通过；待真实个人微信复验 |
| 个人微信增量流 | 发送一个需要较长回答的问题 | 先见一次处理提示，再见有序正文段；终态不整篇重复 | D-198 自动回归通过；待真实 iLink 复验 |
| 自然语言新会话 | 分别发送“开新的对话”“新的对话”，再问新问题 | 与 `/new` 相同确认并切到无历史新会话 | 四平台自动回归通过；待真实账号复验 |
| 企微新会话 | 发送 `/new`，再问新问题 | 立即确认；桌面端出现新会话，旧会话仍可查看 | 用户截图已确认 `/new` 成功 |
| 个人微信入站 | 直接发“你好”；若手机端提示失效再重新扫码 | 首条消息无需重启 Gateway 即进入 ChemClaw，并使用该入站 `context_token` 回复 | 当前 connected/authenticated，poll messages=0；待用户发送真实入站 |
| 现货 + 新闻 | 问“甲醇现货价格及相关新闻” | 现货价和新闻 MCP 均不再出现 `market-scope denied` | 待真实 MCP/Channel 触发 |

> 若个人微信状态显示长轮询持续成功但返回消息数始终为 0，记录为腾讯 iLink 未投递，不冒充本地真机通过。
