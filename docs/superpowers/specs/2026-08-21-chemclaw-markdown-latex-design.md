# ChemClaw Markdown LaTeX 公式渲染（D-185）

**日期**：2026-08-21  
**状态**：已落地（D-185）  
**范围**：GUI 共享 Markdown 渲染器对 `$…$` / `$$…$$` 的 KaTeX 排版；对话最终回答与 RightRail `.md` 产物预览共用同一路径。

## 背景

助手与研究报告大量使用行内 `$…$` 与块级 `$$…$$`。当前 [`Markdown.tsx`](../../../surfaces/gui/src/components/Markdown.tsx) 仅配置 `remark-gfm`，无 `remark-math` / KaTeX，公式以 raw 源码显示。对话与 MD 产物预览共用该组件，故两处同时失败。

## 目标

1. 行内与块级 LaTeX 在对话气泡与 MD 产物预览中正确排版。
2. 一次改动覆盖两处；不新增第二套渲染器。
3. 坏公式不炸整段（`throwOnError: false`）。
4. 不成对 `$100` 等货币文本保持普通文本。

## 产品行为

- 语法：`$inline$`、`$$display$$`（与常见 LLM 输出一致）。
- 引擎：`remark-math` + `rehype-katex` + 直依赖 `katex` CSS。
- 流式：不新增 `renderMath` 开关；未闭合定界符通常不进 math AST。
- Mermaid / ```chart` / artifact 芯片行为不变。

## 非目标

- MathJax；`\[…\]` / `\(…\)` 专用路径。
- 改 Agent prompt / Skill 强制公式语法。
- HTML「做网页版」iframe 注入 KaTeX。
- 用户纯文本气泡、ThinkingBlock 原文。

## 验收

- 行内/块级样例出现 `.katex` / `.katex-display`。
- 截图类 `\Delta t` / `\dfrac` 冒烟通过。
- 不成对 `$100` 无 `.katex`。
- `Markdown.test.tsx` 既有 artifact/mermaid/chart + 新 math 用例全绿。
