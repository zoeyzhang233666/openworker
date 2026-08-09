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

## 协作治理

- **D-057**：项目事实沉淀在 Git 跟踪的本地文档，而不是依赖聊天历史。
- **D-058**：每个新任务先读 `AGENTS.md`、项目状态、规格、决策和当前计划，再汇报状态。
- **D-059**：一次只执行一个可独立验收的小里程碑；修改、测试、提交和文档更新形成闭环。
- **D-060**：合并 `main`、构建正式安装程序、管理员权限安装和写入真实外部数据需要用户明确确认。
