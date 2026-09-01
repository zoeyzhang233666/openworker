# D-199：Channel 图表网页交付设计

## 问题

ChemClaw 桌面端会把 fenced `chart` ChartSpec 渲染成交互图表，但企业微信、个人微信、
飞书、钉钉、Telegram、Slack 等普通消息客户端只会显示文本。当前 Channel 流式与
`send_message` 路径可能把完整 ChartSpec JSON 原样发出，既不可读，也可能包含数百个数据点。

## 决策

- `chart`、`mermaid`、`mmd` 围栏是“仅供渲染的结构化块”，不得进入任何普通 Channel
  聊天气泡；桌面端消息与图表渲染保持不变。
- 增量流只发送围栏之前和完整围栏之后的可读正文。围栏尚未闭合时停在开围栏前，
  不把半段 JSON 推到企微或个人微信。
- 最终回复包含结构化块时，用现有 `report_html` cook 把完整回复生成单文件 HTML：
  云文件存储可用时优先发公开链接；否则在支持原生文件的 Channel 中发送 HTML 附件。
- Telegram 等无原生文件路径的平台在未配置云文件存储时，只发送清理后的文字并明确提示
  网页交付失败；绝不以原始 JSON 作为降级结果。
- 自动终态与模型显式 `send_message` 共用同一清理/网页生成规则，防止旁路泄漏。
- 普通代码围栏（如 Python、JSON 示例）不是渲染块，继续原样发送。

## 验收

1. 企微流式快照、个人微信分段流和四平台自动终态均不含 `````chart`` 或 ChartSpec 数组。
2. 完整 `chart` 回复生成可渲染图表的 HTML，并通过链接或 `.html` 附件交付。
3. Telegram/Slack 等显式 `send_message` 不发送原始结构化块；有 COS 时发送 HTML 链接。
4. HTML/附件发送失败时仍返回可读正文和中文降级提示。
5. 桌面端保存的 assistant message 不被改写，现有 D-195/D-198 行为回归通过。
