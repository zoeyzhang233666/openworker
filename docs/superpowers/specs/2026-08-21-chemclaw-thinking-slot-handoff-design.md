# ChemClaw 思考同槽位交接防空白（D-186）

**日期**：2026-08-21  
**状态**：已落地（D-186）  
**范围**：对话 GUI live→settled 思考槽位连续性；不改后端、streamGate 词阈、D-178 纯 live forceOpen、TurnGroup 开合。

> 计划稿曾标 D-184；仓库 D-184 已用于研究委派强制，本刀决策号为 **D-186**。

## 背景

D-183 保证 settled thinking-only 后仍有「思考过程」+ planning，以及 Turn 上方保留 reasoning。但仍有空白：

1. live 挂载条件含 `!streaming`，早期 `assistant_delta` 使 live 整块卸载，而 `streamMode === "hold"` 不画正文 → 真空白。
2. `assistant_message` 清空 `reasoningStream` 时高度从 forceOpen 正文断崖到一行淡标题；`tool_proposed` 更晚才出步骤卡。

## 目标

1. 有展示用 reasoning 时，**即使 streaming 非空**也不卸思考 chrome（hold 间隙标题仍在）。
2. `assistant_message` 后同槽位切到 settled 收起（`live=false`、无 `forceOpen`、默认收起），展示文本保留直到 Turn 已挂 reasoning。
3. 与 Turn 内 ThinkingBlock 去重：Turn 已展示同一 reasoning 时卸掉 App 外挂槽；running 期间 Transcript 不重复画 thinking-only。
4. 纯 live、无 streaming 时仍 D-178 forceOpen。

## 非目标

- 不改 streamGate 40 词晋升；不伪造 tool stub；不把 planning 挂到步骤出现之后。

## 验收

- `reasoning_delta` → 短 `assistant_delta`：ThinkingBlock 仍在。
- `assistant_message` thinking-only：收起「思考过程」连续可见。
- `tool_proposed` 后 Turn 上方可展开思考，外挂不双份。
- 定向 Vitest 通过。
