# ChemClaw 思考结束收起连续可见（D-183）

**状态：实施完成**

## 边界

1. `firstTokenWaitCopy`：规划等待覆盖 settled thinking-only（live 已清、尚无 tool/非空回答）。
2. `Transcript` TurnGroup：上方渲染汇出的 settled `ThinkingBlock`（默认收起）。
3. `App`：沿用 `isPlanningWaitWindow`；live D-178 `forceOpen` 不变。

## 验收

- 定向 Vitest：`firstTokenWaitCopy` + `FirstTokenWaitLabel` + `ThinkingBlock` + `Transcript`：**61 passed**。
- 首轮思考结束收起且有规划文案；步骤出现后仍可展开思考过程。
