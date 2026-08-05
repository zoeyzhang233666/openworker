# ChemClaw Mermaid 悬停 Chrome 设计

**状态**：书面规格已于 2026-08-03 获得用户批准（方案 B + 纯 CSS）。

## 目标

内联 Mermaid 图默认与对话/报告正文融为一体；仅当用户鼠标悬停或键盘/触控聚焦块内时，才显示边框与工具栏。

## 行为

| 状态 | 边框 / 背景 | 工具栏 |
|------|-------------|--------|
| 默认 | 透明边框、透明背景 | `visibility: hidden`（保留占位高度，防抖动） |
| `:hover` 或 `:focus-within` | `--line` 边框、`--paper` 背景 | 可见 |
| 错误（`is-error`） | 同上，始终显示 | 可见；错误文案与源码始终露出 |

触控：点按图或工具栏按钮进入 `focus-within`，无需单独 JS hover 状态。

## 非目标

- 不改全屏 lightbox、neo 主题、导出、流式不出图、`minHeight` 锁定。
- 不用 JS 维护 hover state。
- 不用 `display: none` 或绝对定位叠图（会取消占位或悬停时高度突变）。

## 实现缝

- CSS：`.mermaid-block` / `.mermaid-block-toolbar` 默认关闭 chrome；`:hover`、`:focus-within`、`.is-error` 打开。
- TSX：`error` 或 `exportError` 时根节点加 `is-error`。
