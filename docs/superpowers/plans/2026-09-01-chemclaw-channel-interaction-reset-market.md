# D-196/D-197 实施计划：Channel 交互闭环、会话重置与行情执行放行

规格：[`../specs/2026-09-01-chemclaw-channel-interaction-reset-market-design.md`](../specs/2026-09-01-chemclaw-channel-interaction-reset-market-design.md)

## D-197

- [x] 动态 MCP 价格语义不再把单独 `market` 当作价格信号。
- [x] 按用户实施中反馈，Engine 取消行情 market-scope/market Scenario 执行硬拒绝，保留意图与投影引导。
- [x] 完成 Engine、Planner、MCP 与 durable resume 回归。

## D-196

- [x] Channel ask_user target 绑定、文字渲染、自然回复、`/answer`、多选和分组推进。
- [x] 安全审批桌面提示；控制命令优先。
- [x] 快速入队、每 session FIFO、人工等待 timeout 豁免。
- [x] 四平台 `/new`/`/reset`、订阅群保护、旧会话保留、旧 stream/终态抑制。
- [x] 个人微信 default account 授权、SecretStore 热刷新和无敏感 poll 诊断。
- [x] 完成单元/集成/回归测试：可写 basetemp 下 166 passed, 1 skipped；Python compileall 通过。
- [x] 从当前 worktree 重启开发 sidecar 与 Vite；health=ok，企微与个人微信均 connected/authenticated、queue=0、无 runtime error。
- [ ] 由真实企微账号发送选项/`/new`/现货查价消息，并在个人微信重新扫码后发送首条入站；未触发前不标记真机 PASS。
- [x] 更新 DECISIONS、DOMAIN、README 与 AGENTS 门禁。
