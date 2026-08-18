# ChemClaw 已批准决策

本文件只记录已经批准、会约束后续工作的决定。新的重要决定按编号追加；不得静默改写旧决定。

## 产品与范围

- **D-001**：ChemClaw V1 保留 OpenWorker 的对话、MCP、权限、审批和自动化能力，并新增 ChemClaw 品牌、可视化 Skill 页面、安装与点击调用能力。
- **D-002**：V1 是 Windows、本地优先、单用户桌面产品；“SaaS 风格”只描述交互方式，不引入多租户、账号、计费或云同步。
- **D-003**：ChemClaw 是唯一对外品牌。正常界面、安装程序和快捷方式不出现 OpenWorker；MIT 署名只保留在关于和法律通知中。
- **D-004**：UI Demo 只作为视觉和信息架构参考；所有假数据、假按钮和概念交互都不能直接当成完成的功能。
- **D-005**：“数据底座”页面永久排除。未来相应区域改为 SAG 检索、2D/3D 图谱、探索模式和化工产业链知识。
- **D-006**：V1 一级导航为对话、技能、智能体、定时任务、连接和设置；审批、审计与历史为二级页面。（2026-08-05：品类名由「专家龙虾」改为「智能体」；角色显示名仍可含「龙虾」。）（2026-08-09：**D-098** 在智能体与定时任务之间增加「客户清单」。）
- **D-007**：所有可见按钮必须接入真实功能，未实现的功能不提前显示。

## 语言与展示

- **D-008**：默认语言固定为 `zh-CN`，支持 `en-US` 切换并持久保存。
- **D-009**：所有第一方页面、错误、审批、安装器和配置向导都必须中英文可用；默认 Agent 回答中文，用户明确要求英文时切换。
- **D-010**：名称和介绍使用中英文展示元数据；实际执行指令保留一份权威内容，默认不自动翻译执行正文。
- **D-011**：ChemClaw 内置化工产业链智能体对外显示名为「产业链龙虾」（代码 id `chain-lobster`）。历史名称「白毛股神 Serenity」仅用于 OpenClaw 能力包合成产物（`serenity`）与来源说明，不再作为 ChemClaw 内置默认展示名。（原表述已由 D-072 修订。）

## 领域模型

- **D-012**：Skill 是可复用工作流和能力单元；Agent 是角色、提示、工具、默认 Skills、MCP 和权限策略的组合；任务模板是提示词、Agent/Skills、时间和输出的组合。
- **D-013**：`serenity-full-package` 识别为一个 Agent 加七个独立中文投研 Skills；Agent 通过引用组合 Skills，不复制内容。
- **D-014**：Skill 与 Agent 可分别编辑、记录修订和恢复。
- **D-015**：点击 Skill 或 Agent 后新建对话并显示会话级挂载标签；允许挂载多个 Skills，全部可见。
- **D-016**：自然语言自动选择 Skill 必须可见、可解释、可移除；用户明确指定时具有最高优先级。
- **D-017**：所有对话的后续调用使用最新有效 Skill/Agent 版本。历史只记录当时版本用于诊断；恢复旧内容会创建新的当前修订。

## 安装、运行与配置

- **D-018**：本地路径、GitHub URL、技能页面和一句话安装共用同一个安装内核。
- **D-019**：安装器在运行前识别 Agent、Skills、脚本、资源、依赖、MCP、环境变量和操作系统要求，并展示中文安装计划。
- **D-020**：用户一次确认后，计划范围内的依赖下载和安装脚本自动执行；新增管理员权限或超出计划的行为必须再次确认。
- **D-021**：依赖型 Skill 使用 ChemClaw 管理的持久运行环境，跨对话和重启继续可用；纯说明型 Skill 不创建多余环境。
- **D-022**：安装在暂存区完成，测试通过后原子激活；失败保持上一有效版本并支持回退/卸载。
- **D-023**：Windows 不兼容能力不出现在普通 Skill 页面，只在安装报告“已跳过”详情中记录。
- **D-024**：兼容但缺少账号、密钥或端点的能力显示“待配置”，通过简化向导、服务商预设和连接测试完成配置。
- **D-025**：凭据不进入 Skill 文档、Git 历史、模型上下文或备份；ChemClaw V1 将现有文件型 SecretStore 升级为 Windows 加密存储。
- **D-026**：Git 更新不静默覆盖本地 Skill 修改；必须显示差异并允许更新、保留或合并。
- **D-027**：Serenity 首版保证 Agent、七个核心中文投研 Skills、相关兼容脚本和 Mermaid 能力在 Windows 真正可用；其他兼容项自动处理，不兼容项隐藏。

## Mermaid 与输出

- **D-028**：对话和 Markdown 报告预览支持 fenced `mermaid` 代码块真实渲染。
- **D-029**：Mermaid 支持图形/源码切换、安全渲染、失败降级及 SVG/PNG 导出。
- **D-030**：产业链类 Skill 可以要求输出 Mermaid，但阶段五的标准产业链图不依赖每次对话临时生成。
- **D-063**：Mermaid 关系图（flowchart/graph/sequenceDiagram 等）的边必须带语义标签。约束集中注入 `coworker/agent.py` 全局附录与仓库 `AGENTS.md`；禁止复制到每个 Agent/Skill。仅出图类 Skill（如产业链层级测绘）与 skill-creator 模板可补强一句。渲染层忠实绘制、不得自动编造边文案，也**不得**向用户展示「缺标签」类提示（该要求仅面向模型）。

## 智能体页与安装（2026-08-05）

- **D-064**：产品对外品类名「智能体」= 领域 Agent = 代码 persona。导航图标为单色描边小龙虾 SVG；主题强调色维持钴蓝 `--accent`，不引入 Demo 橙。
- **D-065**：内置智能体只读，靠发版更新（B1）；用户个性化通过二期「另存为自定义副本」。一期只做只读详情（提示词、默认技能、路径）。
- **D-066**：智能体安装源为 GitHub、本地目录、zip/单文件 md。宽松扫描：含 `SKILL.md` 的目录整树装入技能库；persona `*.md` 只快照 md。冲突逐项覆盖或跳过；缺引用 Skill 仍装 Agent 并警告。运行时依赖不自动安装（对齐 D-060）。完整能力包依赖安装器仍属 D-019。
- **D-067**：新建对话主按钮按标星默认一键开聊（按钮保持单行）；▾ 可选换智能体，菜单中文，`surfaced` 控制列表。回答区「助手」显示本会话智能体名；空会话提示「与 xxx 畅谈」。改全局默认不重绑当前会话（S1）。本会话中途切换与按条 `agent_id` 为二期。
- **D-068**：智能体 frontmatter `skills:` 须在新建该智能体对话时自动挂载已安装的默认 Skill（未安装的可见提示）。
- **D-069**：智能体 zip/目录安装扩展（D-066）：若包内**无**合法 ChemClaw persona md，但存在 OpenClaw `IDENTITY.md` 和/或 `SOUL.md`，判定为 OpenClaw 身份包。此时把工作区 md（IDENTITY/SOUL/AGENTS/USER/TOOLS/MEMORY，以及有实质内容的 HEARTBEAT）**合成进一个** ChemClaw 智能体提示词（写入 `.chemclaw-generated/manifest.md`），**不**把 AGENTS/USER/TOOLS/HEARTBEAT 安装为独立智能体；顶层同名模板与 `agents` 等子目录仅在该信号下排除出 persona 候选（不是全局文件名黑名单）。`MEMORY.md` 写入提示词；`memory/` 目录本阶段不整树导入。运行时只读合成后的 system_prompt，不热读 OpenClaw 工作区。包名含 serenity 或技能命中七个中文投研 Skill 时 id=`serenity`、名=`白毛股神 Serenity`。冲突预览支持「全部覆盖/全部跳过」与 i18n；完整能力包安装器仍属 D-019。

## Git、环境与发布

- **D-031**：采用渐进式模块化升级，不重写 OpenWorker 核心，不整体嵌入 SAG。
- **D-032**：OpenWorker 是需要选择性跟踪的上游；SAG 不是第二上游，只迁移经过审计和测试的图谱/检索模块。
- **D-033**：稳定 `main` 不用于试验；通常只保留 `main` 和一个当前功能 Worktree，紧急修复时才增加临时 Worktree。
- **D-034**：Worktree 隔离源码，不为每个 Worktree 重配 MCP。普通 Worktree 共用一个持久开发配置。
- **D-035**：开发版和稳定版的业务数据库分离；凭据保险箱和不可变依赖缓存可共享，激活版本指针分离。
- **D-036**：高频修改使用源码热更新；功能验收后合并 `main`，稳定里程碑才构建 ChemClaw 安装程序。
- **D-037**：Git 回退源码，数据备份回退运行数据，两者都必须保留。
- **D-038**：当前 OpenWorker 是刚克隆的源码，没有用户数据，因此当前 V1 不实施旧用户数据迁移。

## SAG 检索、图谱与备份

- **D-039**：SAG 以独立本地 Sidecar 接入，保留索引、增量更新、关系推理、检索、备份恢复、2D/3D 和探索能力；不采用 SAG 对话系统。
- **D-040**：ChemClaw 前端原生实现图谱页面，不嵌入 SAG 的 Next.js 应用。
- **D-041**：SAG 是对话可调用的知识检索引擎，不只是图形展示组件。
- **D-042**：保留 `vector` 快速检索和 `multi` 精确多跳检索。普通对话默认自动，Serenity 和严谨研究 Skills 默认深度检索。
- **D-043**：SAG 返回原文块、实体、事件、关系和引用；最终回答由 ChemClaw/OpenWorker 对话系统生成。
- **D-044**：检索范围、实际模式、引用和降级状态必须可见；精确检索回退快速检索不能静默发生。
- **D-045**：知识库内容视为不可信数据，不能通过文档提示词取得 Agent 或工具权限。
- **D-046**：图谱支持导入 JSON、导出 JSON、导出完整备份和一键恢复。
- **D-047**：恢复默认创建新图谱项目；覆盖当前项目需要展示影响范围、自动安全备份和再次确认。
- **D-048**：完整恢复兼容 `.tgz`、PostgreSQL/pgvector `.dump` 和 `.json`。优先复用兼容向量，只有确实不兼容时才重新向量化。
- **D-049**：大数据导入/恢复使用后台分批任务、流式读取、限流、检查点、暂停/继续/取消和幂等重试，不能卡死界面。
- **D-050**：完整备份包含关系数据、向量索引、上传资料、清单、版本和校验值，但默认不包含敏感凭据。

## 阶段五知识产品方向

- **D-051**：阶段五以稳定 ID 的化工百科页和双向链接为核心，支持从品种跳转到来源、应用、上下游、同义词、价格和标准产业链图。
- **D-052**：标准产业链图是可审阅、可版本化、可复现的权威知识制品；AI 可以辅助提取和更新，但同一已发布版本不能因用户重新提问而变化。
- **D-053**：以下三份本地文件是阶段五正式设计来源：
  - `C:\Users\EDY\Nutstore\1\ob\线1_来源路径树_v2.1-蒋老师.md`
  - `C:\Users\EDY\Nutstore\1\ob\化学品缩写消歧规则-蒋老师.md`
  - `C:\Users\EDY\Nutstore\1\ob\线2_应用去向树_v3.0-蒋老师.md`
- **D-054**：化学品唯一身份优先使用 CAS；歧义缩写按强制规则进入上下文消歧或人工确认，不能仅凭缩写合并节点。
- **D-055**：Tencent/WeKnora 的互链 Markdown Wiki、Wiki 浏览和可视图谱作为阶段五产品参考；是否复用代码需在阶段五单独评估，不在当前技术选型中决定。
- **D-056**：交互价格图原则上可行，数据必须来自有时间戳和来源的 MCP/价格接口；具体图表形式、刷新频率和授权规则在阶段五设计时决定。

## Skill 内置与命名（2026-08-04）

- **D-057**：Skill `name` 允许 Unicode 字母/数字（含中文）以及 `.` `-` `_`；仍禁止空格、`/` `\` `..` 与首尾点。文件夹名必须等于 frontmatter `name`。
- **D-058**：ChemClaw 内置 Skill 以完整目录入库（`SKILL.md` + `references`/`scripts`/附属文件），不是单文件提示词。当前内置含 Serenity 七个中文投研 Skills、Serenity `builtin-skills`（跳过 Linux 专用 `computer-use`，对齐 D-023）、以及 chem-cloud 系列 Skills。
- **D-059**：用户删除内置 Skill 后写入 `skills-settings.json` 的 `uninstalled_bundled`；后续启动 seed 不得回种。禁用（enabled）与卸载（删除）是不同操作。
- **D-060**：zip 上传安装须保留附属文件与扩展 frontmatter；仅在无 `source` 时注入 `source: uploaded`，不得用精简模板覆盖整份 `SKILL.md`。运行时依赖（Node/`fd`/`rg` 等）留给正式安装器任务，不在本阶段捆绑。

## 对话运行态（2026-08-04）

- **D-061**：离开设置页或其他对话不取消正在进行的 turn（后端本就不因 WS 断开而 interrupt）。前端同会话重选不得清空 `running`/`streaming`；异会话回切通过 `ready.running` 与中途事件恢复 Stop/进行中状态，并在 `turn_done` 后用落盘消息追齐最终回答。不采用多会话常驻多路 WebSocket。

## 对话并发（2026-08-05）

- **D-062**：跨会话允许并行 turn（与业界 ChatGPT/Claude/claw 一致）。不做全局「最多 N 路对话」软上限——定时任务、频道投递、self-wake 也占用 `_running_sessions`，对话数硬顶会误伤用户或文案不诚实。同会话仍 single-flight。并行安全靠每次 `stream()` 使用独立 OpenAI SDK/httpx 客户端（测注入客户端除外）；前端 WS 事件按绑定 `sessionId` 过滤，避免切会话后旧事件串台。

## 步骤组默认态（2026-08-05）

- **D-070**：对话步骤组（TurnGroup /「N 个步骤」）采用生命周期默认态，不做 Claude 式 Verbose/Normal/Summary 档位，也不默认展开 ThinkingBlock 或步骤 raw。无手动切换时：进行中（live 或工具仍为 `…`）默认展开；成功结算默认收起；工具失败，或结算后紧跟 tone=warn 的 notice（中断/错误/达迭代上限等）默认保持展开。用户点击步骤组标题后，该 TurnGroup 实例内手动覆盖优先到底。成功收起后的贴底跟随复用既有 FB-004，不另建 stick-to-bottom。改写上游 2026-07-14「运行中也默认收起」策略。（编号原误写为第二个 D-069，已更正为 D-070。）

## 模型提供商（2026-08-05）

- **D-071**：芯化和云 ApiHub 作为一等 OpenAI 兼容提供商接入设置「模型」页，拆成两个独立卡片并置顶：`apihub-cn` 显示 `ApiHub CN (chem-cloud)`（端点 `https://apihub.chem-cloud.cn/v1`），`apihub-intl` 显示 `ApiHub Intl (chem-cloud)`（端点 `https://www.tokenfoundryx.com/v1`）。画廊顺序为 CN → Intl → Claude → …；共用同一透明底云图标；密钥槽完全独立；端点预填且可在「自定义端点」中修改。CN 精选含 `deepseek-v4-flash`（主推荐）、`deepseek-v4-pro`、`glm-5.2`、`kimi-k3`；Intl 精选含 `gpt-5.6-sol`、`gpt-5.6-luna`（主推荐）、`gpt-5.6-terra`、`claude-sonnet-5`、`claude-opus-5`、`claude-fable-5`。新鲜安装 / 无已保存 `prefs.default_model` 时默认模型为 `apihub-cn:deepseek-v4-flash`；**不**迁移或覆盖已有用户 prefs。

## 产业链龙虾与过程 Skill（2026-08-05）

- **D-072**：内置智能体 `chain-lobster` 显示名「产业链龙虾」（无 Serenity 副标题）；化工产业链为锚，股票/宏观为同对话延伸。默认 Skill：七个中文投研 + `pdf`/`chart-image`/`file-search`/`multi-search-engine` + `market-analysis`/`stock-analysis` + `chem-price-daily`（D-078）。新建对话默认仍为 ChemClaw/`cowork`（Def1）。空态三条推荐通俗、无固定品名、用「稀缺」表述。Mermaid **M4**：全局安全+边标签+美观工具箱+反模板；「产业链层级测绘」补化工类型样式。过程库 **B1**：superpowers + mattpocock-skills-zh-CN 全量 bundled，不写入各智能体默认 `skills:`。澄清 **G4**：全局一句指针指向 `load_skill(grilling|grill-me|…)`，不另写先对齐长流程；默认交付文档版（Markdown）；可白话问是否要网页版。**（2026-08-07 修订）** 废止「D-077 自动后台烹饪」；网页版改为可选、先对齐再生成；**D-078** 恢复有 MD 时短气泡，并默认挂载 `chem-price-daily`。上传 zip 合成的 `serenity` 与内置龙虾并存（I1）。

## 长程任务上下文韧性（2026-08-05）

- **D-073**：长程任务禁止因上下文过大而阻塞用户交互。具体：
  - 压缩器（上下文摘要）失败时也不弹阻塞式 QUESTION；统一走自动 Trim 并继续。
  - 出站视图中（role=`tool`）的大回包统一裁剪到 40,000 字符；溢出完整内容落盘到会话产物文件，并在出站内容中给出可读路径指针。
  - 压缩后续跑依赖 OPE-27 `<compacted-history>`（LLM 摘要 + 机械 working_state + 用户原话 + 近期原文尾）；Trim 硬裁几乎无叙事摘要，模型应优先依赖该压缩块、工作区产物与必要时重跑工具。
  - **（2026-08-06 修订）** 撤销 `._chemclaw/task-progress.md` 引擎落盘与「查看任务进度」入口；侧栏 Progress/`todo_write` 保留为人看的计划 UI，不替代压缩记忆。

## Mermaid 失败补救（2026-08-06）

- **D-074**：Mermaid 语法/解析渲染失败时，对会话助手消息中的该 fenced 块自动就地修一次（窄通道、无工具、不代发用户气泡），并显示「正在修正图表…」；仍失败保留「修复图表」手动再试。已成功出图、源码过长、库加载失败不进模型修图。产物 MD 预览本期不写回文件。扩展 D-029 失败降级，不改 D-028/D-063。

## Agent Runtime 提速与体验（2026-08-06）

- **D-075**：在 OpenWorker 内核上渐进增强 Agent Runtime（不整体替换）。具体：
  - 产物缺失错误用稳定 key + GUI 中文区分「尚未生成 / 路径不匹配 / 不在工作区」。
  - 全局长程附录与产业链龙虾禁止用浏览器验证 `file://` 与 localhost；最终交付必须用 `[标题](artifact:相对路径)`。
  - 只读 MCP（名称启发式）标记 `risk_level=low`；授权通过后可与其他 low 工具并行；默认桥接超时 30s（可用 `CHEMCLAW_MCP_TOOL_TIMEOUT` / `COWORKER_MCP_TOOL_TIMEOUT` 覆盖；含 batch/export 等慢词保留 120s）。不绕过审批总闸。
  - **（运维备注 / A4）** chem-data-hub 等慢查询在 30s + 并行排队下易大面积 `TimeoutError`（`error` 常为空字符串，因 `str(TimeoutError())` 为空）。默认值暂不回滚；临时止血：设 `CHEMCLAW_MCP_TOOL_TIMEOUT=120` 后重启 sidecar。后续可再议同服务器串行 / 提高默认 / 超时取消飞行请求。
  - 出站 MCP/大 JSON 优先结构化摘要再落盘溢出；`extract_working_state` 记录 MCP 查询与结果预览。
  - Trim 回退摘要使用中文硬裁说明（不再指向任务进度文件）。
  - **（2026-08-06 修订）** 撤销任务进度 md 与 MCP 批次追加落盘；压缩记忆仅靠 `<compacted-history>` 等既有通道。
  - 里程碑 D（压缩态可见 / Plan-then-Act 时间线）见规格 `2026-08-06-chemclaw-agent-runtime-ux-design.md`，另案实施。

## 首包空窗 UX（2026-08-06；2026-08-07 修订）

- **D-076**：发送后至首条可见进展前，不得长期只显示「正在等待 Agent…」。有 `reasoning_delta` 时 live ThinkingBlock 在首包思考阶段默认展开（手动点击粘性覆盖）；无 reasoning 时用全局龙虾文案按前池→后池顺序约每 3s 轮播（中英对等；新等待从第 1 句重启）。压缩态仍用「正在压缩上下文…」。不纳入压缩细化 / 工具间隙 / Plan-then-Act（仍属里程碑 D）。规格/计划：`2026-08-06-chemclaw-first-token-wait-ux-*`。
- **D-079**：扩展 D-076 空窗至「用户答完 ask_user / 对齐补充之后」：`send` 与 `answerQuestion` 乐观 `running`；空窗锚点为最后一条 user 或已 resolve 的 question；答完选项后使用「收到反馈」文案池（收到啦… / 写进方案… / 对齐中… / 记下了继续~），首发仍用原「挠头」池。

## 报告网页版（2026-08-06；2026-08-07 修订）

- **D-077（已修订）**：废止「最终 md 交付后自动后台烹饪网页版」固定流水线（实测一锅出交互 HTML 失败率过高，不适合作为默认模块）。改为：
  - **主阅读**：文档版（Markdown）为默认主阅读面与存档。
  - **网页版为可选项**：交付 md 后可用白话询问是否要网页；文档旁可有「做网页版」按钮（仅注入用户意图，进入正常对话 turn）。默认不生成。
  - **流程**：先 grill 式一次一问对齐细节，用户确认后再在对话内生成 HTML；可反复修改。交互重量由对齐决定，默认偏简单精装；强控件仅在用户要求时做。
  - **形态**：只改提示词引导（不做独立 Skill 包）；拆除 turn 后入队、设置开关、`webpage_cook` WS 三态文案与「再下厨」API。
  - **预览沙箱**：**（D-078 修订）** 允许外链脚本与只读 GET；禁 POST 外泄（见 D-078）。
  - **短气泡**：**（D-078 修订）** 有最终 MD 交付时恢复强制短气泡（见 D-078）。
  - **非目标**：不做对话区内嵌大板 Artifact；不恢复硬同源校验器；不把网页当第二研究代理。
  - 修订 D-072 G4；原规格 `2026-08-06-chemclaw-report-webpage-cook-*` 标为已废止自动烹饪。

## 问答空态（2026-08-07）

- **D-083**：「问答」(`chat`) 空态不再使用「与 问答 畅谈」。标题覆盖为「有什么想问的？」（英：What can I answer?）；其余智能体仍用「与 {name} 畅谈」（D-067）。补三条无需工作区的轻量推荐（解释概念/缩写、对比材料或工艺、拆成追问清单），与 ChemClaw 交付物卡、产业链龙虾拆链卡区分；不改 chat 无 file/shell 能力边界。

## 代码工作区门禁（2026-08-07）

- **D-082**：项目作用域智能体（`family: code`，如「代码」）新建/切换对话时**不**立刻弹出「选择项目文件夹」。先展示空态（标题 + 推荐）；在用户发送、点击推荐任务、或点「选择文件夹」CTA 时再开门禁。`FolderGate` **必须始终可关闭**（无工作区时也不允许卡死）；关闭后回到空态，待发内容回填输入框。`newProject` 仍立刻开门禁。「新建项目」语义不变。不改为 ChemClaw 式自动 scratch。

## 智能体 surfaces 回弹（2026-08-07）

- **D-081**：遗留 prefs `show_chat` / `show_code`（设置 `surfaces`，默认关）不得把当前会话从「代码 / 问答」强制打回 ChemClaw/`cowork`。新建对话 ▾ 与智能体页的启用 / `surfaced` / 标星默认（D-067）是唯一选择器可见性来源。前端删除「hidden surface → switchAgent(cowork)」副作用；后端 surfaces API 本轮保留、可后续清理。

## 默认智能体空态（2026-08-07）

- **D-080**：ChemClaw/`cowork` 新对话空态去掉 OpenWorker 遗留的 HubSpot、GitHub+Slack 连接器门控任务卡。三条推荐改为化工知识工作向：研究备忘录、近期价格与走势要点、阅读本地文件夹提炼要点；lede 改为化工研究/分析口吻。共用主标题「与 {name} 畅谈」不变（D-067）。产业链龙虾空态仍按 D-072；prefill 走 i18n 中英对等。

## 短气泡、价格与 HTML 预览沙箱（2026-08-07）

- **D-078**：在 D-077 可选网页版之上：
  - **短气泡**：助手回复含最终 `[标题](artifact:….md)` 时，气泡仅结论若干句 + 要点列表 + 文档链接；全文以右侧文档版为准。
  - **价格**：产业链龙虾默认挂载 `chem-price-daily`；化工品研究可取价时用 MCP（如 `get_price_trend`）取数，**MD 写价格表**；用户要网页版时用同一序列画**可悬停交互走势图**（可用 CDN 图库）；无数据则注明，禁止编造。
  - **预览沙箱**：允许外链 `<script src=https>` 与 CSP `script-src https:`（Chart.js 等）；`fetch`/`XHR` 仍仅 GET/HEAD；禁止把本地报告 POST 外泄。深度研究仍走对话 MCP/技能，网页负责展示与轻量只读刷新。
  - 修订 D-072 默认 Skill 列表与 D-077 沙箱/短气泡表述。

## 云连接（2026-08-07）

- **D-084**：试用与 ChemClaw V1 默认关闭上游 OpenWorker 云登录（`CLOUD_SIGNIN_ENABLED=false`）。隐藏侧栏/Onboarding/连接页登录按钮与 Persona Gallery；`POST /v1/cloud/login` 与 managed connect / gallery API 硬拒绝且不打开浏览器。手动 Token/PAT 与 ApiHub 模型不受影响。芯化和云自有 Auth + OAuth broker 就绪后再改端点并打开开关。对齐 D-003 / D-007；不改变 D-002 本地优先边界。

## 本机资料（2026-08-07）

- **D-085**：左下角账号行使用与云登录无关的本机资料：可编辑显示名（默认「本机用户」/ Local user）与可选本地图片头像（JPEG/PNG/WebP，≤2MB，存于状态目录 `local-profile/`）。设置 → 通用提供「本机资料」卡片；账号菜单「编辑资料」打开设置。云关闭时不再显示「未登录」。对齐 D-002 / D-084。

## 销售增长智能（2026-08-07）

- **D-086**：ChemClaw 面向芯化和云的首要产品用途是**外贸拓客、内贸拓客、商机发现与销售转化**；化学、研究和报告能力用于增强产品识别、证据、合规与成交质量，不作为产品主轴。首条销售智能纵向链路确定为“具体产品/SKU + 目标国家 → 有主体和业务证据的候选客户 → 双评分 → 下一步动作”。
- **D-087**：外贸拓客采用“深工作流 + 稳定能力模块”：一名 `export-sales-lobster` Agent、一个主 Skill `chem-export-prospecting`，以及 `chem-product-intelligence`、`chem-buyer-discovery`、`chem-company-qualification`、`chem-lead-ranking` 四个能力 Skill。V3.2 的同类薄 Skill 按规格合并，不为每个步骤或数据源创建用户可见 Skill。
- **D-088**：搜索结果不是 Lead。Qualified Lead 必须经过主体归一、企业角色和业务相关性核验；专业分销商/贸易商是否保留由 ICP 决定，货代/物流等噪声单独识别。排序同时展示 `Lead Fit Score` 与 `Evidence Confidence`；评分由版本化确定性规则计算，未知不等同负面，所有强结论必须能追溯到 `EvidenceItem`。
- **D-089**：外部 API 位于平台 Tool/Provider 层，不嵌进 Skill；`public-apis` 只作发现目录。首条链路只要求现有网页检索/读取、企业官网证据、PubChem 辅助与用户约束，GLEIF 可选；Comtrade、TED/SAM、SEC、USAspending、海关与化工社能力按业务阶段逐个审计接入。来源型 API 不自动变成 Skill。
- **D-090**：V3.2 压缩包作为需求、风险规则和 Eval 种子，不作为可直接执行的总计划。本地化工社/K-Dense 科研 Skill 不批量内置；逐包完成价值、上游版本、许可证、脚本/网络、依赖、兼容性、中文化、权限、测试和回退审核。核心销售 Skill 首版不引入 RDKit、Datamol、TimesFM 等重型依赖。完整规格见 `docs/superpowers/specs/2026-08-07-chemclaw-sales-growth-intelligence-design.md`。
- **D-091（2026-08-07）**：用户明确授权实现**首个外贸拓客内置能力包**（不等于批准内贸/商机/转化/Provider 全阶段）。交付范围：内置 Agent `export-sales-lobster`（「外贸拓客龙虾」）+ `chem-export-prospecting` / `chem-product-intelligence` / `chem-buyer-discovery` / `chem-company-qualification` / `chem-lead-ranking`；默认智能体仍为 `cowork`，新 Agent 默认禁用、用户可在「智能体」页启用；不接外部 API、不自动发邮件、不写真实 CRM；权限与审批不变（只读检索走现有工具权限，发送/外部写入须审批）；`Lead Fit` 与 `Evidence Confidence` 由版本化确定性脚本计算；`SessionManager` 经 `skill_dirs` 真实 `load_skill`；证据 locator 拒绝 `task-provided:` / `unknown:` / `placeholder:` 占位符。Pack Schema 的 Qualified 门禁弱于评分脚本，**以 `score_lead` 为权威**。`seed_bundled_skills` 对已存在同名目录不自动升级。
- **D-092（2026-08-07）**：用户明确授权实现**内贸拓客纵向链路内置能力包**（不等于批准商机雷达/转化/国内 Provider）。交付：内置 Agent `domestic-sales-lobster`（「内贸拓客龙虾」）+ 主 Skill `chem-domestic-prospecting`；复用 `chem-product-intelligence` / `chem-buyer-discovery` / `chem-company-qualification` / `chem-lead-ranking`；默认仍为 `cowork`，新 Agent 默认禁用；国内规则（中文查询、园区/工商公开证据、统一社会信用代码优先、噪声排除、岗位级联系）写入主 Skill references；不挂 `chem-newbiz-lead`；不接国内工商/海关 API；不自动外发；权限与占位 locator 拒绝与 D-091 一致。计划见 `docs/superpowers/plans/2026-08-07-chemclaw-domestic-sales-builtin-pack.md`。
- **D-093（2026-08-07）**：用户明确授权实现**商机雷达内置能力包首包**（不等于批准 TED/SAM/Comtrade/海关 Provider 或销售转化）。交付：内置 Agent `opportunity-radar-lobster`（「商机雷达龙虾」）+ `chem-opportunity-radar` + `chem-opportunity-scoring`（`chem-opportunity-fit@1.0.0`，权重 25/20/25/15/15）；复用 `chem-product-intelligence` 与 `chem-company-qualification`；默认仍为 `cowork`，新 Agent 默认禁用；信号须可回溯来源，口述无来源保持 `NeedsReview`；不默认挂载 `chem-newbiz-lead` / `chem-inquiry-feed`；不接外部招标/询盘 API；不自动外发；占位 locator 拒绝与 D-091 一致。计划见 `docs/superpowers/plans/2026-08-07-chemclaw-opportunity-radar-builtin-pack.md`。
- **D-094（2026-08-07）**：用户明确授权实现**外贸销售转化内置能力包首包**（不等于批准报价数学、SMTP Provider、发送按钮或客户清单工作台）。交付：内置 Agent `export-engagement-lobster`（「外贸转化龙虾」）+ `chem-sales-engagement` + `chem-sales-quality-check`（`chem-sales-quality@1.0.0`）；复用 `chem-product-intelligence`；默认仍为 `cowork`，新 Agent 默认禁用；草稿 ≠ 发送；无可靠邮箱时只出岗位策略与补证；不接邮件 Provider；不自动外发/写 CRM；占位 locator 拒绝与 D-091 一致。计划见 `docs/superpowers/plans/2026-08-07-chemclaw-export-engagement-builtin-pack.md`。
- **D-095（2026-08-09）**：用户明确授权实现**首个领域数据 Provider 首包**：PubChem 化学身份（`ChemicalIdentityProvider` / Tool `lookup_chemical_identity`），平台层 `coworker/chem/`，对齐 `coworker/web/` 模式；免密钥、只读；Fixture 契约测试为主，CI 不依赖外网；`chem-product-intelligence` 仍用本地 `cas.py` 做格式/校验位，冲突/歧义保持 unresolved；**不**推断商业应用或采购意图。本决策**不等于**批准 GLEIF、TED/SAM、Comtrade、SMTP、报价数学或数据源 GUI。计划见 `docs/superpowers/plans/2026-08-07-chemclaw-pubchem-identity-provider.md`。
- **D-096（2026-08-09）**：用户明确授权实现**GLEIF 法定主体 Provider 首包**（`LegalEntityProvider` / Tool `lookup_legal_entity`），平台层 `coworker/entity/`，镜像 PubChem 模式；免密钥、只读；Fixture 契约测试为主，CI 不依赖外网；`chem-company-qualification` 用 evidence locator 承载 LEI（`government_registry`），不强制改 entity Schema；歧义/未命中/失败保持 `NeedsReview`/未决，不得编造 LEI；**不**接国家登记、关系树、制裁产品化、TED/Comtrade/SMTP/报价或数据源 GUI。计划见 `docs/superpowers/plans/2026-08-09-chemclaw-gleif-legal-entity-provider.md`。
- **D-097（2026-08-09）**：用户明确授权实现**询盘转报价内置首包**：平台确定性 Tool `calculate_quote`（`coworker/quote/`）+ Skill `chem-inquiry-to-quote`（Inquiry / QuoteDraft / QuoteRun）；挂到现有 `export-engagement-lobster`（不新建龙虾）；缺量/缺价 → `NeedsReview`，不编造单价；草稿 ≠ 发送；**不**接 `chem-inquiry-feed`/`chem-quote-monitor` MCP、SMTP、发送按钮或 CRM。计划见 `docs/superpowers/plans/2026-08-09-chemclaw-inquiry-to-quote-builtin-pack.md`。
- **D-098（2026-08-09）**：用户批准销售主线队列后实现**客户清单工作台首包**：平台 Tool `format_lead_list`（`coworker/leads/`）+ Skill `chem-lead-list`；挂外贸/内贸拓客龙虾；GUI 主导航增加「客户清单」（修订 D-006），支持导入 LeadList JSON、导出 CSV、本地标记可联系/待补查/排除与备注；**不**显示发送/CRM 按钮。SMTP 与 TED/Comtrade/国内登记仅落盘后续计划，不在本决策内实现。计划见 `docs/superpowers/plans/2026-08-09-chemclaw-lead-list-workbench.md`。
- **D-099（2026-08-09）**：用户点名实现**SMTP 发送审批闭环首包**：**不**新建 `coworker/mail/`；复用 Email 连接器 `email_send` + SecretStore `email:default` + 现有审批卡；发送相关错误中文化；外贸转化龙虾/`chem-sales-engagement` 仅在 `ready_for_human_send` 且用户明确要求发送时可调用 `email_send`；对话 Transcript 在助手文本含 `ready_for_human_send` 时显示「提交发送审批」CTA；**禁止**自动外发；客户清单页仍无发送按钮；不接 CRM/TED/国内登记。计划见 `docs/superpowers/plans/2026-08-09-chemclaw-smtp-send-approval.md`。
- **D-100（2026-08-09）**：用户批准销售主线队列后实现**国内登记 Provider 首包**：`CnRegistryProvider` + `RoutingLegalEntityProvider`；扩展 `lookup_legal_entity`（`query_type=uscc|auto|…`，返回 `uscc`）；USCC 校验位；SecretStore `cn_registry:default`（`base_url` 必填才联网）；Fixture 契约测试；Skill 仅文档接线；**不**接 TED/Comtrade/海关/爬虫/CRM。计划见 `docs/superpowers/plans/2026-08-09-chemclaw-cn-registry-provider.md`。
- **D-101（2026-08-09）**：用户批准「本机点检 → TED」队列后实现**TED TenderProvider 首包**：平台 `coworker/tender/`（`TedProvider` + Tool `search_tenders`）；TED Search API v3 免密钥 POST；结果映射为 `OpportunitySignal`（`ted:<publication-number>`）；Fixture 契约测试；挂商机雷达龙虾 / `chem-opportunity-radar` 文档接线；禁止伪造 TED 编号；**不**接 Comtrade/CRM/SMTP。计划见 `docs/superpowers/plans/2026-08-09-chemclaw-ted-tender-provider.md`。
- **D-102（2026-08-09）**：用户点名实现**客户清单进阶 UX**：`LeadsWorkbench` 行展开（匹配原因/关键证据/下一步/排除原因）；「继续补查」「调整 ICP 并重评」经 `requestLeadFollowup` 注入对话意图并切回会话；导入 JSON 若含 `run_id`/`stage`/`budget` 显示断点只读条；**仍无**发送邮件与 CRM 按钮；不静默改分、不自动重跑拓客。计划见 `docs/superpowers/plans/2026-08-09-chemclaw-lead-list-advanced-ux.md`。
- **D-103（2026-08-09）**：用户点名实现**UN Comtrade TradeFlowProvider 首包**：平台 `coworker/trade/`（`ComtradeProvider` + Tool `lookup_trade_flow`）；SecretStore `comtrade:default`（`api_key` 必填）；Fixture 契约测试；挂外贸拓客龙虾 / `chem-export-prospecting` / `chem-product-intelligence` 文档接线；返回国家/HS 汇总 + 非买家警告；无密钥中文错误；**禁止**把贸易流行当作成交买家；**不**接 CRM/海关全量/买家爬取。计划见 `docs/superpowers/plans/2026-08-09-chemclaw-comtrade-provider.md`。
- **D-104（2026-08-10）**：用户授权实现**化工多平台内容重构内置能力包 M1**：内置 Agent `platform-rewrite-lobster`（「化工内容重构龙虾」）+ `chem-rewrite-brief` / `chem-platform-rewrite` / `chem-content-policy` / `chem-content-quality-check`；`RewriteBrief` 事实合同；确定性 `scan_content.py` / `check_content.py`；第一期平台小红书/抖音/X；默认仍为 `cowork`，新 Agent 默认禁用；不自动发帖/登录；仅改写时不主动联网补事实；门禁最高 `ready_for_publish_review`；**不等于**批准 hook-cta 包、全量业务语料、词表热升级或桌面包验收（M2/M3）。计划见 `docs/superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md`。**同日补丁**：knowledge 会话自动挂载已安装 `skills` 目录为只读 root，排除出用户 `extra_roots` 持久化与可移除列表，修复 `read_file` 对 `resources_path` 的 `Path escapes allowed roots`。
- **D-105（2026-08-10）**：用户点名实现**HubSpot CRM 审批写入首包**：**不**新建 CRM Provider；复用连接器 `hubspot_log_note`（已有 EXTERNAL 审批）；对话门禁 `ready_for_crm_write` +「提交 CRM 写入审批」CTA（镜像 D-099）；未连接中文错误；转化龙虾/`chem-sales-engagement` 仅在门禁+用户明示时可调 `hubspot_log_note`；**禁止**首包主动调用 `hubspot_create_contact` / `update_object` / `create_task`；**禁止**自动写 CRM；客户清单页仍无 CRM 按钮；不等于批准 Close/买联系人。计划见 `docs/superpowers/plans/2026-08-10-chemclaw-hubspot-crm-write-approval.md`。
- **D-106（2026-08-10）**：用户点名实现**SAM.gov TenderProvider 首包**：平台 `coworker/tender/sam.py`（`SamProvider` + Tool `search_sam_opportunities`）；SecretStore `sam:default`（`api_key`）；结果映射 `OpportunitySignal`（`sam:<noticeId>`）；Fixture 契约测试；挂商机雷达龙虾 / `chem-opportunity-radar`；禁止伪造 noticeId；无密钥中文错误；**不**接海关/SEC/USAspending。计划见 `docs/superpowers/plans/2026-08-10-chemclaw-sam-tender-provider.md`。
- **D-107（2026-08-10）**：用户点名实现**化工多平台内容重构 M2**：`chem-hook-cta-pack`（按需 load，不插入四核心强制流水线）；12 条合成回归语料 + `REGRESSION_CORPUS.md` + pytest；skills 只读 root 集成测已入库（随 D-104 补丁）；默认仍为 `cowork`；**不等于**批准 M3（managed rules / 词表热升级 / 安装包内 `load_skill` 验收）。计划见 `docs/superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md`。
- **D-108（2026-08-10）**：用户点名实现**海关企业级文件 Provider 首包**：平台 `coworker/customs/`（`CustomsFileProvider` + Tool `filter_customs_importers`）；工作区 UTF-8 CSV；货代噪声过滤 + 进口商启发式评分；结果含「收货方≠终端买家」警告；Fixture 契约测试；挂外贸拓客龙虾 / `chem-export-prospecting` / `chem-buyer-discovery`；**不**接 XLSX/外部海关 API；**不**把候选直接标为 Qualified Lead；不等于批准买联系人/CRM 扩展。计划见 `docs/superpowers/plans/2026-08-10-chemclaw-customs-enterprise-file-provider.md`。
- **D-109（2026-08-10）**：用户点名实现**HubSpot 创建联系人审批 CTA**：新门禁 `ready_for_crm_create_contact` +「提交创建联系人审批」；复用连接器 `hubspot_create_contact`（已有 EXTERNAL 审批）；与 D-105 笔记门禁并列；转化龙虾/`chem-sales-engagement` 仅在门禁+用户明示且有可靠 email 时可调；**禁止**编造邮箱；**禁止**产品 CTA 打开 `hubspot_update_object` / `hubspot_create_task`；清单页仍无 CRM 按钮；不自动写。计划见 `docs/superpowers/plans/2026-08-10-chemclaw-hubspot-create-contact-approval.md`。
- **D-110（2026-08-10）**：用户点名实现**海关文件 XLSX 支持**：`CustomsFileProvider` / `filter_customs_importers` 可读工作区 `.xlsx`（`openpyxl` 只读首表）；与 CSV 共用列别名与评分；`.xls` 中文提示另存；Fixture 契约测试；**不**接外部海关 API。计划见 `docs/superpowers/plans/2026-08-10-chemclaw-customs-xlsx.md`。
- **D-111（2026-08-10）**：用户点名实现**化工社合集单包试点** `uncertainty-and-units`：自 `D:\化工社skills合集` vendor K-Dense MIT Skill 至 `coworker/skills/bundled/uncertainty-and-units`；中文 ChemClaw 边界；`audit_units.py` 标准库可用；可选 extra `uncertainty`（pint/uncertainties）；询盘转报价与外贸转化龙虾**可选** `load_skill`，不强制写入龙虾 `skills:`；**不**进入 Lead Fit/拓客评分；**不**批量内置其余合集包；**不**接官方 reaction-publisher / 化工社写反应 API；**不**将 NumPy/SciPy 写入核心依赖。计划见 `docs/superpowers/plans/2026-08-10-chemclaw-uncertainty-and-units.md`。
- **D-112（2026-08-10）**：用户批准对 `D:\化工社skills合集`（158 K-Dense zip）做**批量分流（Triage）而非批量安装**：产出 [`docs/chemclaw/HUAGONGSHE_SKILL_TRIAGE.md`](HUAGONGSHE_SKILL_TRIAGE.md) + JSON fixture；四档 DONE/P0/P1/P2/Skip；P0/P1 须用户确认后才逐包小任务实现；仍禁止一次复制多包进 `bundled/`；官方 `huagongshe-reaction-publisher` 不在合集内、另案评估。生成脚本 `scripts/_gen_huagongshe_triage.py`。
- **D-113（2026-08-10）**：用户授权在「连接」页新增第三栏 **「API 公开查询」**（英文 Public API lookups；路由 `/v1/public-api-lookups`）：列出本仓库 Skill/Agent 使用的全部平台 Provider（免密钥如 PubChem/GLEIF/TED/web_fetch、工作区海关文件、可选密钥网页搜索、需密钥 SAM/Comtrade/国内登记）；需密钥项可在 GUI 保存到 SecretStore，GET **永不回显** `api_key`；不伪装成连接器/MCP；不做通用 `/v1/secrets`；不含模型 Provider 与本地确定性 Tool（报价/清单格式化）。实现见 `coworker/public_lookups.py` + `PublicApiLookupsSection`。
- **D-114（2026-08-10）**：用户反馈卡片说明不足后，增强 **API 公开查询** 文案：每项增加做什么 / 谁在用 / 如何配置，以及 `docs_url` / `signup_url`（SAM→sam.gov、Comtrade→comtradedeveloper.un.org、可选搜索引擎申请页等）；国内登记写明须向贵司 IT/供应商要 `base_url`。不改密钥存储，不代申请密钥。
- **D-115（2026-08-10）**：确认 **SAM.gov / UN Comtrade 为境外可选增强**，非大陆刚需。API 公开查询卡片、未配置错误文案与商机/外贸龙虾默认路径改为优先 TED / 海关文件 / 网页搜索；未配密钥不以申请成功为门禁；不删除 Provider。探针备忘见 [`PUBLIC_API_PROBE_2026-08-10.md`](PUBLIC_API_PROBE_2026-08-10.md)。
- **D-116（2026-08-10）**：按 public-apis 短名单探针结果，接入**免密钥 VATComply** 平台 Tool `validate_eu_vat`（`coworker/vat/`）；挂企业核验 / 外贸与商机龙虾文档；列入 API 公开查询；Fixture 契约测试；**不**批量接入 Frankfurter/USAspending/World Bank；Tenders.guru 本机不可达、OpenSanctions 需密钥故不接。
- **D-117（2026-08-10）**：按**业务场景**筛选免密钥增强，而非「探针通过就全接」。本刀落地：`lookup_fx_rate`（Frankfurter→询盘转报价/转化龙虾）、`lookup_wikipedia`（MediaWiki→产品情报及外贸/内贸/商机龙虾）、巩固 `validate_eu_vat` 公开查询必显；新增 CATALOG⊇销售 Provider Tool 回归门禁。**延期** USAspending（非大陆日常拓客）、World Bank（宏观非买家）；仍不接 Tenders.guru / OpenSanctions。
- **D-118（2026-08-10）**：用户点名接入**化工社只读 API 首包**：平台 `coworker/huagongshe/`（`search_huagongshe` + `lookup_huagongshe_chemical`）；可选 Bearer `huagongshe:default`；「API 公开查询」可填 Token（永不回显）；挂 `chem-product-intelligence` 与外贸/内贸龙虾作化学证据补充；**禁止**进 Lead 评分；**不**接 `validate`/`create` 写反应、不装官方 reaction-publisher、不加 RDKit。契约见 https://huagongshe.com/api/agent-guide 。
- **D-119（2026-08-10）**：在 D-118 之上补齐**写反应首包**：`validate_huagongshe_reaction`（须 Token，不写库，无审批）+ `create_huagongshe_reaction`（须 Token、`Idempotency-Key`、`requires_approval=True`）；bundled Skill `chem-huagongshe-reaction`（中文边界编排，按需 `load_skill`，不强制销售龙虾 `skills:`）；公开查询文案标明校验/保存依赖 Token 与审批。仍**禁止**进 Lead 评分；**不**整包拷贝官方 SKILL、不加 RDKit/SVG、不接编辑/删除 API。
- **D-120（2026-08-11）**：澄清 D-118/D-119「不加 RDKit/SVG」= **禁止本机 RDKit 渲染与把 SVG 源码搬进模型上下文**；**允许**平台只读 Tool `fetch_huagongshe_svg` 经化工社公开接口拉取分子/反应 2D SVG，**完整写入会话工作区产物**（如 `huagongshe_assets/….svg`），Tool 回包仅元数据（路径、`public_url`、字节数等）。禁止用 `web_fetch` / shell 直连搬运 SVG 正文。交付用 `artifact:` 芯片或 Markdown 图链；仍**禁止**进 Lead 评分。
- **D-121（2026-08-11）**：上下文压缩硬裁用户提示中性化，并提高摘要二次成功率。Trim 成功时显示「上下文已自动精简以继续」（不再使用「摘要不可用」）；摘要失败打 `warning` 日志；第二次摘要尝试收紧 summarizer span（更短 tool-result clip / 更小 char budget）后再 Trim。不改变「失败不阻塞、自动 Trim 续跑」契约；不关闭压缩。与 D-073/D-075 一致；D-120 只减少 SVG 胀爆，不能单独消灭硬裁。
- **D-122（2026-08-11）**：四只销售龙虾（`export-sales-lobster` / `domestic-sales-lobster` / `opportunity-radar-lobster` / `export-engagement-lobster`）新对话空态改为专属 `SessionIntro` 三卡（lede + title/sub/prompt，中英 i18n），对齐拓客/商机/转化真实场景；不再落入代码向 `SUGGESTIONS`（跑测试套件 / 读项目概览 / 修失败构建）。标题仍用「与 {name} 畅谈」（D-067）；不改默认禁用、Skill、权限或 Provider。
- **D-123（2026-08-11）**：正式安装包运行态与遗留 OpenWorker 数据隔离。默认状态目录改为 Windows `%APPDATA%\\ChemClaw`、POSIX `~/.config/chemclaw`（`COWORKER_STATE_DIR` 仍可覆盖，开发态继续用 `.chemclaw-dev\\state`）。PyInstaller 必须把本 worktree 的 `coworker/skills/bundled/**` 与 `coworker/personas/builtin/**` 打入 sidecar；聊天记录永不打进安装包，只存在于状态目录。不自动迁移 `%APPDATA%\\coworker` 旧数据。
- **D-124（2026-08-11）**：上游 OpenWorker 选择性 backport Wave A（共同基线 `01b6f83`，参考 tip `9702c86`）。合入 #415 DNS connection pin、#416 Python 3.10 `tomli` fallback、#419 GUI CI `tsc --noEmit`、#417 GUI README/`lib.rs` 去 `platform/` 旧路径。禁止 `git merge upstream/main`；禁止 cherry-pick #471/#472 merge commit。#471 ask_user 与 #472 Memory 为 Wave B/C，须用户点名后按 [chemclaw-upstream-file-by-file-upgrade-plan-2026-08-11.md](chemclaw-upstream-file-by-file-upgrade-plan-2026-08-11.md) 局部移植。
- **D-125（2026-08-11）**：上游 #471 ask_user 2.0（Wave B）按文件计划 Task 4–5 局部移植到分支 `chore/upstream-ask-user-2026-08-11`：富选项（label/description/recommended/preview）、最多 4 题分组 stepper、`{"answer"}`/`{"answers"}` 结果形、旧字符串 options 与无 header/questions 的 Inbox JSON 兼容；channel 对 grouped 不发 buttons。GUI 文案走 `ask.*` i18n。高冲突文件禁止整文件覆盖。已合回 `chemclaw-clean`（用户点名）。
- **D-126（2026-08-11）**：上游 #472 Memory V1（Wave C）按文件计划 Task 6–9 局部移植到分支 `chore/upstream-memory-2026-08-11`：summary/index/`memory_read` → `MemorySettingsStore`+live 写闸+REST → Settings Memory 页/`memory_saved` Undo（全 i18n）→ CLI/TUI 同读 `memory-settings.json`。关=停写入；已有记忆仍注入新会话；user rules 与已知事实在会话启动时固定。禁止整文件覆盖 `agent.py`/`manager.py`/`app.py`/`App.tsx`/`SettingsView.tsx`/`Transcript.tsx`。合回 `chemclaw-clean` 须用户点名。
- **D-127（2026-08-12）**：用户授权实现 **HubSpot CRM 字段更新与任务创建审批 CTA**：门禁 `ready_for_crm_update_object` +「提交 CRM 字段更新审批」→ `hubspot_update_object`；门禁 `ready_for_crm_create_task` +「提交 CRM 任务创建审批」→ `hubspot_create_task`；均复用连接器既有 `requires_approval`；与 D-105/D-109 并列；须可靠对象 ID / 已确认跟进动作，禁止编造；任务工具不扩关联 API（已知联系人写入 `notes`）；清单页仍无 CRM 按钮；不自动写；不等于批准 Close/买联系人。计划见 `docs/superpowers/plans/2026-08-12-chemclaw-hubspot-crm-update-task-cta.md`。
- **D-128（2026-08-12）**：用户点名实现**化工多平台内容重构 M3**：`chem-content-policy` 词表拆为 `references/lexicon/managed/`（官方可按 `rule_version` 热升级）+ `user.csv`（用户覆盖/`action=suppress`，官方同步永不覆盖）；`scan_content` 合并两层并输出 `rule_set:{id,version}`；启动时 `sync_managed_lexicon` 在 `seed_bundled_skills` 之后仅同步 managed（兼容旧 `lexicon/base.csv` 迁移）；package-data / SkillLoader 路径验收；**不等于**已确认重打 NSIS（产物内 frozen `load_skill` 须用户再确认打安装包后补验）。计划见 `docs/superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md`。
- **D-129（2026-08-12）**：Context compaction 产品默认改为 **70%** 触发比例与 **100,000** tokens 上限（`coworker/compaction.py` `DEFAULT_*` + 设置页无键回退）；设置页仍允许调到最高 95% / 2,000,000。不迁移已写入 prefs 的本机旧值。目的：更早摘要，降低拖到爆窗后反复硬裁（「上下文已自动精简以继续」）。
- **D-130（2026-08-12）**：OPE-27 摘要可靠性首包采用「单次严格投影 + 分类诊断 + 确定性中间降级」，不立即增加多轮 map-reduce。摘要输入读取摘要模型 context window；未知模型按 32k，普通输入最多 24k tokens、紧缩重试最多 8k，并预留 3k 输出与至少 2k safety。`reasoning_content` 不得当作摘要正文；reasoning-only、空回复、输出截断、context overflow、限流、超时与其他 Provider 错误分别记录无正文 warning。保留既有 `compaction_model` Provider 路由；摘要等待默认 90s。两次失败后先生成确定性 continuity ledger，保留最近 todo、产物路径、命令状态、MCP 查询、助手结论、用户原话和近期原文；仍失败才最小 Trim。成功继续显示「上下文已自动压缩（较早轮次已摘要）」；非 LLM 降级继续显示「上下文已自动精简以继续」。canonical transcript 永不改写。
- **D-131（2026-08-13）**：默认智能体对外身份统一为 **ChemClaw**（对齐 D-003）。`coworker/agents/cowork.py` 的 `COWORK_INSTRUCTIONS` / `title` 改为自称 ChemClaw（不再 “You are a Cowork agent” / title Cowork）；前端 `personaScope` 与侧栏 fallback 对 `id=cowork` 显示 ChemClaw（不再 Coworker/协作助手）。内部路由 id 仍为 `cowork`；不改 Python 包名；不清洗 Code/Chat/Ops 提示词中的 coworker 措辞。
- **D-132（2026-08-17）**：会话 workspace **根目录 = 用户最终产物**（报告 Markdown 与其引用的图片等）；**`._chemclaw/` = 内部工作目录**（绘图脚本、中间 json/csv、过程图，默认 `._chemclaw/charts/`）。产物栏递归列举时继续跳过点目录；knowledge/ChemClaw 会话额外隐藏遗留顶层 `charts/`，Code 会话不隐藏。`artifact:` identity 为 workspace-relative；聊天里的 Windows 绝对路径仅当确实位于当前 workspace 内才安全相对化（`PureWindowsPath`，禁止 basename）。RightRail 展示全部产物，不再静默截断 16 条。不把扫描改成只看根目录；不取消 workspace escape。**（同日修订）** 会话 `workspace` 不得跟随 shell `cwd`；模型 `cd` 进 `._chemclaw/...` 后仍持久化 primary scratch。读取产物时若发现路径含 `._chemclaw`，截回该段之前的会话根并写回库。
- **D-133（2026-08-17）**：**Inline Chart 快路径（第一轮）**：聊天即时图用 fenced ```chart` + 受控 ChartSpec v1 + 浏览器 Chart.js（`ChartBlock`，仿 Mermaid）；流式 `renderCharts=false`。全局 `_INLINE_CHART_GUIDANCE`：普通聊天优先 inline chart，禁止仅为可视化而 shell/Node/npm/chart.mjs/chart-image。`chart-image` 仅静态导出（PNG/报告/附件）。本轮不做 Fast Router、不做 MCP→ChartSpec 确定性归一化（TODO 留在 guidance）。**（同日修订）** 解析器别名：`x.labels`→顶层 `labels`；`xLabel`/`x_label`/`x.title`/`x.label`→`xTitle`（权威形状仍为扁平 labels）。**（同日修订）** 多 series 色板改为 Okabe–Ito 改编期刊定性色序（首色 ChemClaw `#2563eb`，第二色朱红 `#D55E00`）。
- **D-134（2026-08-17）**：**行情回答默认附 inline 趋势图**：回答化工品近期价格/走势且 Tool/MCP 含可用时间序列（≥2 个日期点）时，同一条回复必须含价格表、简要要点，以及一条 ```chart`（ChartSpec v1 line）；数值与表一致；无序列或无数据则不强行出图。空态 `intro.task.price.*`、`_INLINE_CHART_GUIDANCE`、`chem-price-daily` 已对齐。仍不引入 `emit_chart_spec` / Fast Router；数值继续由模型从 Tool 结果抄入 ChartSpec。
- **D-135（2026-08-17）**：**Yahoo 非官方 OHLC + 蜡烛图**：第一方 `lookup_yahoo_ohlc`（Yahoo Chart API，免密钥，best-effort，非持牌行情；支持 `CHEMCLAW_HTTP_PROXY`）；ChartSpec 增加 `candlestick` + `ohlc[{o,h,l,c}]`（`chartjs-chart-financial`）；缺省缺写 `version` 时按 1；多标的 = 多块独立蜡烛图。化工现货仍走 chem-data-hub + line；禁止为拉 Yahoo 而 shell/curl。
- **D-136（2026-08-17）**：**Yahoo K 线短引用、禁止手抄 OHLC**：`lookup_yahoo_ohlc` 返回确定性 `chart_spec`；助手气泡内 ````chart` 只写 `from_tool`+`symbol`（可选 title）；GUI 按本轮 tool preview 回查出图。完整手抄 candlestick 若 labels/ohlc 长度不齐则按 `min` 前缀截齐兜底。化工现货 line 仍可手抄。
- **D-137（2026-08-17）**：**K 线国内配色（红涨绿跌）**：蜡烛图 `up`/`down` 对齐同花顺/文华习惯（红阳绿阴）；折线多 series 色板不变；不做空心阳线。
- **D-138（2026-08-17）**：**K 线走势阶段标注**：ChartSpec `candlestick` 可选 `stages[{start,end,tone,reason}]`；GUI 用 `chartjs-plugin-annotation` 画背景色带；高低价由前端从 OHLC 自动计算（全局极值 + 涨/跌段极值）。**不做方向箭头**（色带已够）。**阶段原因不常驻画布**：悬停详情在 **左预留栏**（`layout.padding.left`，不进入 `chartArea`），顺序为 **日期 → 开高低收 → 阶段性区间/驱动**；**单击 K 线固定详情**（再点切换，Esc/移出取消），固定后可任意移动并滚动读完驱动；十字线锁在固定 bar。**不用浮动磨砂卡**；Chart.js OHLC tooltip 关闭。**图表全屏**（更大字号左栏、默认约 180 根窗）；极值 label 用 yAdjust + 上下 padding，防裁切；K 线提示含拖动/滚轮与固定说明。Yahoo short-ref 可同级附带 `stages` 并 merge，仍禁止手抄 OHLC。普通查价可不附 stages；原因须 grounded 本轮工具/检索。不做空心阳线/成交量副图/自动分段。
- **D-139（2026-08-17）**：**手抄 OHLC 数组兼容**：`parseOhlcBar` 接受 `[o,h,l,c]` 四元组与 `{o,h,l,c}`/`open|high|low|close` 对象，统一归一成对象；长度≠4 或非有限数仍报错。Yahoo 路径仍优先 short-ref（D-136）。
- **D-140（2026-08-17）**：**K 线默认最新窗口 + 滚轮缩放/拖动**：蜡烛图默认 X 窗为最新 **90** 根（不足则全显）；`chartjs-plugin-zoom` 支持滚轮缩放与左右拖动（仅 X，limits 锁在数据范围）；可见区 OHLC 高低驱动 Y 自适应（忽略全序列 yMin/yMax）；`offset: false` 收紧左右空白；X 刻度仍为连续 index→日期均匀抽样，不改成只标转折点。line/bar 本刀不动。
- **D-141（2026-08-17）**：**现货图十字线 + 融文铬层**：`line`/`area`/`bar` 与 K 线共用左栏详情 + 按 X 吸附十字线 + 单击固定；挂载默认最新价，移出/Esc 回退最新（左栏不空）；成功态去掉「图表/源码」切换与灰外框，仅悬停显示全屏图标按钮；芯片式操作提示。`scatter` 仍用 Chart.js tooltip。不改 ChartSpec。
- **D-142（2026-08-17）**：**全屏不透 + 现货区间/焦点**：Chart lightbox 近不透明遮罩（不用弱 `--scrim`）+ lightbox 内强制实底；`line`/`area` 支持 `stages` 色带与左栏驱动；可选 `focusLabel` 挂载默认固定到询问日否则最新且 pinned；短内容左栏垂直居中。guidance + `chem-price-daily`：默认拉够历史（约 ≥60 交易日/月线 ≥12 点），短问也出长图+焦点。不改 MCP 工具代码。
- **D-143（2026-08-18）**：**行情图操作提示悬停才显**：对话内操作芯片在**画布上方**固定 32px 槽位；平时透明、悬停/聚焦淡入，不叠在 Chart.js 标题/图例上，也不因浮现改变图画布位置；全屏 lightbox 内仍常显于顶部。不改 ChartSpec / 交互模型。
- **D-144（2026-08-18）**：**行情图左栏详情始终垂直居中**：K 线/现货左栏卡片固定左中（`top: 50%` + `translateY(-50%)`），不再仅短内容居中、长内容贴顶；超高内容仍在卡内滚动。不改 ChartSpec。
- **D-145（2026-08-18）**：**去掉 Wind 金融 Skill 调用路径**：ChemClaw 当前**没有**可用 Wind 工具，且不注册该商业金融语料工具。`market-analysis` / `stock-analysis` / `macro-analysis` 与 `chain-lobster` **不得再出现**该幽灵工具名；行情用已注册 `lookup_yahoo_ohlc`，公告/新闻用 `web_search`/`web_fetch`；Web 不得伪装成结构化金融库；缺精确指标写 unavailable，禁止猜测。产业链龙虾金融为验证层、非单点故障。启动时窄刷新已安装且仍含旧幽灵工具名的上述三份 `SKILL.md`。国内结构化行情留给未来 `coworker/cn_market/`（另案；不把 AKShare 打进核心依赖）。
- **D-146（2026-08-18）**：**行情图左栏价格不截断**：左栏详情 KV 改为上下排（名称可折行、价格 `nowrap`）；对话内轨宽 188 / 面板 172，全屏 208 / 192，避免长系列名把上千价水平裁成上百假象。不改 ChartSpec。
- **D-147（2026-08-18）**：**左栏空白收紧 + OHLC 色说明**：面板改为 `width: fit-content`（min 112 / max 172；lightbox min 128 / max 192），短内容不再固定撑满；OHLC 用左右排、系列长名仍上下排。左栏开/收颜色按**当根** `收盘>=开盘` 红否则绿（与昨收无关）；最高固定红、最低固定绿（D-137）。不改 ChartSpec / 轨宽常量。
- **D-148（2026-08-18）**：**国内行情层地基（Run 1）**：授权 D-145 另案的第一段，落地 `coworker/cn_market/`（models / errors / source policy / cache / A 股与化工期货 symbol / 交易日历 / fake provider）。免登录只读；AKShare **不**进入 core/`pyproject.toml`；缓存只写 `state_dir()/cn_market/cache`，不写仓库；单测禁止网络。tick/L2 固定 `unsupported_keyless`。不注册 structured tools，不改 `coworker/agent.py` / ChartSpec / Yahoo 路由。真实 A 股/期货 adapter 属后续独立 Run。
- **D-149（2026-08-18）**：**A 股公开 adapter（Run 2）**：`PublicCNStockProvider` 用现有 urllib 拉新浪行情/JSONP K 线/财报、东财龙虎榜/北向历史、上交所两融汇总。不引入 AKShare/pandas/mini-racer。报价走 `hq.sinajs.cn`（不用东财快照）。日线用 `CN_MarketDataService.getKLineData` scale=240（不用需 V8 的 klc_kl.js）；qfq/hfq 目前回退为未复权并 warning。北向持股与财务分析指标保持 `source_unavailable`。Structured tools：`lookup_cn_stock_quote/ohlc/minute/financials/feature` **未**注册进 `agent.py`。GUI short-ref 仍只认 Yahoo。
- **D-150（2026-08-18）**：**国内期货公开 adapter（Run 3）**：`PublicCNFuturesProvider` 用 urllib 拉新浪期货 L1 / 日线 / 分钟，不加 AKShare、不改 `agent.py`。L1 用 `Market_Center.getHQFuturesData`，node 为 `qihuohangqing.js` 品种标记（甲醇=`zc_qh` 郑醇，不是 `MA0`）；本地按持仓量选主力并标 `series_method=dominant_by_open_interest`。新浪 `MA0`/`PG0` 连续只标 `upstream_sina_continuous`。K 线 JSONP：`InnerFuturesNewService.getDailyKLine` / `getFewMinLine`。`market_depth=L1`，不称 L2。理论保证金公式级计算器，必须声明非期货公司占用。Tools：`lookup_cn_futures_quote/ohlc/minute/l1`、`calculate_cn_futures_margin` **未**注册。GUI short-ref 仍只认 Yahoo。Tick/L2 仍 `unsupported_keyless`。
- **D-152（2026-08-18）**：**国内行情 Agent 接线（Run 5）**：默认对话注册 11 个 `lookup_cn_*` / `calculate_cn_futures_margin`。路由：大陆 A 股/财报/龙虎榜/两融/北向历史 → CN stock；国内期货 → CN futures；上市期权 → `lookup_cn_option_market`；美股/港股/全球期货 → `lookup_yahoo_ohlc`。CN 结构化失败禁止 Yahoo/网页探测补同一行情。GUI short-ref 认 `lookup_cn_stock_ohlc` / `lookup_cn_futures_ohlc` / `lookup_cn_option_market` 等（symbol 可产品码对合约）。API 公开查询新增 A 股/国内期货/期权三张免密钥卡。HARD STOP D `hard-stop-d-legacy-tool-schema-snapshot.json` 随注册集更新。Tick/L2 仍 `unsupported_keyless`（Run 4X 未授权）。不加 AKShare，不改 `pyproject.toml`。
- **D-153（2026-08-18）**：**现货折线缩放/拖动对齐 K 线**：`line`/`area` 复用 D-140 交互（最新 90 点窗、X 向滚轮缩放与拖动、可见区 Y 自适应、X 刻度 `maxTicksLimit: 8`）。可见点超过 24 时隐藏圆点。极值标签画在点上方，并加右侧/底部 canvas padding，避免最低价压住日期、最右价格显示不全。`bar`/`scatter` 与 ChartSpec 不动。
- **D-154（2026-08-18）**：**行情图极值标签分侧 + 留白 + 去重**：K 线与现货 `line`/`area` 最高价标点上、最低价标点下；`CHART_PAD_TOP=32` / `CHART_PAD_BOTTOM=20`；可见区 Y `padRatio=0.12`。`dedupeExtremes` 保留全局高低，丢弃同 kind 且 `|Δindex|<5` 的阶段极值，避免相邻最低价叠字、最高价被裁切。不改 ChartSpec。
- **D-155（2026-08-18）**：**小图不标极值、全屏才标**：inline `candlestick`/`line`/`area` 不画高低价标签（色带仍可画）；lightbox 只标可见 X 窗口的全局最高与最低，zoom/pan 时刷新。小图收回为标签预留的顶/底/右 padding。`bar`/`scatter` 与 ChartSpec 不动。
- **D-156（2026-08-18）**：**阶段方向重算 + 驱动只写原因**：模型仍给 `start`/`end`/`reason`；GUI 用区间整体涨跌幅覆盖 `tone`（横盘 |r| 不得 ≥ 任一涨/跌段）。`reason` 为言简意赅的主导因素，禁止复述走势、禁止具体价格；展示层 `sanitizeStageReason` 去价位，空则隐藏驱动行。`MAX_STAGE_REASON_LEN=80`。guidance 与 `chem-price-daily` 已对齐。不做自动分段。
- **D-157（2026-08-18）**：**短引用中文品种匹配**：`OhlcSeries` 回传可选 `name`/`aliases`；期货 provider 从 `CNFuturesSymbol` 填入（橡胶/天然橡胶→RU）。GUI `payloadMatchesSymbol` 对规范码、中文名、别名精确匹配，禁止 substring。guidance 优先抄工具 `symbol`。不在 TS 复制品种表。不加 AKShare，不改 `pyproject.toml`。
- **D-158（2026-08-18）**：**阶段色带互斥**：`exclusiveStageRanges` 与悬停 last-wins 对齐；每根 K 线只属一段；相邻色带 `±0.5` 贴齐，半透明不再叠成紫/褐。左栏走同一裁切。月 K 上日频 stages 吸附后同一 `YYYY-MM` 只一种 tone。不改 ChartSpec / 不做自动分段。
- **D-159（2026-08-18）**：**短引用直播 sidecar + 全会话回查**：`TOOL_FINISHED` 对含 `chart_spec` 的结果下发 sidecar（`chart_spec`/`symbol`/`plot_status`/可选 name/aliases），不加大步骤卡 300 字 preview。GUI `chartPreview` 优先于截断 preview；`yahooChartToolsFromItems` 扫全会话。short-ref 认 `args.symbol`。错误区分无工具结果、preview 截断、上游 `error`。GUI 不直连 Yahoo。不加 AKShare。
- **D-160（2026-08-18）**：**未指定周期默认日线**：问股票/期货/上市期权价格且未点名周期时，出日线（CN `lookup_*_ohlc` / Yahoo `interval=1d` / 期权 `action=daily`）。禁止默认走 `lookup_cn_*_minute` 或 Yahoo `1wk`/`1mo`。回看仍约 60 个交易日（`range=3mo`）；「最近一年」未说周/月/年线 = `range=1y` + 日线。CN 无周/月/年 K，禁止本地重采样冒充；Yahoo 无年线 interval，点名年线用 `1mo` 并说明。化工现货 `chem-price-daily`、ChartSpec、GUI 不动。不在工具层覆盖用户已声明的 `interval`。

## 协作治理

- **D-057**：项目事实沉淀在 Git 跟踪的本地文档，而不是依赖聊天历史。
- **D-058**：每个新任务先读 `AGENTS.md`、项目状态、规格、决策和当前计划，再汇报状态。
- **D-059**：一次只执行一个可独立验收的小里程碑；修改、测试、提交和文档更新形成闭环。
- **D-060**：合并 `main`、构建正式安装程序、管理员权限安装和写入真实外部数据需要用户明确确认。
