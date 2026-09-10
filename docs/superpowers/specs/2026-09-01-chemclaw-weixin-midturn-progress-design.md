# D-200：个人微信中途过程流设计

- 日期：2026-09-01
- 状态：用户已批准实施并授权实施
- 前置：D-195、D-198、D-199

## 问题

个人微信在长工具轮次中，用户往往只看到一条「ChemClaw 正在处理…」，直到终态才出现正文。企微同轮会通过 `tool_started` 原位刷新「正在调用 {tool}…」，并持续刷新草稿。微信侧虽已有 D-198 分段正文，但：

1. `tool_started` 仅绑定 `wecom_stream`，微信不发过程提示；
2. 分段门槛 `WEIXIN_STREAM_MIN_CHARS=240` 偏高，短答/早期草稿长时间静默。

官方 iLink 没有企微 `reply_stream` 单气泡原位刷新；不得伪造该能力。

## 设计

### 多气泡过程流（`incremental_messages`）

1. 开轮仍发一次 `kind=progress`：「ChemClaw 正在处理…」。
2. 无助手正文草稿时，`tool_started` 另发短过程气泡：「ChemClaw 正在调用 {tool}…」。
3. 过程气泡独立节流（≥2.0s，同文案不重复），避免工具连发刷屏。
4. 正文仍走 `stream_chunk` 有序后缀；`WEIXIN_STREAM_MIN_CHARS` 降至约 80；保留硬上限与标点边界。
5. 终态逻辑不变：只补未发送尾段；有 chart/mermaid 时仍走 D-199 rich 交付。
6. `error` 且尚未终态投递时，发一条中文错误气泡。
7. 不向微信推送 reasoning/思考全文。

### 能力声明

- `streaming=true`，诊断仍为 `streaming_mode=incremental_messages`。
- 不实现、不宣称微信侧 `update_stream`。

## 验收

- 工具型长轮次在最终回答前至少出现一次「正在调用 …」。
- 连续快速多次 `tool_started` 不在节流窗口内刷多条。
- 长正文仍有序分段；终态不重复已发前缀。
- 既有 D-198 长答分段、D-199 rich 终态回归通过。
- 真机须重启 sidecar 后复验。

## 非目标

- 不发明 iLink 原位编辑 API。
- 不改飞书/钉钉/GUI。
- 不做工具名中文映射表。
- 不把企微 COS 精装过程刷新搬进微信过程气泡。
