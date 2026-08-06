# ChemClaw 首包空窗 UX

**日期**：2026-08-06  
**状态**：已落地（D-076）  
**范围**：对话 GUI 首包空窗与 live ThinkingBlock 默认展开；不碰里程碑 D 的压缩/工具间隙/Plan-then-Act。

## 背景

新对话发送后，turn 已 `running`，但在第一条可见进展（reasoning / 流式正文 / 工具或审批）出现前，界面长时间只显示「正在等待 Agent…」。用户看不到思考过程，易误判模型未工作。

## 目标

1. 有 `reasoning_delta` 时，首包期内 ThinkingBlock **默认展开**，让用户看见思考正文。
2. 无 reasoning 时，用 ChemClaw 龙虾口吻文案池证明「还在动」：按前池→后池顺序约每 3 秒轮播，直到有进展。
3. 不再在首包空窗长期使用含糊的「正在等待 Agent…」。

## 产品行为

### 首包空窗 / 首包期

- **首包空窗**：turn 已 `running`，但尚未出现任一可见进展时的静默区间。
- **首包期**：从用户发送到首包空窗结束的时段。
- **结束条件（任一即结束）**：出现 reasoning、任意流式正文、工具条目或审批条目。

### 有 reasoning

- 尽早渲染 live ThinkingBlock。
- 首包期内默认展开正文；用户点击标题后，该 live 实例内手动覆盖优先。
- 首包期结束后，live/定稿 ThinkingBlock 恢复既有默认折叠（不扩大 D-070 稳态规则）。

### 无 reasoning（龙虾等待条）

- 全局龙虾口吻（所有智能体同一套段子）。
- 轮播序列 = 前池全部 + 后池全部；每次等待从第 1 句起，约每 **3 秒** 前进一句并环绕，直到首包结束。
- 压缩态仍用既有「正在压缩上下文…」分支，不走龙虾池。

**中文池**

| 段 | 文案 |
|---|---|
| 前 | 龙虾正在挠头想… |
| 前 | 龙虾正把问题掰开揉碎… |
| 后 | 龙虾还在深潜，马上冒泡… |
| 后 | 龙虾思考有点长，别以为它睡着了… |
| 后 | 龙虾还在啃这道题，马上吐泡… |
| 后 | 龙虾在慢慢熬一锅好回答… |

**英文池**

| 段 | 文案 |
|---|---|
| 前 | Lobster's scratching its head… |
| 前 | Lobster's breaking the question into bits… |
| 后 | Still diving deep — bubbles soon… |
| 后 | Thinking long — not napping… |
| 后 | Still chewing on it — bubbles soon… |
| 后 | Slow-cooking a good answer… |

## 非目标

- 后端新事件或细工程阶段（鉴权/组上下文等）。
- 假计划气泡、按智能体切换口吻。
- 里程碑 D：压缩进度细化、工具时间线状态机、Plan-then-Act。

## 与里程碑 D 的边界

本切片只解决**首包空窗**误判。压缩态可见、工具间隙「等待模型」、研究智能体 Plan-then-Act 仍见 [`2026-08-06-chemclaw-agent-runtime-ux-design.md`](./2026-08-06-chemclaw-agent-runtime-ux-design.md)。

## 验收

- [x] 新对话发送后不再长期只显示「正在等待 Agent…」。
- [x] 有 reasoning：首包期内思考正文默认可见。
- [x] 无 reasoning：立即见前池第 1 句，约每 3s 按前→后池顺序轮播；有进展后等待条消失。
- [x] 中英切换均有对等可爱文案；压缩态行为不变。
- [x] 相关前端 / i18n 测试通过。

## 后续实施

见 [`../plans/2026-08-06-chemclaw-first-token-wait-ux.md`](../plans/2026-08-06-chemclaw-first-token-wait-ux.md)。
