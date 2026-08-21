# ChemClaw 步骤卡下方 live 思考强制展开

**日期**：2026-08-21  
**状态**：已落地（D-178）  
**范围**：对话 GUI live ThinkingBlock 在步骤卡出现后的展开策略；贴底跟滚沿用 D-176；不改后端、Router、TurnGroup 生命周期。

## 背景

D-176 仅在首包窗口（尚无工具/回答）对 live「正在思考」使用 `forceOpen`。多轮工具之间 `assistant_message` 清空 `reasoningStream` 会卸掉 ThinkingBlock；下一轮 `reasoning_delta` 重新挂载时 `isFirstTokenThinkingOpen` 已为 false，初始收起，出现「正在运行 x 个步骤」展开、下方「正在思考…」收起，且收起时正文无法贴底跟滚。

## 目标

1. 只要 live ThinkingBlock 按现有条件挂载（`running && reasoningStream && !streaming`），一律强制展开正文。
2. 正文仍按 D-176 贴底跟滚（框内上翻暂停）。
3. TurnGroup「正在运行 x 个步骤」可同时保持展开；不做互斥折叠。

## 产品行为

- live 挂载即 `defaultOpen` + `forceOpen` 为 true，不再依赖 `isFirstTokenThinkingOpen`。
- `isPlanningWaitWindow` / 规划间隙提示仍仅首包前；步骤出现后提示继续消失。
- settled「思考过程」默认仍收起。

## 非目标

- 不改 TurnGroup 自动开合、settled ThinkingBlock、后端 reasoning、规划文案池文案本身。
- 不伪造 upstream reasoning。

## 验收

- 有工具步骤后再次出现 live 思考：正文自动展开并随增量贴底。
- 步骤卡可与思考框同时展开。
- 定向 Vitest（ThinkingBlock 相关）通过。
