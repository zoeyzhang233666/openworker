# ChemClaw 思考结束收起连续可见（D-183）

**日期**：2026-08-21  
**状态**：已落地（D-183）  
**范围**：对话 GUI live→settled 思考交接与规划等待窗口；TurnGroup 保留 reasoning；不改后端、Router、D-070/D-178 live forceOpen。

## 背景

D-178 让 live「正在思考」挂载即强制展开。`assistant_message` 清空 `reasoningStream` 后 live 卸载；thinking-only assistant 使 `hasPostAnchorActivity` 为 true，规划/龙虾等待全部关掉；工具到达后 `buildRows` 丢弃无正文 reasoning，思考整块消失，首轮出现「大片空白再出现正在运行 x 个步骤」。

## 目标

1. 思考结束改为**收起**（标题「思考过程」可见），不整块消失。
2. 收起后到步骤/回答出现前，继续轮播规划等待文案。
3. 步骤卡出现后，Turn 上方仍保留可展开的 settled ThinkingBlock（汇出最新非空 reasoning）。
4. 多轮工具间隙同源修复；D-178 live 挂载仍 forceOpen。

## 产品行为

- live 条件不变：`running && reasoningStream && !streaming` → forceOpen + 贴底。
- settled / Turn 内 ThinkingBlock 默认收起，可手动展开。
- 规划等待扩展：live stream 已清、尚无 tool/approval/非空回答，但锚点后已有带 reasoning 的 assistant 时仍显示 planning 池。
- 出现 tool、非空 streaming、或非空 assistant 正文后提示消失。

## 非目标

- 不伪造 reasoning；不改 TurnGroup 自动开合；不把 planning 挂到步骤出现之后；不保留「正在思考…」脉冲到步骤之后。

## 验收

- 首轮：思考结束 → 收起标题 ± 规划文案 → 步骤出现且思考仍可展开。
- 多轮间隙不空白。
- 定向 Vitest（firstTokenWaitCopy + Transcript/ThinkingBlock）通过。
