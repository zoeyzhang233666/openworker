# ChemClaw Mermaid 渲染设计

- 日期：2026-08-03
- 状态：书面规格已于 2026-08-03 获得用户批准；已实现（2026-08-03）
- 关联决策：D-028、D-029、D-030
- 关联产品规格：`docs/superpowers/specs/2026-07-29-chemclaw-product-design.md` §11
- Worktree：`chemclaw-clean` / 分支 `design/chemclaw-upstream`

## 1. 背景与目标

对话回答和右侧 Markdown 报告预览中，fenced `mermaid` 代码块目前仍显示为普通源码，无法看图。用户需要：

1. 将 `mermaid` 块渲染为真实图表。
2. 提供遮罩层全屏查看（可缩放/平移）以及 SVG/PNG 导出。
3. **硬约束**：加入渲染后，鼠标滚轮浏览页面时不得出现视口/滚动位置抖动。

本设计只覆盖前端 GUI 渲染与导出；不改后端编排；不实现阶段五权威产业链图数据模型。

## 2. 已确认的产品选择

| 项 | 选择 |
| --- | --- |
| 全屏形态 | 遮罩 lightbox（非浏览器 Fullscreen API）+ SVG/PNG 导出（选项 C） |
| 流式时机 | 助手消息结束后再渲染；流式过程中不渲染图（选项 A） |
| 实现路径 | Markdown 缝合 + 独立 `MermaidBlock`（方案 1） |
| 默认视图 | 图形 |
| 语言 | 控件文案走现有 i18n，默认简体中文 |

## 3. 架构与接入点

### 3.1 组件职责

| 单元 | 职责 |
| --- | --- |
| `Markdown` | 现有 GFM 渲染；增加 `renderMermaid?: boolean`（默认 `true`）。在 `pre` 组件中检测 `language-mermaid`，按开关交给 `MermaidBlock` 或保留普通代码块。保留 `artifact:` 芯片行为不变。 |
| `MermaidBlock` | 接收源码字符串；图/源码切换；懒加载 mermaid；安全渲染；错误降级；工具栏（全屏 / 导出 SVG / 导出 PNG）。 |
| `MermaidLightbox` | `createPortal` 到 `document.body`；展示已渲染 SVG；Esc/遮罩/关闭退出；滚轮缩放与拖拽平移；不改变文档流高度。 |
| `mermaidExports.ts` | 纯函数：从 SVG 字符串导出 SVG/PNG 文件下载；文件名与尺寸上限校验。 |

### 3.2 数据流

```text
助手最终气泡 / MD 报告
  → <Markdown />（renderMermaid 默认 true）
  → pre + code.language-mermaid
  → MermaidBlock(source)
  → lazy import('mermaid') → render SVG
  → 工具栏 → Lightbox / download SVG|PNG

流式 streamingText
  → <Markdown renderMermaid={false} />
  → 普通代码块（不出图）
```

### 3.3 调用点

- `Transcript`：流式路径传 `renderMermaid={false}`；已完成助手消息使用默认 `true`。
- `RightRail` Markdown 产物预览：默认开启（静态文件，非流式）。
- 其他已使用 `Markdown` 的表面默认开启，除非后续单测证明需关闭。

### 3.4 依赖与安全

- 依赖：`mermaid@11.16.0`（与既有阶段 1 计划钉扎版本一致），动态 `import()`，不打进首屏主包。
- 初始化一次：

```ts
mermaid.initialize({
  startOnLoad: false,
  securityLevel: "strict",
  maxTextSize: 50_000,
  suppressErrorRendering: true,
  theme: "neutral",
});
```

- 只将 Mermaid 返回的 SVG 字符串插入组件自有容器；不执行图内脚本；不信任图内外链导航。

## 4. 防抖 / 无滚动抖动（硬约束）

### 4.1 必须避免的行为

- 流式过程中反复 `mermaid.render` 导致高度抖动。
- 渲染完成瞬间无占位地插入 SVG，把下方内容顶开且滚动锚点跳动。
- 用 IntersectionObserver / scroll 监听触发渲染或改尺寸。
- 字体或主题二次加载导致同一图二次布局。

### 4.2 强制对策

1. **流式零渲染**：`streamingText` 使用 `renderMermaid={false}`。
2. **单次稳定渲染**：同一 `source` 只成功渲染一次；`source` 未变不重跑；递增 `renderId` 丢弃过期异步结果。
3. **占位锁高**：渲染前固定 `min-height`（约 180px）；成功后将容器高度设为 SVG 实测高度并保持；图/源码切换只改块内部，尽量不改变块外文档流。
4. **滚动路径零副作用**：不在 scroll/IO 上触发 render；Lightbox 使用 `position: fixed` portal；打开时可暂时 `document.body.style.overflow = "hidden"`，关闭后恢复，**不得**改变背后内容高度。
5. **SVG 尺寸约束**：块内 `max-width: 100%`、`height: auto`；超宽图块内横向滚动，不撑破主栏反复回流。
6. **懒加载占位**：库加载中保持与渲染前相同占位高度，避免「先矮后高」。

### 4.3 验收手感

长对话含多张 Mermaid 图时，连续滚轮下滑：主观无周期性上下跳；`scrollTop` 不因非用户操作被代码改写。

## 5. 交互：工具栏、全屏、导出

### 5.1 工具栏（渲染成功后）

文案键走 i18n（中/英）：

- 图形 | 源码
- 全屏
- 导出 SVG
- 导出 PNG

### 5.2 图形 / 源码

- 默认「图形」。
- 「源码」显示只读原始文本；不销毁已缓存的 SVG；切回「图形」直接复用，不再调用 `mermaid.render`。

### 5.3 全屏（Lightbox）

- 触发：工具栏「全屏」或点击图表区域。
- 行为：遮罩 + 居中 SVG；Esc / 点遮罩 / 关闭按钮退出。
- 缩放：滚轮；平移：拖拽。
- Lightbox 内可再次导出（复用同一导出函数）。

### 5.4 导出

- **SVG**：下载当前 SVG 字符串，`image/svg+xml;charset=utf-8`。
- **PNG**：SVG → Image → 有界 canvas（限制最大边长/像素，防止 OOM）→ `image/png`；超限显示中文错误，SVG 仍可导出。
- 文件名：`chemclaw-diagram-YYYYMMDD-HHmmss.svg|.png`。
- 未成功渲染时导出与全屏禁用。

## 6. 错误降级

| 情况 | 行为 |
| --- | --- |
| 语法/渲染失败 | 中文错误（如「无法渲染此图表」）+ 展示源码；气泡不崩 |
| 源码超过 `maxTextSize` | 拒绝渲染并提示过长 |
| PNG 超画布上限 | 中文失败提示；SVG 仍可用 |
| `import('mermaid')` 失败 | 保留源码 + 可理解错误（可含重试入口） |

## 7. 明确不做（本任务）

- 浏览器原生 Fullscreen API
- 服务端预渲染 SVG/PNG
- 流式过程中出图
- 阶段五权威/版本化产业链图
- 修改 Skill 安装内核或后端 turn 协议

## 8. 文件变更范围（实施时）

预计修改/新增（实施计划可再拆步）：

- 新增：`surfaces/gui/src/components/MermaidBlock.tsx`
- 新增：`surfaces/gui/src/components/MermaidBlock.test.tsx`
- 新增：`surfaces/gui/src/components/MermaidLightbox.tsx`
- 新增：`surfaces/gui/src/mermaidExports.ts`（及对应测试）
- 修改：`surfaces/gui/src/components/Markdown.tsx` / `Markdown.test.tsx`
- 修改：`surfaces/gui/src/components/Transcript.tsx`（流式关闭渲染）
- 修改：`surfaces/gui/src/i18n.tsx`、`styles.css`
- 修改：`surfaces/gui/package.json` / lockfile（钉扎 `mermaid@11.16.0`）
- 文档：`docs/chemclaw/README.md`、`TESTING.md`；可选 e2e `mermaid.spec.ts`

不修改：`coworker/` 业务逻辑（除非实施中发现与本能力无关的阻塞，另开任务）。

## 9. 测试与验收

### 9.1 自动化

- Mock `mermaid` 的单元测试：
  - fenced mermaid → 出现图表容器
  - 普通 fenced code 仍为代码
  - `renderMermaid={false}` 不渲染图
  - 图/源码切换保留源码文本
  - 渲染失败显示降级 UI
  - 导出助手被调用
  - `artifact:` 芯片回归
- `mermaidExports`：文件名格式、超限拒绝
- `npm run build` 通过（含 lazy chunk）

### 9.2 手工验收

1. 对话中完成含 mermaid 的回答 → 出图；流式过程中不出图。
2. 打开 MD 报告预览 → 同样出图。
3. 全屏可开关；导出 SVG/PNG 可下载。
4. 长页多图滚轮无抖动。
5. 故意坏语法 → 中文错误 + 源码可读。

### 9.3 验收门禁（全部满足才算完成）

1. 回答与报告中的 fenced mermaid 渲染为图，可全屏、可导出 SVG/PNG。
2. 流式时只见代码，结束后出图。
3. 滚轮浏览多图长页无明显抖动。
4. 坏语法有中文错误 + 源码可读。
5. 非 mermaid 代码块与 `artifact:` 芯片行为不变。

## 10. 与既有决策的对齐

- **D-028**：对话与 Markdown 报告预览真实渲染 — 本设计覆盖。
- **D-029**：图/源码、安全渲染、失败降级、SVG/PNG — 本设计覆盖；全屏为 D-029 之上的 UX 增强（遮罩查看）。
- **D-030**：本图仍是对话/报告临时制品，不是阶段五权威产业链图。

## 11. 下一步

用户批准本规格后：

1. 使用 `writing-plans` 编写小步实施计划。
2. 用户批准实施后按任务逐项实现、验证、提交。
