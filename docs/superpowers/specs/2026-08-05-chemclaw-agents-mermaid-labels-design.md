# ChemClaw 智能体一期 + Mermaid 边标签设计

- 日期：2026-08-05
- 状态：grilling 共同理解已确认；用户批准按计划执行
- 关联决策：D-006（修订）、D-063–D-068
- 计划：智能体 UX（Cursor plans）+ Mermaid edge labels

## 1. 智能体一期（摘要）

品类名改为「智能体」；单色龙虾图标；钴蓝主题不变。拆包联装（Skill 整目录 / Agent 快照 md）；只读详情；默认技能接线；新建对话 A1（单行按钮 + 本会话身份）。内置 B1 只读；编辑/另存为/本会话切换为二期。

详见已确认计划与 DECISIONS D-064–D-068。

## 2. Mermaid 边标签（摘要）

生成侧缺标签，非渲染 bug。约束集中在 `agent.py` 全局附录 + 仓库 `AGENTS.md`；少数出图 Skill 补强；可选 GUI 缺标签软提示。禁止逐 Agent/Skill 复制全文。

详见 D-063。
