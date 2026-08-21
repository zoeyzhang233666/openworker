# ChemClaw 思考框贴底滚动 + 规划间隙提示（D-176）

**状态：实施完成**

## 边界

1. `ThinkingBlock`：`forceOpen` + `.thinking-body` 贴底滚动（尊重框内上翻）。
2. `firstTokenWaitCopy`：`planning` 池 + `isPlanningWaitWindow`；App 接线 live Thinking + 规划提示。
3. 主 transcript follow 依赖含 `reasoningStream`。
4. 不改 TurnGroup / settled 思考默认收起 / 后端。

## 验收

- 定向：`ThinkingBlock` / `firstTokenWaitCopy` / `FirstTokenWaitLabel` / i18n / localization-audit：**41 passed**。
- 空白期强制展开 + 规划提示；有工具或回答流后提示消失。
