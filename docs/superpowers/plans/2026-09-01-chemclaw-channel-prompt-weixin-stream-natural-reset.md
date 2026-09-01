# D-198 实施计划：Channel 选项必达、个人微信增量流与自然语言新对话

规格：[`../specs/2026-09-01-chemclaw-channel-prompt-weixin-stream-natural-reset-design.md`](../specs/2026-09-01-chemclaw-channel-prompt-weixin-stream-natural-reset-design.md)

- [x] 统一桌面/Channel `ask_user` 创建与通知入口，修复共享引擎被桌面闭包覆盖的问题。
- [x] 检查 Channel prompt 的真实发送结果并做 pending 期间有限重试。
- [x] 实现个人微信处理提示、长回答分段增量和终态去重，并暴露准确诊断模式。
- [x] 增加严格自然语言新对话命令，复用 D-196 重置合同并保证控制命令优先。
- [x] 增加桌面+Channel 同时可见、发送重试、微信增量、自然语言重置与误触回归。
- [x] 运行 D-196/D-197、D-193、D-195 相关测试和 compileall。
- [x] 更新 README、DECISIONS、DOMAIN、AGENTS 与真机清单。
- [x] 从当前 worktree 重启开发 sidecar/Vite 并记录真实状态；不构建安装包、不合并 `main`。
