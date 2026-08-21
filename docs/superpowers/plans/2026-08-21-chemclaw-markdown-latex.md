# ChemClaw Markdown LaTeX 公式渲染（D-185）

**状态：实施完成**

## 边界

1. 共享 `surfaces/gui/src/components/Markdown.tsx`：`remarkGfm` + `remarkMath` + `rehypeKatex`。
2. 直依赖 `remark-math`、`rehype-katex`、`katex`；导入 `katex/dist/katex.min.css`。
3. `.md .katex-display` 横向滚动，避免宽公式撑破气泡/预览。
4. 不改后端、prompt、HTML 网页版、ThinkingBlock。

## 验收

- 定向 Vitest：`src/components/Markdown.test.tsx`：**19 passed**。
- 对话与 MD 产物预览公式均排版（同一组件保证）。
