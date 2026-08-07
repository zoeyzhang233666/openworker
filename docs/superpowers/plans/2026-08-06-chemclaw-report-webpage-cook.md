# ChemClaw 报告网页版烹饪 — 实施计划

> **For agentic workers:** 按任务顺序执行；每个 Task 先写失败测试再改代码。规格已于 2026-08-06 获用户批准。

**规格**：[`docs/superpowers/specs/2026-08-06-chemclaw-report-webpage-cook-design.md`](../specs/2026-08-06-chemclaw-report-webpage-cook-design.md)  
**决策**：D-077（修订 D-072 G4）

---

### Task 1: 设置开关 + prefs 默认开 + 中英文案

**Files:**
- Modify: `coworker/server/manager.py`（prefs get/set；缺省键视为 `true`）
- Modify: `coworker/server/app.py`（若设置 API 需暴露新字段）
- Modify: `surfaces/gui/src/components/SettingsView.tsx`（或设置子页）
- Modify: `surfaces/gui/src/interfaceMessages.ts` / `interfaceMessagesZh`（及相关 i18n）
- Test: prefs 默认开；关闭后 API 返回 false；localization-audit / i18n

**Steps:**
1. 约定 prefs 键名（如 `cook_webpage_after_md`），缺省 / 缺失 = 开。
2. 设置 UI 名称/说明与规格一致（中文定稿；英文对等）；用户文案不用「芯片」。
3. 跑通相关测试。

**验收：** 新鲜 prefs 与缺省行为为开；关闭可持久化；设置页中英文正确。

---

### Task 2: 检测最终 md 交付并在 turn 结束后入队烹饪

**Files:**
- Create: `coworker/webpage_cook.py`（或等价模块：解析 `artifact:….md`、任务表、取消同路径旧任务）
- Modify: `coworker/server/app.py` / turn 完成钩子（`turn_done` 附近）
- Modify: `coworker/server/manager.py`（读 prefs、会话工作区路径）
- Test: `tests/test_webpage_cook.py`（解析多链接、忽略非 md、prefs 关不入队、同路径取消旧任务）

**Steps:**
1. 从当轮最终助手消息提取 `[title](artifact:path.md)` 列表。
2. turn 成功结束后若 prefs 开则入队；主 turn 状态不得因烹饪保持 `running`。
3. 同一相对路径未完成任务先 cancel 再 enqueue。
4. 窄通道模型调用骨架可先 stub（Task 3/5 接状态与重试）；本 Task 至少证明入队/取消语义。

**验收：** 交 md 后入队；关开关不入队；同文件重交付取消旧任务；主 turn 已 `turn_done`。

---

### Task 3: 烹饪状态事件 → 对话区三态文案

**Files:**
- Modify: `coworker/server/app.py`（WS/事件：`webpage_cook` 进行中/成功/失败）
- Modify: `surfaces/gui/src/App.tsx` / Transcript 相关
- Modify: `surfaces/gui/src/interfaceMessages.ts`（三态模板，`{标题}` 插值）
- Test: 事件驱动 UI 文案；中英键

**文案（中文定稿）：**
- 进行中：`龙虾下厨中，正在烹饪网页版《{标题}》，文档版可以先看~`
- 成功：`龙虾为你精心烹饪了网页版《{标题}》，比干巴巴的文字顺眼多了，点开看看吧~`
- 失败：`这锅网页版炖糊了，先看 md 文档版吧，要不要让龙虾再下厨一回？`

**验收：** 三态按序出现；进行中可继续读文档版；无「芯片」字样。

---

### Task 4: 右侧 HTML 预览沙箱（网络策略按 D-077）

**Files:**
- Modify: `surfaces/gui/src/components/RightRail.tsx`（现有 `iframe` + `sandbox="allow-scripts allow-same-origin"`）
- Create/Modify: 预览封装或 CSP/`srcDoc` 注入策略（禁外链 script、禁 POST 报告；允许静态资源与只读 GET）
- Test: 组件/策略单测（外链 script 无效或被剥；POST 被拦）

**Steps:**
1. 在现有 HTML 预览上加强沙箱，对齐 D-077 表。
2. 不破坏已有 html 产物预览冒烟路径。

**验收：** 开放页内脚本仍可跑本地交互；外链 JS / POST 本地报告按策略失败；主 UI 不崩。

---

### Task 5: 成功自动打开；失败轻提示 + 再下厨

**Files:**
- Modify: `surfaces/gui/src/App.tsx`（同会话成功 → 打开 RightRail 对应 HTML）
- Modify: 烹饪模块（真正调用模型写 HTML；配对路径如 `foo.md` → `foo.html` 或规格约定名）
- Modify: UI「再下厨」触发重新入队
- Test: 成功打开预览；离开会话不抢焦点；重试入队

**Steps:**
1. 接上真实窄通道烹饪（提示词：开放 HTML/JS、鼓励控件、定量不编造、自包含优先）。
2. 成功事件携带 html 相对路径；GUI 若 `sessionId` 匹配则 `onPreview` 打开。
3. 失败展示文案与重试控件。

**验收：** 同会话自动打开网页版；失败可重试且文档版仍可读；烹饪不阻塞新 turn。

---

### Task 6: 全局/龙虾提示词：短气泡 + 去掉先问网页

**Files:**
- Modify: `coworker/agent.py`（`_CLARIFY_POINTER`、`_LONG_TASK_GUIDANCE`）
- Modify: `coworker/personas/builtin/chain-lobster.md`
- Test: 若有提示词快照/字符串断言测则更新；否则文档化抽检清单

**Steps:**
1. 删除「白话问要不要网页」。
2. 约定：有最终文档版时短答 + `artifact:….md`；不要同轮自写长 HTML 挡阅读；网页版由系统烹饪。
3. 保留禁止 browser 验证本地页（D-075）。

**验收：** 源码中无「先问要不要网页」类句子；短答与文档版交付约定可检索到。

---

### Task 7: 回归测试与控制台闭环

**Files:**
- Tests: 汇总 Task 1–6 相关 pytest / npm test
- Modify: `docs/chemclaw/README.md`（✅ D-077 落地状态；记录实测命令与结果）
- Modify: `docs/chemclaw/DECISIONS.md` / 规格状态行（若需标「已落地」）

**验收：** 相关测试通过；README 反映已实现而非「待批准」；无运行时代码把 OpenWorker 露出到正常 UI。

---

## 依赖与风险

- 烹饪耗时与模型费用：必须与主 turn 解耦（Task 2/5）。
- HTML 沙箱与「只读 GET」在 Electron/iframe 上的可达性需在 Task 4 实测；若平台限制过严，优先保「禁外链 JS + 禁 POST」，再文档化 GET 降级。
- 短气泡依赖提示词遵从（Task 6）；若模型仍写长文，另案再议 UI 折叠，不在本计划扩大范围。
