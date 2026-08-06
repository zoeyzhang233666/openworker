# ChemClaw Mermaid 渲染失败补救设计（A3 + B′）

- 日期：2026-08-06
- 状态：用户批准按计划执行（Cursor plan：Mermaid repair fallback）
- 关联决策：D-028、D-029、D-063、**D-074**
- 关联规格：`docs/superpowers/specs/2026-08-03-chemclaw-mermaid-rendering-design.md`
- Worktree：`chemclaw-clean`

## 1. 背景与目标

当前 fenced `mermaid` 在 `mermaid.render` 失败时只显示「无法渲染此图表」+ 源码（D-029 失败降级），没有补救。用户需要：

1. 回答结束后，**仅对渲染失败的块**自动就地修一次（B′），并显示「正在修正图表…」。
2. 自动仍失败时保留「修复图表」按钮（A3 手动触发同一窄通道）。
3. **已成功渲染的图不得**发起修图或无故重绘。

## 2. 已确认产品选择

| 项 | 选择 |
| --- | --- |
| 形态 | A3 就地替换 + B′ 自动试 1 次 |
| 进度 | 必须显示「正在修正图表…」（不完全静默） |
| 触发 | 仅语法/解析失败；成功 SVG / 超长 / 库加载失败不进模型修图 |
| 历史 | 不代发可见用户消息 |
| 落盘 | 替换助手消息内对应 fence 并 persist |
| 产物 MD 预览 | 本期仅做错误降级；无 session 消息定位时不自动/手动修图（避免写文件副作用） |

## 3. 架构

```text
MermaidBlock: mermaid.render
  ├─ OK → SVG（停止）
  ├─ tooLong / loadFailed → 降级（库失败可前端重试加载）
  └─ syntax fail
        → 显示「正在修正…」
        → POST /v1/sessions/{id}/mermaid-repair
        → 无工具 LLM 只返回 mermaid fence
        → 就地替换 content 中该 fence → persist → WS message_updated
        → 再 render；仍失败 → 报错 + 源码 +「修复图表」
```

### 3.1 后端窄通道

- `POST /v1/sessions/{session_id}/mermaid-repair`
- Body：`message_ts`（助手消息 `ts`）、`source`（失败块原文）、`error`（短错误字符串）、可选 `block_index`
- 用该会话当前模型调用 `provider.complete(..., tools=None)`；system 要求只输出一个可渲染的 mermaid fence，保留原意图、不改正文旁白
- 从响应解析首个 ```mermaid 块；在对应助手 `content` 中精确替换匹配的 fence；`persist_session`；`broadcast_session` 类型 `message_updated`（含更新后的 message）
- 同会话正在普通 turn：允许并行轻量补丁（不占 `_running_sessions`）；若找不到消息/源码不匹配 → 404/409 + 中文错误

### 3.2 前端

- `Markdown` / `MermaidBlock` 可选传入 `repairContext: { sessionId, messageTs }`
- `Transcript` 对已完成助手消息传入 context；流式 `renderMermaid={false}` 不变
- 失败分类：`syntax` | `tooLong` | `loadFailed`
- `syntax` + 有 repairContext：自动修每块最多 1 次（按 `messageTs + source` 键）；手动按钮另计，合计手动最多 2 次
- 修图中禁用导出/全屏；源码仍可见；进度在错误区

## 4. 明确不做

- 生成前服务端预渲染整份回答
- 自动修成功图 / 超长 / 库加载失败
- 静默无进度提示
- A1 代发用户气泡
- 本期写回 artifact 文件

## 5. 验收

1. 坏语法 → 「正在修正…」→ 多数出图；刷新后仍好图
2. 合法图 → 无修图请求
3. 自动仍失败 → 降级 +「修复图表」
4. 库加载失败 → 不调修图 API
5. i18n 中英齐全；pytest + npm 覆盖替换与触发闸门

## 6. 决策对齐

- **D-074**：语法渲染失败可自动就地修 1 次并显示进度；失败保留手动修复；成功图不重绘
- **D-029**：失败降级保留；本设计在其上增加补救闭环
- **D-063**：渲染层仍不编造边标签；修图由模型重写源码
