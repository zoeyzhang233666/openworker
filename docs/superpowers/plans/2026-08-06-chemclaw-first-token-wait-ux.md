# ChemClaw 首包空窗 UX — 实施计划

> **For agentic workers:** 按任务顺序执行；每个 Task 先写失败测试再改代码。

**规格**：[`docs/superpowers/specs/2026-08-06-chemclaw-first-token-wait-ux-design.md`](../specs/2026-08-06-chemclaw-first-token-wait-ux-design.md)

---

### Task 1: 龙虾文案池与阶段切换纯函数

**Files:**
- Create: `surfaces/gui/src/firstTokenWaitCopy.ts`
- Test: `surfaces/gui/src/firstTokenWaitCopy.test.ts`

**Steps:**
1. 写测试：前/后段池非空；`pickCopy(phase, rng)` 从对应池抽取；同 seed 可复现；常量 `FIRST_TOKEN_WAIT_LATE_MS === 3000`。
2. 实现中英键或原文池（与 i18n 键对齐见 Task 3）。
3. 跑通测试。

---

### Task 2: ThinkingBlock 首包期默认展开 + 手动覆盖

**Files:**
- Modify: `surfaces/gui/src/components/Transcript.tsx`
- Test: `surfaces/gui/src/components/ThinkingBlock.test.tsx`（新建；或并入既有 Transcript 测）

**Steps:**
1. 写失败测试：`defaultOpen` 时正文可见；点击后可收起并保持（手动覆盖）。
2. 给 `ThinkingBlock` 增加 `defaultOpen?: boolean`；内部 state 初始为 `!!defaultOpen`；点击切换后不再被 prop 强行改回（本实例粘性）。
3. App 在 live 首包路径传 `defaultOpen`。

---

### Task 3: 首包等待条接入 App + i18n

**Files:**
- Modify: `surfaces/gui/src/App.tsx`
- Modify: `surfaces/gui/src/interfaceMessages.ts`
- Create: `surfaces/gui/src/useFirstTokenWaitLabel.ts`（或内联于小组件）
- Test: `surfaces/gui/src/useFirstTokenWaitLabel.test.ts` / 组件测

**Steps:**
1. 测试：进入等待时显示前段句；`advanceTimersByTime(3000)` 后切后段；同一次等待文案钉死；有 reasoning/streaming/工具时不渲染龙虾等待。
2. 首包路径不再默认 `t("Waiting for agent...")`；压缩态仍用 `Compacting context…`。
3. 中英键写入 `interfaceMessagesZh`；localization-audit / i18n 测覆盖。

---

### Task 4: 文档闭环

更新 `docs/chemclaw/README.md` 与 `DECISIONS.md`（D-076）。
