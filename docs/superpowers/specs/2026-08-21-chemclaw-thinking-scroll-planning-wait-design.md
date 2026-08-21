# ChemClaw 思考框贴底滚动 + 规划间隙提示

**日期**：2026-08-21  
**状态**：已落地（D-176）  
**范围**：对话 GUI live ThinkingBlock 正文贴底跟随，以及 reasoning 停更到步骤卡出现前的规划间隙提示；不改后端、Router、TurnGroup（D-070）。

## 背景

1. live「正在思考」正文有 `max-height: 280px`，流式更新时不自动滚到最新，用户看不到实时思考。
2. 有 `reasoningStream` 后龙虾空窗等待关闭；思考停更到 `tool_proposed` / 回答流出现前，若思考被收起或只剩静态框，界面长时间安静，易被误判为任务中断。

## 目标

1. live 思考正文在用户仍贴底时，随 `reasoning_delta` 自动滚到最新；用户在思考框内上翻则暂停，回到底部再恢复。
2. 空白期（有 reasoning、尚无工具/回答进展）**强制保持思考正文展开**，并在思考框下方显示「龙虾正在规划下一步」类轮播提示。
3. 步骤卡或回答流出现后，规划提示消失；不伪造 upstream reasoning。

## 产品行为

### 思考框贴底

- 作用域：`.thinking-body` 内部滚动，不替代主 transcript FB-004。
- 贴底阈值约 24–48px；主列表 stick-to-bottom 依赖增加 `reasoningStream`（仍受 `atBottomRef` 约束）。

### 空白期强制展开

- 条件与 `isFirstTokenThinkingOpen` 相同：尚无锚点后活动。
- `forceOpen`：该期内标题可点，但不允许收成一行标题。
- 首包期结束后（有工具/回答），恢复既有可手动折叠行为；settled「思考过程」默认仍收起。

### 规划间隙提示

- 谓词：`running && !compacting && reasoningStream && !streaming && !hasPostAnchorActivity`。
- 文案池 `planning`（约 3s 轮播，中英对等）：
  - Lobster is planning the next step… / 龙虾正在规划下一步…
  - Mapping tools for what comes next… / 龙虾正在梳理下一步要调用的能力…
  - Still on it — next move soon… / 还在忙，下一步马上就来…
- 无 reasoning 的空窗仍走 D-076/D-079 first/feedback 池。

## 非目标

- 不改 settled ThinkingBlock 默认收起、TurnGroup 生命周期。
- 不覆盖工具执行中途的另一套等待文案 / Plan-then-Act。
- 不伪造 reasoning。

## 验收

- 思考流式更新时正文跟到底；上翻后不强制贴底。
- 空白期思考正文保持展开 + 下方规划提示；步骤卡出现后提示消失。
- 定向 Vitest + i18n/localization-audit 通过。
