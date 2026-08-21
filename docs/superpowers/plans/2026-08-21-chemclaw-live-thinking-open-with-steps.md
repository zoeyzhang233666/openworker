# ChemClaw 步骤卡下方 live 思考强制展开（D-178）

**状态：实施完成**

## 边界

1. `App.tsx`：live ThinkingBlock `defaultOpen`/`forceOpen` 恒 true（挂载即强制展开）。
2. 贴底逻辑继续用 D-176 `ThinkingBlock` 正文 stick-scroll。
3. 不改 TurnGroup / planning wait 谓词 / settled 默认收起。

## 验收

- 定向：`ThinkingBlock.test.tsx` + `firstTokenWaitCopy.test.ts`：**16 passed**。
- live 挂载（含步骤后 remount）强制展开 + 贴底；规划提示仍仅首包前。
