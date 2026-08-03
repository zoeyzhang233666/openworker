# ChemClaw Mermaid 渲染 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 在对话最终回答与右侧 Markdown 报告预览中真实渲染 fenced `mermaid` 图，支持图/源码切换、遮罩全屏与 SVG/PNG 导出，且滚轮浏览时不抖动。

**Architecture:** 在现有 `Markdown`（react-markdown + remark-gfm）缝合点拦截 `language-mermaid`，交给懒加载的 `MermaidBlock`；流式 `streamingText` 传 `renderMermaid={false}` 只显示源码。导出与 Lightbox 为独立单元，不改 `coworker/` 后端。

**Tech Stack:** React 18、TypeScript、Vite、Vitest、Testing Library、`mermaid@11.16.0`、现有 i18n。

**Plan status:** 已实现（Tasks 1–5 代码与文档完成；手工 UI 验收清单待用户勾选）。

**Spec:** `docs/superpowers/specs/2026-08-03-chemclaw-mermaid-rendering-design.md`（已批准）

## Global Constraints

- 只在 `D:\OpenWorker\openworker\.worktrees\chemclaw-clean` / 分支 `design/chemclaw-upstream` 工作。
- 钉扎依赖：`mermaid@11.16.0`；动态 `import()`，不打进首屏主包。
- `securityLevel: "strict"`；`startOnLoad: false`；`maxTextSize: 50_000`；`suppressErrorRendering: true`；`theme: "neutral"`。
- 流式零渲染：`Transcript` 的 `streamingText` 必须 `renderMermaid={false}`。
- 防抖硬约束：单次稳定渲染、占位锁高（`min-height: 180px`）、不用 IntersectionObserver/scroll 触发渲染、Lightbox 用 fixed portal。
- 全屏是遮罩 lightbox，不是浏览器 Fullscreen API。
- 默认简体中文；控件文案走 `i18n.tsx`。
- 正常界面只显示 ChemClaw；不改后端 turn/MCP/审批。
- 每个任务独立 TDD、验证、提交；失败则停并用 systematic-debugging。
- 不合并 `main`，不构建安装程序。

## File Structure

| 文件 | 职责 |
| --- | --- |
| `surfaces/gui/src/mermaidExports.ts` | SVG/PNG 下载纯函数、文件名、画布上限 |
| `surfaces/gui/src/mermaidExports.test.ts` | 导出助手单测 |
| `surfaces/gui/src/components/MermaidBlock.tsx` | 渲染、图/源码、工具栏、错误降级、高度锁 |
| `surfaces/gui/src/components/MermaidBlock.test.tsx` | Block 行为单测（mock mermaid） |
| `surfaces/gui/src/components/MermaidLightbox.tsx` | 遮罩全屏、缩放平移 |
| `surfaces/gui/src/components/Markdown.tsx` | `renderMermaid` 开关 + `pre` 缝合 |
| `surfaces/gui/src/components/Markdown.test.tsx` | mermaid 缝合与 artifact 回归 |
| `surfaces/gui/src/components/Transcript.tsx` | 流式路径关闭渲染 |
| `surfaces/gui/src/i18n.tsx` | mermaid.* 中英文案 |
| `surfaces/gui/src/styles.css` | `.mermaid-block` / lightbox 样式 |
| `surfaces/gui/package.json` + lockfile | 钉扎 mermaid |
| `docs/chemclaw/README.md` / `TESTING.md` | 状态与测试记录 |

---

### Task 1: 钉扎 mermaid + 导出纯函数

**Files:**
- Create: `surfaces/gui/src/mermaidExports.ts`
- Create: `surfaces/gui/src/mermaidExports.test.ts`
- Modify: `surfaces/gui/package.json`, `surfaces/gui/package-lock.json`

**Interfaces:**
- Consumes: 无
- Produces:
  - `export const MERMAID_MAX_TEXT_SIZE = 50_000`
  - `export const MERMAID_PNG_MAX_EDGE = 8192`
  - `export const MERMAID_PNG_MAX_PIXELS = 16_000_000`
  - `export function mermaidExportFilename(ext: "svg" | "png", at?: Date): string`
  - `export function downloadSvg(svg: string, filename?: string): void`
  - `export async function downloadPng(svg: string, filename?: string): Promise<void>` — 超限抛 `Error`，message 为稳定英文码 `PNG_TOO_LARGE`（UI 层翻译）

- [x] **Step 1: 安装钉扎依赖**

```powershell
Push-Location 'surfaces\gui'
npm.cmd install mermaid@11.16.0 --save
Pop-Location
```

Expected: `package.json` dependencies 含 `"mermaid": "11.16.0"`（或精确锁定该版本）。

- [x] **Step 2: 写失败单测**

Create `surfaces/gui/src/mermaidExports.test.ts`:

```ts
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  mermaidExportFilename,
  downloadSvg,
  downloadPng,
  MERMAID_PNG_MAX_EDGE,
} from "./mermaidExports";

describe("mermaidExports", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "URL",
      {
        createObjectURL: vi.fn(() => "blob:mock"),
        revokeObjectURL: vi.fn(),
      },
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("formats filename chemclaw-diagram-YYYYMMDD-HHmmss.ext", () => {
    const at = new Date(Date.UTC(2026, 7, 3, 5, 6, 7)); // month 0-based → Aug
    expect(mermaidExportFilename("svg", at)).toMatch(
      /^chemclaw-diagram-\d{8}-\d{6}\.svg$/,
    );
    expect(mermaidExportFilename("png", at)).toMatch(/\.png$/);
  });

  it("downloadSvg creates an anchor click with svg mime", () => {
    const click = vi.fn();
    const el = { href: "", download: "", click } as unknown as HTMLAnchorElement;
    vi.spyOn(document, "createElement").mockReturnValue(el);
    downloadSvg("<svg></svg>", "chemclaw-diagram-test.svg");
    expect(el.download).toBe("chemclaw-diagram-test.svg");
    expect(click).toHaveBeenCalled();
  });

  it("downloadPng rejects when edge exceeds limit", async () => {
    // Force measured size above MERMAID_PNG_MAX_EDGE via stubbed Image in implementation test hook,
    // or call an exported measure helper. Prefer: export function assertPngBounds(w, h).
    const { assertPngBounds } = await import("./mermaidExports");
    expect(() => assertPngBounds(MERMAID_PNG_MAX_EDGE + 1, 10)).toThrow(/PNG_TOO_LARGE/);
  });
});
```

Also export:

```ts
export function assertPngBounds(width: number, height: number): void {
  if (
    width > MERMAID_PNG_MAX_EDGE ||
    height > MERMAID_PNG_MAX_EDGE ||
    width * height > MERMAID_PNG_MAX_PIXELS
  ) {
    throw new Error("PNG_TOO_LARGE");
  }
}
```

- [x] **Step 3: 跑测确认失败**

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- --run src/mermaidExports.test.ts
Pop-Location
```

Expected: FAIL（模块不存在）。

- [x] **Step 4: 实现 `mermaidExports.ts`**

```ts
export const MERMAID_MAX_TEXT_SIZE = 50_000;
export const MERMAID_PNG_MAX_EDGE = 8192;
export const MERMAID_PNG_MAX_PIXELS = 16_000_000;

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

export function mermaidExportFilename(ext: "svg" | "png", at: Date = new Date()): string {
  const y = at.getFullYear();
  const mo = pad(at.getMonth() + 1);
  const d = pad(at.getDate());
  const h = pad(at.getHours());
  const mi = pad(at.getMinutes());
  const s = pad(at.getSeconds());
  return `chemclaw-diagram-${y}${mo}${d}-${h}${mi}${s}.${ext}`;
}

export function assertPngBounds(width: number, height: number): void {
  if (
    width > MERMAID_PNG_MAX_EDGE ||
    height > MERMAID_PNG_MAX_EDGE ||
    width * height > MERMAID_PNG_MAX_PIXELS
  ) {
    throw new Error("PNG_TOO_LARGE");
  }
}

export function downloadSvg(svg: string, filename = mermaidExportFilename("svg")): void {
  const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadPng(
  svg: string,
  filename = mermaidExportFilename("png"),
): Promise<void> {
  const svgUrl = URL.createObjectURL(
    new Blob([svg], { type: "image/svg+xml;charset=utf-8" }),
  );
  try {
    const img = await loadImage(svgUrl);
    assertPngBounds(img.naturalWidth || img.width, img.naturalHeight || img.height);
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("PNG_CANVAS_UNAVAILABLE");
    ctx.drawImage(img, 0, 0);
    const pngUrl = canvas.toDataURL("image/png");
    const a = document.createElement("a");
    a.href = pngUrl;
    a.download = filename;
    a.click();
  } finally {
    URL.revokeObjectURL(svgUrl);
  }
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("PNG_IMAGE_LOAD_FAILED"));
    img.src = url;
  });
}
```

- [x] **Step 5: 跑测确认通过**

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- --run src/mermaidExports.test.ts
Pop-Location
```

Expected: PASS

- [x] **Step 6: Commit**

```powershell
git add -- surfaces/gui/package.json surfaces/gui/package-lock.json surfaces/gui/src/mermaidExports.ts surfaces/gui/src/mermaidExports.test.ts
git commit -m "feat: add Mermaid SVG/PNG export helpers"
```

---

### Task 2: `MermaidBlock` 渲染、图/源码、防抖占位

**Files:**
- Create: `surfaces/gui/src/components/MermaidBlock.tsx`
- Create: `surfaces/gui/src/components/MermaidBlock.test.tsx`
- Modify: `surfaces/gui/src/i18n.tsx`（仅本任务需要的 mermaid.* 键）
- Modify: `surfaces/gui/src/styles.css`（`.mermaid-block` 基础样式）

**Interfaces:**
- Consumes: `MERMAID_MAX_TEXT_SIZE`, `downloadSvg`, `downloadPng` from `../mermaidExports`
- Produces:
  - `export function MermaidBlock({ source }: { source: string }): JSX.Element`
  - `data-testid="mermaid-block"` / `mermaid-diagram` / `mermaid-source` / `mermaid-error`
  - Props for later lightbox wiring: 内部 state `lightboxOpen`；Task 3 接入 `MermaidLightbox`
  - 成功后缓存 `svg` 字符串于 state；同一 `source` 不重复 render

- [x] **Step 1: 写失败单测（mock mermaid）**

Create `surfaces/gui/src/components/MermaidBlock.test.tsx`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MermaidBlock } from "./MermaidBlock";

const renderMock = vi.fn(async (_id: string, _src: string) => ({
  svg: '<svg data-testid="fake-svg"></svg>',
}));

vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: (...args: unknown[]) => renderMock(...(args as [string, string])),
  },
}));

afterEach(() => {
  cleanup();
  renderMock.mockClear();
});

describe("MermaidBlock", () => {
  it("renders svg for valid source once", async () => {
    render(<MermaidBlock source={"graph TD; A-->B"} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-diagram")).toBeTruthy());
    expect(renderMock).toHaveBeenCalledTimes(1);
  });

  it("toggles to source and back without re-render", async () => {
    render(<MermaidBlock source={"graph TD; A-->B"} />);
    await waitFor(() => screen.getByTestId("mermaid-diagram"));
    fireEvent.click(screen.getByRole("button", { name: /源码|Source/i }));
    expect(screen.getByTestId("mermaid-source").textContent).toContain("graph TD");
    fireEvent.click(screen.getByRole("button", { name: /图形|Diagram/i }));
    expect(screen.getByTestId("mermaid-diagram")).toBeTruthy();
    expect(renderMock).toHaveBeenCalledTimes(1);
  });

  it("shows error and source on render failure", async () => {
    renderMock.mockRejectedValueOnce(new Error("parse"));
    render(<MermaidBlock source={"not mermaid"} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-error")).toBeTruthy());
    expect(screen.getByTestId("mermaid-source")).toBeTruthy();
  });

  it("rejects oversized source without calling mermaid.render", async () => {
    const huge = "x".repeat(50_001);
    render(<MermaidBlock source={huge} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-error")).toBeTruthy());
    expect(renderMock).not.toHaveBeenCalled();
  });
});
```

- [x] **Step 2: 跑测确认失败**

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- --run src/components/MermaidBlock.test.tsx
Pop-Location
```

Expected: FAIL（组件不存在）。

- [x] **Step 3: 在 `i18n.tsx` 的 `zh-CN` / `en-US` 增加键**

```ts
"mermaid.diagram": "图形",       // en: "Diagram"
"mermaid.source": "源码",        // en: "Source"
"mermaid.fullscreen": "全屏",    // en: "Fullscreen"
"mermaid.exportSvg": "导出 SVG", // en: "Export SVG"
"mermaid.exportPng": "导出 PNG", // en: "Export PNG"
"mermaid.renderError": "无法渲染此图表", // en: "Could not render this diagram"
"mermaid.tooLong": "图表源码过长，无法渲染", // en: "Diagram source is too long to render"
"mermaid.pngTooLarge": "图片尺寸过大，无法导出 PNG", // en: "Image is too large to export as PNG"
"mermaid.exportFailed": "导出失败", // en: "Export failed"
"mermaid.loading": "正在渲染图表…", // en: "Rendering diagram…"
```

- [x] **Step 4: 实现 `MermaidBlock.tsx`（本任务先不做 Lightbox 内容，全屏按钮可先 `setLightboxOpen(true)` 占位空状态，或暂不渲染按钮直到 Task 3——优先：先实现图/源码/导出，全屏按钮在 Task 3 再亮）**

核心要求（必须写入实现）：

1. 模块级 `let mermaidReady: Promise<typeof import("mermaid")> | null`；首次调用时 `import("mermaid")` 并 `initialize({...})`。
2. `useEffect` 依赖 `[source]`；进入时 `renderIdRef.current += 1`，异步结束后若 id 不匹配则丢弃。
3. `source.length > MERMAID_MAX_TEXT_SIZE` → 设错误为 `t("mermaid.tooLong")`，展示源码，不调用 render。
4. 容器：`className="mermaid-block"`，`style={{ minHeight: svg ? undefined : 180 }}`；有 svg 后 `style.height` 设为测得高度（`scrollHeight`/`getBBox` 或包装 div 的 `offsetHeight`），之后保持。
5. 用 `dangerouslySetInnerHTML` **仅**插入 mermaid 返回的 svg 字符串到 `data-testid="mermaid-diagram"` 的 div。
6. 工具栏：图/源码切换；导出 SVG/PNG（调用 Task 1 函数）；导出失败时若 `message === "PNG_TOO_LARGE"` 显示 `t("mermaid.pngTooLarge")`。
7. 本任务可不含 Lightbox；全屏按钮可 `disabled` 或留待 Task 3（若省略按钮，在 Task 3 补上，并补测）。

- [x] **Step 5: 基础 CSS**

```css
.mermaid-block {
  margin: 4px 0 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--paper);
  overflow: hidden;
}
.mermaid-block-toolbar {
  display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  padding: 6px 10px; border-bottom: 1px solid var(--line);
  font-size: 12px;
}
.mermaid-block-diagram {
  overflow-x: auto; padding: 12px; min-height: 180px;
}
.mermaid-block-diagram svg { max-width: 100%; height: auto; display: block; }
.mermaid-block-source {
  margin: 0; padding: 12px 14px; overflow-x: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12.5px; line-height: 1.55; white-space: pre;
}
.mermaid-block-error { color: var(--danger); font-size: 12.5px; padding: 8px 12px; }
```

- [x] **Step 6: 跑测确认通过**

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- --run src/components/MermaidBlock.test.tsx
Pop-Location
```

Expected: PASS

- [x] **Step 7: Commit**

```powershell
git add -- surfaces/gui/src/components/MermaidBlock.tsx surfaces/gui/src/components/MermaidBlock.test.tsx surfaces/gui/src/i18n.tsx surfaces/gui/src/styles.css
git commit -m "feat: render Mermaid diagrams with source toggle"
```

---

### Task 3: `MermaidLightbox` 遮罩全屏

**Files:**
- Create: `surfaces/gui/src/components/MermaidLightbox.tsx`
- Modify: `surfaces/gui/src/components/MermaidBlock.tsx`
- Modify: `surfaces/gui/src/components/MermaidBlock.test.tsx`
- Modify: `surfaces/gui/src/styles.css`

**Interfaces:**
- Consumes: `svg: string`, `onClose: () => void`, optional export handlers
- Produces: `export function MermaidLightbox({ svg, onClose }: { svg: string; onClose: () => void }): JSX.Element`
  - `data-testid="mermaid-lightbox"`
  - portal → `document.body`
  - Esc / 遮罩点击关闭
  - 滚轮缩放、拖拽平移（变换作用在内部 SVG 包装层，不改页面高度）

- [x] **Step 1: 扩展失败单测**

在 `MermaidBlock.test.tsx` 增加：

```ts
it("opens lightbox from fullscreen button", async () => {
  render(<MermaidBlock source={"graph TD; A-->B"} />);
  await waitFor(() => screen.getByTestId("mermaid-diagram"));
  fireEvent.click(screen.getByRole("button", { name: /全屏|Fullscreen/i }));
  expect(screen.getByTestId("mermaid-lightbox")).toBeTruthy();
  fireEvent.keyDown(window, { key: "Escape" });
  await waitFor(() => expect(screen.queryByTestId("mermaid-lightbox")).toBeNull());
});
```

- [x] **Step 2: 跑测确认失败**

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- --run src/components/MermaidBlock.test.tsx
Pop-Location
```

Expected: FAIL（无全屏/lightbox）。

- [x] **Step 3: 实现 `MermaidLightbox.tsx`**

要点：

```tsx
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

export function MermaidLightbox({ svg, onClose }: { svg: string; onClose: () => void }) {
  const [scale, setScale] = useState(1);
  const [tx, setTx] = useState(0);
  const [ty, setTy] = useState(0);
  // on mount: remember body.overflow, set hidden; cleanup restore
  // keydown Escape → onClose
  // backdrop click → onClose; inner stopPropagation
  // wheel preventDefault → setScale clamp 0.4..4
  // pointer drag → setTx/setTy
  return createPortal(
    <div className="mermaid-lightbox" data-testid="mermaid-lightbox" role="dialog" aria-modal="true">
      ...
      <div
        className="mermaid-lightbox-stage"
        style={{ transform: `translate(${tx}px, ${ty}px) scale(${scale})` }}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    </div>,
    document.body,
  );
}
```

- [x] **Step 4: 在 `MermaidBlock` 接入**：有 `svg` 时启用全屏按钮；点击图表区域或全屏打开；渲染 `{lightboxOpen && <MermaidLightbox svg={svg} onClose=... />}`。

- [x] **Step 5: lightbox CSS**（`position: fixed; inset: 0; z-index` 高于侧栏；不改文档流）

- [x] **Step 6: 跑测确认通过**

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- --run src/components/MermaidBlock.test.tsx
Pop-Location
```

Expected: PASS

- [x] **Step 7: Commit**

```powershell
git add -- surfaces/gui/src/components/MermaidLightbox.tsx surfaces/gui/src/components/MermaidBlock.tsx surfaces/gui/src/components/MermaidBlock.test.tsx surfaces/gui/src/styles.css
git commit -m "feat: add Mermaid fullscreen lightbox"
```

---

### Task 4: Markdown 缝合 + Transcript 流式关闭

**Files:**
- Modify: `surfaces/gui/src/components/Markdown.tsx`
- Modify: `surfaces/gui/src/components/Markdown.test.tsx`
- Modify: `surfaces/gui/src/components/Transcript.tsx`

**Interfaces:**
- Consumes: `MermaidBlock`
- Produces: `export function Markdown({ text, renderMermaid = true }: { text: string; renderMermaid?: boolean })`

- [x] **Step 1: 写失败单测**

在 `Markdown.test.tsx` 增加（可复用 Task 2 的 mermaid mock，或在本文件 `vi.mock("mermaid", ...)`）：

```ts
describe("Markdown mermaid fence", () => {
  it("renders MermaidBlock for ```mermaid when enabled", async () => {
    const text = "见下图\n\n```mermaid\ngraph TD; A-->B\n```\n";
    render(<Markdown text={text} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-block")).toBeTruthy());
  });

  it("keeps ordinary code as pre/code", () => {
    render(<Markdown text={"```js\nconsole.log(1)\n```"} />);
    expect(screen.queryByTestId("mermaid-block")).toBeNull();
    expect(document.querySelector("pre code")?.textContent).toContain("console.log");
  });

  it("skips MermaidBlock when renderMermaid is false", () => {
    const text = "```mermaid\ngraph TD; A-->B\n```";
    render(<Markdown text={text} renderMermaid={false} />);
    expect(screen.queryByTestId("mermaid-block")).toBeNull();
    expect(document.querySelector("pre code")?.className || "").toMatch(/language-mermaid/);
  });
});
```

保留既有 artifact 四测不变。

- [x] **Step 2: 跑测确认失败**

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- --run src/components/Markdown.test.tsx
Pop-Location
```

Expected: FAIL（尚无缝合）。

- [x] **Step 3: 实现 Markdown `pre` 覆盖**

```tsx
import { Children, isValidElement, type ReactElement } from "react";
import { MermaidBlock } from "./MermaidBlock";

function mermaidSourceFromPreChildren(children: React.ReactNode): string | null {
  const arr = Children.toArray(children);
  if (arr.length !== 1 || !isValidElement(arr[0])) return null;
  const el = arr[0] as ReactElement<{ className?: string; children?: React.ReactNode }>;
  const cls = el.props.className || "";
  if (!cls.includes("language-mermaid")) return null;
  return String(el.props.children ?? "");
}

export function Markdown({ text, renderMermaid = true }: { text: string; renderMermaid?: boolean }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={(url) => (url.startsWith("artifact:") ? url : defaultUrlTransform(url))}
        components={{
          a: /* existing */,
          pre: ({ children }) => {
            if (renderMermaid) {
              const src = mermaidSourceFromPreChildren(children);
              if (src !== null) return <MermaidBlock source={src} />;
            }
            return <pre>{children}</pre>;
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
```

- [x] **Step 4: Transcript 三处流式/最终区分**

- `TurnGroup` 内 `streamingText`：`<Markdown text={streamingText} renderMermaid={false} />`
- 叙述 `row.text`、助手 `item.text`、plan：保持默认（可渲染）
- 若存在其它 live 流式 Markdown，同样传 `false`

- [x] **Step 5: 跑测确认通过**

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- --run src/components/Markdown.test.tsx src/components/MermaidBlock.test.tsx src/mermaidExports.test.ts
Pop-Location
```

Expected: PASS

- [x] **Step 6: Commit**

```powershell
git add -- surfaces/gui/src/components/Markdown.tsx surfaces/gui/src/components/Markdown.test.tsx surfaces/gui/src/components/Transcript.tsx
git commit -m "feat: wire Mermaid into Markdown; disable during stream"
```

---

### Task 5: 构建、文档与验收记录

**Files:**
- Modify: `docs/chemclaw/README.md`
- Modify: `docs/chemclaw/TESTING.md`
- Modify: `docs/superpowers/specs/2026-08-03-chemclaw-mermaid-rendering-design.md`（状态已批准即可；若实施完成可注「已实现」）
- Modify: `docs/superpowers/plans/2026-08-03-chemclaw-mermaid-rendering.md`（勾选完成的任务）

- [x] **Step 1: 生产构建**

```powershell
Push-Location 'surfaces\gui'
npm.cmd run build
Pop-Location
```

Expected: PASS；产物中存在独立 mermaid chunk（或至少 build 无类型错误）。

- [x] **Step 2: 更新 README / TESTING**

README 业务代码列表增加：

- ✅ 对话与 MD 报告 fenced mermaid 真实渲染（图/源码、遮罩全屏、SVG/PNG；流式不出图；防抖占位）

TESTING 记录本次 `npm test` 相关文件 passed 与 `npm run build` 结果。

- [ ] **Step 3: 手工验收清单（执行者勾选）**

- [ ] 对话完成含 mermaid 的回答 → 出图；流式过程中为代码块
- [ ] 右侧打开 `.md` 报告 → 出图
- [ ] 全屏 / Esc 关闭；滚轮缩放与拖拽可用
- [ ] 导出 SVG、PNG 可下载
- [ ] 长页多图滚轮无明显抖动
- [ ] 坏语法 → 中文错误 + 源码
- [ ] `artifact:` 芯片仍可用

- [x] **Step 4: Commit**

```powershell
git add -- docs/chemclaw/README.md docs/chemclaw/TESTING.md docs/superpowers/plans/2026-08-03-chemclaw-mermaid-rendering.md
git commit -m "docs: record Mermaid rendering completion"
```

---

## Spec coverage self-check

| 规格要求 | 任务 |
| --- | --- |
| D-028 对话+报告渲染 | Task 2–4（RightRail 已用 Markdown，默认开启） |
| 图/源码切换 | Task 2 |
| 安全 strict + 失败降级 | Task 2 |
| SVG/PNG 导出 | Task 1–2 |
| 遮罩全屏+缩放平移 | Task 3 |
| 流式零渲染 | Task 4 |
| 防抖占位/单次渲染 | Task 2 |
| i18n | Task 2 |
| 不改后端 | 全任务 |
| 构建+文档 | Task 5 |

## Placeholder scan

无 TBD/TODO；导出错误码、高度 180、mermaid 11.16.0、文件名格式均已钉死。

## Type consistency

- `Markdown({ text, renderMermaid?: boolean })`
- `MermaidBlock({ source: string })`
- `MermaidLightbox({ svg: string; onClose: () => void })`
- `downloadSvg` / `downloadPng` / `assertPngBounds` / `mermaidExportFilename` 与 Task 1 一致
