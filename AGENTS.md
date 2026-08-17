# ChemClaw 项目协作说明

本仓库正在把 OpenWorker 渐进式升级为芯化和云的 ChemClaw。ChemClaw 是唯一对外产品；OpenWorker 只是底层技术来源，SAG 只是后续知识检索与图谱能力来源。

## 每个 Codex 任务开始前

按顺序阅读：

1. `docs/chemclaw/README.md`
2. `docs/superpowers/specs/2026-07-29-chemclaw-product-design.md`
3. `docs/chemclaw/DECISIONS.md`
4. `docs/chemclaw/DOMAIN.md`
5. 当前里程碑在 `docs/superpowers/plans/` 下的实施计划（存在时）

先用中文简要汇报当前状态、这次任务边界、验收标准和预计修改范围，再开始工作。不要依赖旧聊天记录恢复项目事实。

## 不可违反的产品边界

- 正常界面、安装程序、快捷方式、图标和产品文案中只显示 ChemClaw，不显示 OpenWorker。
- 在“关于/开源许可”中保留 OpenWorker、SAG 及其他依赖要求的许可证和版权说明。
- 永远不实现 UI Demo 中的“数据底座”页面。未来相应产品区域是知识检索、2D/3D 图谱、探索模式和化工产业链知识。
- 默认语言是简体中文，支持切换英文。第一方错误、审批、安装和配置流程也必须中文化。
- 保留并回归验证 OpenWorker 的对话、MCP、权限、审批和定时任务能力。
- 所有显示出来的按钮必须有真实功能；未实现功能不提前放入首版界面。
- Skill 与 Agent 的安装必须处理脚本、依赖、配置、兼容性、测试和回退，不能只复制 `SKILL.md`。
- 用户安装或修改 Skill/Agent 后，所有对话的后续调用使用最新有效版本。
- Agent 不能绕过既有权限和审批机制。
- SAG 只提供检索、索引、备份恢复、2D/3D 图谱和探索能力；不采用 SAG 原有对话系统。
- 阶段五的标准产业链图是可审阅、可版本化的权威知识制品，不能每次提问时临时生成不同答案。

## 工程工作流

- 未经批准的设计不得直接实现。
- 多步骤实现必须先有本地规格和实施计划。
- 稳定 `main` 不用于试验；通常只保留一个当前功能 Worktree。
- 每次只完成一个可独立验收的小任务，使用小提交。
- 修改前确认工作区状态，不覆盖用户已有改动。
- 完成前运行与风险相称的测试，并记录实际结果；不以“应该能用”代替验证。
- 合并 `main`、构建正式安装程序、管理员权限安装和可能写入真实外部数据的操作，需要用户明确确认。
- 每个任务结束时更新 `docs/chemclaw/README.md` 的状态和相关决策/计划。

## Mermaid 图

- 输出 `flowchart` / `graph` / `sequenceDiagram` 等有向关系图时，**每条边必须有关系标签**（如 `A -->|"采购"| B` 或 `A->>B: 请求`）。禁止裸 `A --> B`。
- 标签默认中文；用户要求英文时用英文。含特殊字符时加引号。
- 不要把该规则复制进每个 Skill；产品运行时另有全局附录。

## 当前门禁

产品设计与阶段 1 实施计划已获批准。销售主线首包（D-091—D-122）与内容重构 M1+M2+M3（D-104/D-107/**D-128**）已落地。**D-127 HubSpot 字段更新/任务创建 CTA 已落地**。**D-131 默认智能体自称 ChemClaw**（system prompt/title/UI，id 仍 `cowork`）。当前：公开查询必显销售 Provider；VAT/汇率/维基已接线；**化工社只读 + 写反应 + SVG 落盘**（D-118/D-119/D-120）；**压缩硬裁提示中性化**（D-121）；**压缩默认 70%/100k**（D-129）；**四销售龙虾专属空态三卡**（D-122）。**性能 Router v5：HARD STOP A–G + §65 46–55 已完成；Step 56–59 已授权落地**（routing + projection + structured-tools true streaming known-safe + Emergency Finalization built-in = 候选 ON；unknown/custom 仍 buffered；FAST/KNOWLEDGE EF 强制 OFF；NEW FAIL = none）。**四开关独立 rollout 已全部完成**。下一刀须新独立授权（合集 P0 / 其它产品门禁）。按 GATE 点检 D-108+。以 `docs/chemclaw/README.md` 为准。
