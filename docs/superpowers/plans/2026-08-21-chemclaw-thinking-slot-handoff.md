# ChemClaw 思考同槽位交接防空白（D-186）

**状态：实施完成**

> 计划稿曾标 D-184；与研究委派 D-184 冲突后改号为 **D-186**。

## 边界

1. `thinkingSlot.ts`：`thinkingSlotView` 覆盖 live forceOpen、assistant_delta hold 收起、settled 收起；Turn 已挂 reasoning 时返回 null。
2. `App.tsx`：用 `thinkingSlot` 替代 `reasoningStream && !streaming` 挂载条件。
3. `Transcript.tsx`：running 期间 thinking-only 不在 Transcript 内再画一份（由 App 槽位承接）。

## 验收

- 定向 Vitest：`thinkingSlot` + `firstTokenWaitCopy` + `FirstTokenWaitLabel` + `ThinkingBlock` + `Transcript`：**67 passed**。
