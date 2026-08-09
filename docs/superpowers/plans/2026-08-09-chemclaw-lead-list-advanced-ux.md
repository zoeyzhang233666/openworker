# ChemClaw 客户清单进阶 UX Implementation Plan（待点名后实现）

> D-098 首包之后的规格 §10 剩余；**未点名不写代码。**

**Goal:** 在客户清单工作台增加证据详情、继续补查、ICP 重评入口与断点续跑提示；仍无 CRM/发送按钮。

**Architecture（拟定）：**
- GUI `LeadsWorkbench`：行展开证据摘要；「继续补查」注入对话意图（对齐 `requestSendApproval` 模式）
- 可选读取工作区 `ProspectingRun` JSON 展示预算/阶段
- 不自动重跑拓客；重评须用户确认

**验收：** localization-audit 绿；无发送/CRM；空清单仍可用。

**Out of Scope：** TED、SMTP 重做、买联系人。
