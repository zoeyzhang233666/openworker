# ChemClaw 项目控制台

## 当前状态

- **D-187：双模式停止 + 主任务超时可恢复（2026-08-21）**：用户 GUI/HTTP `immediate` 立刻硬停；智能体/系统 `wrap_up` 先催写部分报告（~90s）再 force；流式 read=300s；timeout 且本轮有工具产物时 EF salvage。聚焦 background/subagent/EF/model_errors/compaction/provider kwargs：**54 passed**。规格/计划：[`D-187 design`](../superpowers/specs/2026-08-21-chemclaw-dual-mode-stop-timeout-design.md) / [`plan`](../superpowers/plans/2026-08-21-chemclaw-dual-mode-stop-timeout.md)。**须重启 sidecar** 后验证：右栏停止立刻停；模型 `background_task_stop` 出现 wrap-up；长轮超时更少裸英文。
- **D-186：思考同槽位交接防空白（2026-08-21）**：修 D-183 未覆盖的真空白——live 思考不再因早期 `assistant_delta`/`!streaming` 整块卸载；hold 间隙与 `assistant_message` 后同槽位收起保留「思考过程」；Turn 已挂 reasoning 时外挂让位避免双份。GUI `thinkingSlot` + firstTokenWaitCopy + ThinkingBlock + Transcript：**67 passed**。规格/计划：[`D-186 design`](../superpowers/specs/2026-08-21-chemclaw-thinking-slot-handoff-design.md) / [`plan`](../superpowers/plans/2026-08-21-chemclaw-thinking-slot-handoff.md)。
- **D-185：Markdown LaTeX 公式渲染（2026-08-21）**：共享 `Markdown.tsx` 接入 `remark-math` + `rehype-katex` + 直依赖 `katex`；对话最终回答与 RightRail `.md` 产物预览同时支持 `$…$` / `$$…$$`；坏公式 `throwOnError: false`；不成对 `$100` 保持文本。不改 prompt、ThinkingBlock、HTML 网页版。GUI `Markdown.test.tsx`：**19 passed**。规格/计划：[`D-185 design`](../superpowers/specs/2026-08-21-chemclaw-markdown-latex-design.md) / [`plan`](../superpowers/plans/2026-08-21-chemclaw-markdown-latex.md)。
- **D-184：研究套利强制委派 + LLM 超时可重试（2026-08-21）**：研究 Scenario 命中后 AGENT→DEEP_RESEARCH；父面去掉行情 MCP/CN 工具（合成写工具 + web + subagent 控制保留）；`make_execution_profile(DEEP_RESEARCH)` 尊重投影 allowlist；APITimeout 计入流式重试 + 中文 `llm_api` 分层错误。聚焦 scenario/planner/harness/model_errors/router/prompt/execution_profile：**104 passed**；扩展 market/subagent/EF/projection：**55 passed**。规格/计划：[`D-184 design`](../superpowers/specs/2026-08-21-chemclaw-research-delegate-force-design.md) / [`plan`](../superpowers/plans/2026-08-21-chemclaw-research-delegate-force.md)。**须重启 sidecar** 后用「研究沥青期货产业链上下游套利怎么做」复验右栏 ≥2 research。
- **D-183：思考结束收起连续可见（2026-08-21）**：live「正在思考」结束后改为收起「思考过程」标题（不整块消失）；settled thinking-only 间隙继续轮播规划等待文案；TurnGroup 上方保留可展开 reasoning。D-178 live forceOpen 不变。GUI `firstTokenWaitCopy` + `FirstTokenWaitLabel` + `ThinkingBlock` + `Transcript`：**61 passed**。规格/计划：[`D-183 design`](../superpowers/specs/2026-08-21-chemclaw-thinking-collapse-continuity-design.md) / [`plan`](../superpowers/plans/2026-08-21-chemclaw-thinking-collapse-continuity.md)。
- **D-182：研究路径剩余英文提示纠偏（2026-08-21）**：补丁 D-180——汉化 `start_subagent`/`background_task_*`/`explore`、技能目录头与 `load_skill`/`search_skills`、`<market-scope-policy>`、以及 research/explore/worker Profile instructions。GUI 仍透传 upstream reasoning。聚焦 `test_prompt_language_zh` + market_intent + emergency/skills/projection：**52 passed**。**须重启 sidecar** 后用「研究甲醇期货产业链上下游套利怎么做」复验思考语言。
- **D-181：化工行情 Web 有序降级（2026-08-21）**：修订 D-166/D-177——化工现货/国内期货/期现双口径默认放行 `web_search`/`web_fetch`；先结构化、空结果再联网补价并标来源；仍禁交叉替代与 Yahoo 冒充国内期现。A 股/期权不变。TurnPlanner 将 chem Web 并入 Scenario 投影；澄清后仍保留 Web。聚焦 market/planner/projection/harness/prompt：**61 passed**；扩展 market 过滤：**23 passed**。规格/计划：[`D-181 design`](../superpowers/specs/2026-08-21-chemclaw-chem-web-ordered-fallback-design.md) / [`plan`](../superpowers/plans/2026-08-21-chemclaw-chem-web-ordered-fallback.md)。
- **D-180：第一方 system/tool 提示汉化（2026-08-21）**：默认 cowork/chat 主提示、`agent.py` 投影核心与共享 guidance、以及默认核心工具（read_file/grep/run_shell/todo_write/ask_user/web_search/web_fetch 等）的 schema `description` 改为简体中文，并写明「用简体中文思考与回复」；工具 name/参数键仍英文。GUI ThinkingBlock 继续原样透传 upstream reasoning。聚焦 `test_prompt_language_zh` + prompt/skills/batching/webpage/catalog/market：**58 passed**。不翻译 reasoning、不整库汉化 Skill。真机 ApiHub 思考语言待用户侧确认。
- **D-179：研究效率首包硬伤修复（2026-08-21）**：子智能体继承父 `MarketToolSelection`（含 D-177 双口径）；ApiHub generic invalid 强制 compact 重试一次 + EF salvage + 中文友好错误；`chart_finished_sidecar` 用 `series_name` 不再覆盖 `TOOL_FINISHED.name`；research 补 `grep`；Windows shell 默认 UTF-8；cowork 优先 `grep`/`read_file`。聚焦 engine/market/subagent/EF/shell/catalog：**35 passed**；宽回归 subagent+EF+cohort+background：**40 passed**。规格/计划：[`D-179 design`](../superpowers/specs/2026-08-21-chemclaw-research-efficiency-hard-fixes-design.md) / [`plan`](../superpowers/plans/2026-08-21-chemclaw-research-efficiency-hard-fixes.md)。
- **D-178：步骤卡下方 live 思考强制展开（2026-08-21）**：补丁 D-176——live「正在思考」只要挂载即 `forceOpen`（含「正在运行 x 个步骤」之后 remount），正文贴底跟滚；步骤卡可同时展开。规划间隙提示仍仅首包前。GUI `ThinkingBlock` + `firstTokenWaitCopy`：**16 passed**。规格/计划：[`D-178 design`](../superpowers/specs/2026-08-21-chemclaw-live-thinking-open-with-steps-design.md) / [`plan`](../superpowers/plans/2026-08-21-chemclaw-live-thinking-open-with-steps.md)。
- **D-177：期现套利双口径放行（2026-08-21）**：修复「甲醇期货…套利/基差/结合现货」被 D-166 单口径守卫误拦 `get_price_trend` 的问题。新增 `CN_SPOT_FUTURES`：同句现货+期货、期现/基差、或期货+套利/上下游时同一轮放行 chem-data-hub 与 `lookup_cn_futures_*`；禁止交叉替代。纯期货/纯现货/裸甲醇澄清与区域现货套利不变。聚焦 `test_market_intent` + market guard + scenario/planner/projection：**54 passed**。规格/计划：[`D-177 design`](../superpowers/specs/2026-08-21-chemclaw-spot-futures-basis-dual-scope-design.md) / [`plan`](../superpowers/plans/2026-08-21-chemclaw-spot-futures-basis-dual-scope.md)。
- **D-176：思考框贴底滚动 + 规划间隙提示（2026-08-21）**：live `ThinkingBlock` 正文在贴底时随 reasoning 滚到最新（框内上翻暂停）；空白期强制展开思考正文，下方轮播「龙虾正在规划下一步」类提示，步骤卡/回答流出现后消失。不改 TurnGroup / settled 思考默认收起。GUI 定向 **41 passed**。规格/计划：[`D-176 design`](../superpowers/specs/2026-08-21-chemclaw-thinking-scroll-planning-wait-design.md) / [`plan`](../superpowers/plans/2026-08-21-chemclaw-thinking-scroll-planning-wait.md)。
- **D-175：Subagent 自动汇合 + 短查兜底（2026-08-21）**：对照 Claude Code 完成通知、OpenHarness listener、DeerFlow 终态/短超时、Agents SDK fan-in；同批后台 Agent 全部终态后只注入一次汇合消息（`deliver_to_session`：idle 新回合 / busy steer），并接线 `WakeStore.complete_job`。`background_task_gather` 默认超时改为 **60s**，仅作短查/读报告；委派政策禁止长阻塞 gather 当主等待。新增 `DelegationCohortTracker`。聚焦 `test_delegation_cohort` + `test_subagent_cohort_wake` + `test_self_wake` + `test_subagent_runtime` + `test_background_tasks`：**34 passed**。不实现 AgentRoom，不占用 D-173。规格/计划：[`D-175 design`](../superpowers/specs/2026-08-20-chemclaw-subagent-auto-synthesis-design.md) / [`plan`](../superpowers/plans/2026-08-20-chemclaw-subagent-auto-synthesis.md)。
- **按时间最近对话取消自动折叠（2026-08-20）**：`Chronological` / flat 布局不再用 `RECENT_PEEK=4` 截断；「再显示 xx 项」已去掉，侧栏滚动展示全部会话。按助手分组的 `sessions_peek` 不变。GUI `Sidebar` **8 passed**。
- **D-174：Research Subagent 可执行权限 + 可靠停止（2026-08-20）**：修复研究子智能体卡在 plan 模式空转、缺国内期货工具、以及右栏停止后仍假 running 的问题。`research` 改为 `interactive` + `shared_workspace`，allowlist 含 `lookup_cn_futures_*` 与写报告工具，并继承父会话 PermissionEngine 模式（完全访问时写报告无需再卡审批）；停止超时强制 `cancelled` 且防竞态回写。`explore` 仍只读。聚焦 `test_subagent_runtime` + `test_background_tasks` + `test_subagent`：**26 passed**。不占用 D-173 Hook Bus。
- **权限模式首帧闪烁修复（2026-08-20）**：`/v1/health` 暴露 `mode`（`manager.mode` / prefs `default_mode`）；GUI boot 在清 splash 前 `setMode`，新建会话不回落 `interactive`；WS `ready` 仍为权威纠偏。去掉「先请求批准再跳完全访问」的显示滞后。GUI `permissionMode` **3 passed**；Python health 聚焦 **2 passed**。
- **D-172 补丁：研究意图优先于查价 Scenario（2026-08-20）**：修复「上海原油期货深度研究」等请求被 D-166 `cn_futures_market` / 现货查价 Scenario 抢走后 `subagent_eligible=false`、模型自报「并行派发被拒绝」的问题。含「深度研究/周报/产业链/供需分析」等标记时匹配 `chemical_market_research`（或企业研究），并禁止 market_intent 把 AGENT 降为 VERIFIED；纯查价（如「甲醇期货现在多少钱」「上海原油期货」）仍走查价 Scenario 且不开放 Subagent。`start_subagent` 默认 Profile 改为 `research`（代码探索须显式 `explore`）。聚焦 `test_scenario_resolver` + `test_turn_planner` + `test_agent_harness_routing` + `test_subagent_runtime`：**32 passed**。不占用 Phase 3 Hook Bus 的 D-173。
- **Cursor 工程交接（2026-08-20）**：已新增 [`CURSOR_HANDOFF_2026-08-20.md`](CURSOR_HANDOFF_2026-08-20.md)，以实际 `chemclaw-UI@98d9ce6` dirty worktree 为基线，完整记录产品边界、D-165—D-172 已完成能力、Phase 1/2 interface、运行/测试/ACL 风险、donor 固定版本，以及 Phase 3 Hook/Fallback/Verifier、Phase 4 Scenario 工作台、Phase 5 AgentRoom、Phase 6 企业微信的分阶段交接方案。本文档不新增运行时代码、不替代已批准决策；下一执行者必须先保护 D-168—D-172 未提交改动，再为 D-173 写规格并等待批准。
- **Agent Harness Phase 2 产品闭环（2026-08-20，D-172）**：D-171 的 runtime 已接入真实对话产品面。`chemical_company_research` / `chemical_market_research` 的 eligible TurnPlan 会投影 `start_subagent` 与任务控制工具，并注入“至少两个独立分支、最多 3 个研究子智能体”的有界委派政策；简单查价/身份查询不扩工具面。`BackgroundTaskManager` 的 created/status/output 变化经父会话 WS `background_task_changed` 通知，REST/SQLite 负责重连恢复。当前对话 RightRail 仅在存在任务时显示“子智能体与后台任务”，支持列表、状态/耗时、工作记录/结果、停止和 Agent 续发，不恢复独立“活动”页。真实 ApiHub 会话 `c3b686dc-2f8` 已并行完成上游原料、下游用途、代表企业 3 个 `research` task；父轮 Provider 超时后 child 仍继续直至全部完成并可在右栏点开，证明生命周期独立，其中两个分支产出带证据链接的完整复核报告；完成后的任务也已从右栏续发并以 `run_count=2` 读取原报告、再次完成。真实验收同时补给 `research` Profile 本地产物只读 `read_file/list_files`。聚焦 Python **52 passed**、GUI **34 passed**、production build 通过（仅既有警告）。规格/计划：[`D-172 design`](../superpowers/specs/2026-08-20-chemclaw-subagent-task-visibility-design.md) / [`plan`](../superpowers/plans/2026-08-20-chemclaw-subagent-task-visibility.md)。
- **Agent Harness Phase 2（2026-08-20，D-171）**：已完成通用 `SubagentRuntime + BackgroundTaskManager`。Agent/Shell 统一为可查询、增量读输出、停止、wait/gather、completion listener、重启调和的持久 task；内置 `explore/research/worker` Profile，复用现有 `TurnEngine`、child Conversation、MCP、PermissionEngine 与 TurnTrace。`explore` 旧合同兼容，Agent 完成后可续发消息并沿用 child context；Shell 不自动重放。提供 runtime tools 与本地鉴权 REST，不恢复 D-170“活动”页面。聚焦回归：runtime/permission **85 passed**、Harness/Planner/Trace **134 passed**、D-166 市场门禁 **89 passed**、Automation **21 passed**；服务器组合仍受已记录 Windows SecretStore pytest ACL 污染影响，未宣称全量通过。规格/计划：[`D-171 design`](../superpowers/specs/2026-08-20-chemclaw-subagent-background-runtime-design.md) / [`plan`](../superpowers/plans/2026-08-20-chemclaw-subagent-background-runtime.md)。
- **移除用户侧“活动/执行诊断”页面（2026-08-20，D-170）**：用户确认该开发排障页面难以理解且无直接业务价值；账号菜单已移除“活动”，App 删除 audit surface 与页面。D-169 的 Scenario/Capability、执行守卫、Trace 和诊断 API 继续在后端生效，不占用普通用户界面。Sidebar+i18n **30 passed**，D-169 Python 聚焦 **170 passed**，GUI build 通过。计划：[`D-170`](../superpowers/plans/2026-08-20-chemclaw-remove-activity-ui.md)。
- **Agent Harness Phase 1（2026-08-20，D-169）**：在既有单一 `TurnPlanner -> TurnEngine` 链路内完成 5 个内置 Scenario、8 个业务 Capability、声明式 Provider binding、规划期 readiness/fallback、受开关控制的 Tool allowlist guard、兼容 `ToolOutcome`、无正文 `TurnTrace` 及 REST/WS Preview/Trace。`scenario_resolution_enabled` 为**候选 ON**；关闭后保持 D-165/D-166 legacy 投影。未引入第二套 Agent Loop，也未提前实现 Subagent/BackgroundTaskManager/Hook Bus。聚焦 Python **170 passed**；1000 次确定性解析 P95 < 10 ms、缓存 Preview P95 < 50 ms。最初附带的用户侧执行诊断页已按 D-170 移除，后端能力不变。规格/计划：[`D-169 design`](../superpowers/specs/2026-08-20-chemclaw-agent-harness-phase-1-design.md) / [`plan`](../superpowers/plans/2026-08-20-chemclaw-agent-harness-phase-1.md)。
- **退役 GUI「客户清单」侧栏（2026-08-19，D-168）**：主导航去掉「客户清单」；删除 `LeadsWorkbench` / JSON 导入桥。对话侧 `format_lead_list` + `chem-lead-list` + 拓客龙虾产物保留。GUI `Sidebar`+`i18n`+`localization-audit` **31 passed**；`tsc --noEmit` OK。计划：[`retire-lead-list-nav`](../superpowers/plans/2026-08-19-chemclaw-retire-lead-list-nav.md)。
- **内置 chem-data-hub / chem-biz-scope MCP（2026-08-19，D-167）**：安装包可携带混淆密钥 bundle（`packaging/builtin_mcp.secrets.json` 构建注入，不进 Git）；首次启动种入全局 `mcp.json`（仅 `${VAR}`）与状态目录 `.env`；连接页只读「内置」（可启停，不可删/改密钥）。用户已自配同名 server 不覆盖；两台 URL 均在仓库模板（biz-scope：`http://121.37.133.47:8900/mcp`）。混淆≠对外密钥保管。定向 `tests/test_builtin_mcp.py` **9 passed**。规格/计划：[`D-167 design`](../superpowers/specs/2026-08-19-chemclaw-builtin-mcp-design.md) / [`plan`](../superpowers/plans/2026-08-19-chemclaw-builtin-mcp.md)。
- **化工现货与期货路由纠偏（2026-08-19，D-166）**：新增不可变市场意图/工具选择 seam；明确“现货”只投影 chem-data-hub `get_price_trend`，明确国内期货才投影 `lookup_cn_futures_quote/ohlc`，WTI/Brent 走 Yahoo OHLC。甲醇/原油等裸问价先 `ask_user`，Engine 在权限审批前阻止澄清前和错误口径调用；durable resume 重新读取原始用户请求，口径守卫不会因重启丢失。纯查价无 Web，MCP 缺失/空数据不以网页或期货补价。工具投影 OFF 或 Router OFF 保持 legacy。最终聚焦 **94 passed**（含 GUI WS 四场景 Tool 事件）；广泛回归 **319 passed, 8 deselected**，8 项均为既有/Windows ACL 环境失败。规格/计划：[`D-166 design`](../superpowers/specs/2026-08-19-chemclaw-spot-futures-routing-design.md) / [`plan`](../superpowers/plans/2026-08-19-chemclaw-spot-futures-routing.md) / [`execution log`](../superpowers/plans/2026-08-19-chemclaw-spot-futures-routing-execution-log.md)。
- **ApiHub CN Flash 单独重跑（2026-08-18，D-164）**：长答协议、N=3、≥200ms 不放宽。Live 只跑 `deepseek-v4-flash`（~39s）**PASS**（三轮长答间隔约 4.7–5.1s，已写入对表）。默认 `apihub-cn:deepseek-v4-flash` 带工具可真流式。Pro/GLM 仍为 D-163 PASS；kimi-k3 仍 FAIL。Kill switch OFF / Intl / 自定义 host 仍 buffered。定向 `test_apihub_cn_stream_capability` + `test_providers` + live skip：**63 passed, 1 skipped**。夹具合并写入 `docs/chemclaw/fixtures/apihub_cn_stream_capability.json`。规格/计划：`docs/superpowers/specs/2026-08-18-apihub-cn-flash-reprobe-design.md` / `docs/superpowers/plans/2026-08-18-apihub-cn-flash-reprobe.md`。
- **ApiHub CN 长答再验（2026-08-18，D-163）**：综合轮 ≥12 句/≥400 字；不放宽 200ms。`deepseek-v4-pro` / `glm-5.2` PASS。Flash 当时因第 3 次工具轮超时 FAIL，由 D-164 覆盖。
- **产物 Markdown 短引用回查出图（2026-08-18，D-162）**：报告 md 里的 K 线短引用与对话共用本会话 OHLC 回查（RightRail 预览传入 `chartToolResults`）。同会话打开含 `from_tool`+`symbol` 的产物可出图，不再报 `no … result in this session`。不手抄 OHLC、不写 sidecar。GUI `RightRail.artifacts`+`chartSpec`+`ChartBlock`+`Markdown`+`Transcript` **151 passed**；`tests/test_skills.py` **6 passed**。
- **ApiHub CN 带工具真流式单独验证（2026-08-18，D-161）**：精确 `(host, model)` 对表已落地；短答 live 四模型无 PASS。生产对表以 **D-163 + D-164** 为准。Kill switch OFF 与 Intl/自定义 host 不变。规格/计划：`docs/superpowers/specs/2026-08-18-apihub-cn-structured-stream-verify-design.md` / `docs/superpowers/plans/2026-08-18-apihub-cn-structured-stream-verify.md`。
- **未指定周期默认日线（2026-08-18，D-160）**：问股价/期货价未点名周期时走日线 OHLC（CN `lookup_*_ohlc`、Yahoo `interval=1d`、期权 `action=daily`），不默认分钟/周/月。guidance 去掉「60 交易日或月线 ≥12 点」的股票/期货等价选项；`stock-analysis` 分钟仅用户点名才用。化工现货与 GUI 不动。定向 pytest（skills + cn_market_agent + yahoo_ohlc + finance + snapshot/parity）**31 passed**。
- **Yahoo/CN 短引用直播出图（2026-08-18，D-159）**：`TOOL_FINISHED` 额外下发 `chart_spec` sidecar（步骤卡仍 300 字 preview）；GUI 存 `chartPreview` 并**全会话**回查 OHLC 工具（追问不必再调）。匹配 payload.symbol/name/aliases 与 `args.symbol`。错误分层：无该工具 / preview 截断 / 工具 `error`（如 Yahoo HTTP 429）。GUI `chartSpec`+`ChartBlock`+`Markdown`+`Transcript` **147 passed**；`tests/test_engine.py` **19 passed**。
- **阶段色带互斥（2026-08-18，D-158）**：`exclusiveStageRanges` 按 last-wins 把每个 X 索引判给最后覆盖它的 stage，色带与左栏共用裁切后的连续互斥区间；相邻 `xMin/xMax` 以 `±0.5` 贴齐，半透明红/绿/蓝不再叠成紫/褐。日频共享端点与月标签吸附日频 stages 均适用。不改 ChartSpec。GUI `chartSpec`+`ChartBlock`+`Markdown` **103 passed**。
- **短引用中文品种匹配（2026-08-18，D-157）**：CN OHLC payload 回传 `name`/`aliases`（期货从品种表填入，如橡胶→`RU.SHFE`+`天然橡胶`）。GUI short-ref 对 `symbol`/`name`/`aliases` 精确匹配（禁止 includes，避免「橡胶」误配「丁二烯橡胶」）。guidance：优先抄工具回包 `symbol`，中文名能对上该次回包也可。`tests/test_cn_market.py`+`test_cn_market_futures.py`+`test_skills.py` **36 passed**。
- **行情驱动因素纠偏（2026-08-18，D-156）**：分段仍由模型给 `start`/`end`/`reason`；GUI 按区间收盘/现货涨跌幅重算 `tone`（`Rmax<0.8%` 全横盘，否则 `|r|<0.4*Rmax` 才 side），色带与左栏共用。`reason` 只写主导因素，禁止复述涨跌、禁止具体价格；展示层去掉 `2374.00`/`¥3180` 一类价位，删空则隐藏驱动行。`MAX_STAGE_REASON_LEN=80`。guidance + `chem-price-daily` 已对齐。GUI `chartSpec`+`ChartBlock`+`Markdown` **98 passed**；`tests/test_skills.py` **6 passed**。
- **小图不标极值、全屏才标（2026-08-18，D-155）**：对话内 `candlestick`/`line`/`area` 不画高低价标签（阶段色带仍在）；全屏只标**可见窗口**全局最高+最低各 1 个，缩放/拖动时刷新。小图收回顶/底/右标签留白。`bar`/`scatter` 与 ChartSpec 不动。
- **行情图极值标签分侧+去重（2026-08-18，D-154）**：K 线与现货 `line`/`area` 共用：最高价标在点上方、最低价标在点下方；顶部 padding 32、底部 20；可见区 Y pad 约 12%。同 kind 且 X 索引间距 <5 的阶段极值丢弃，避免相邻最低价叠字、最高价被标题裁切。`bar`/`scatter` 与 ChartSpec 不动。GUI `chartSpec`+`ChartBlock`+`Markdown` **86 passed**。
- **现货图缩放/拖动对齐 K 线（2026-08-18，D-153）**：`line`/`area` 与蜡烛图相同：默认最新约 90 点（全屏 180）；滚轮缩放 + 左右拖动（仅 X）；可见区 Y 自适应；X 轴最多约 8 个日期；可见点 >24 时隐藏圆点（悬停仍可定位）。高低价标签改到点上方；右侧与底部留白，避免最低价压住日期、最右价格被裁切。`bar`/`scatter` 不动。不改 ChartSpec。GUI `chartSpec`+`ChartBlock`+`Markdown` **84 passed**。
- **左栏空白收紧（2026-08-18，D-147）**：左卡 `fit-content`；OHLC 左右排、系列上下排；开/收随当根涨跌（红涨绿跌），最高红、最低绿。
- **左栏价格不截断（2026-08-18，D-146）**：左栏 KV 上下排 + 加宽轨；长系列名不再把上千价裁成上百。
- **国内行情 Agent 接线（2026-08-18，D-152）**：默认对话注册 `lookup_cn_stock_quote/ohlc/minute/financials/feature`、`lookup_cn_futures_quote/ohlc/minute/l1`、`calculate_cn_futures_margin`、`lookup_cn_option_market`。A 股/国内期货/期权走 CN 工具，美股/港股/全球期货走 `lookup_yahoo_ohlc`；CN 失败禁止网页探测或 Yahoo 补同一行情。GUI short-ref 支持 CN OHLC（`from_tool` 须匹配所用工具；期货可用 `PG` 对上 `PG2609.DCE`）。公开查询新增 `cn_stock_public` / `cn_futures_public` / `cn_option_public`。Tick/L2 仍未做。不加 AKShare，不改 `pyproject.toml`。定向：`tests/test_cn_market*.py` + wiring/projection/finance/catalog **83 passed**；GUI `chartSpec`+`ChartBlock`+`Markdown` **78 passed**。全量 `pytest`（`--deselect` 既有挂死用例 `test_ws_session_persisted_while_parked_on_approval`）：**1721 passed, 30 failed, 2 skipped, 1 deselected**；30 个失败均为既有（bedrock/fake_slack/durable-resume/pack bytecode 等），**NEW FAIL = none**。HARD STOP D schema snapshot 已含 11 个 CN 工具。
- **期权公开 adapter（2026-08-18，D-151）**：`PublicCNOptionProvider` + `lookup_cn_option_market`（action：contracts/quote/daily/minute/greeks/exchange_stats）。上交所 ETF 期权走新浪到期月 + `OP_UP`/`OP_DOWN`/`CON_OP_*`/`CON_SO_*` + 日线/分钟 JSON；中金所合约盘口走 `OptionService.getOptionData`。Greeks 仅 `greeks_source=upstream`，不做本地 BS。`exchange_stats` 因 Run 0 字段失败 + 本机 `query.sse.com.cn` 超时保持 `source_unavailable`。概念/行业等 Core-35 缺口 Run 0 未验证，**不发明源**，`stock_feature` 仍 `unsupported`。Agent 接线见 D-152。
- **国内期货公开 adapter（2026-08-18，D-150）**：`PublicCNFuturesProvider` 用 urllib 拉新浪 L1（`getHQFuturesData`，node 用 `qihuohangqing.js` 标记如甲醇 `zc_qh`，不是 `MA0`）、合约/连续日线与 1/5/15/30/60 分钟 JSONP。主力按持仓量本地选取（`dominant_by_open_interest`）；`MA0`/`PG0` 标成 `upstream_sina_continuous`，不冒充本地连续。L1 只承诺一档（`market_depth=L1`）。理论保证金 = 价格×乘数×保证金率×手数，明确非期货公司占用。Agent 接线见 D-152。
- **A 股公开 adapter（2026-08-18，D-149）**：`coworker/cn_market/` 可读新浪报价/日线/分钟/财报、东财龙虎榜、上证两融汇总、北向历史（金额可能空）。Agent 接线见 D-152。不加 AKShare。期货真源见 D-150。
- **国内行情层地基（2026-08-18，D-148）**：`coworker/cn_market/` 公共合同 + cache + symbol/calendar + fake provider。不接 Agent、不加 AKShare。A 股真源见 D-149。
- **去掉 Wind 金融 Skill 路径（2026-08-18，D-145）**：确认 ChemClaw 无可用 Wind 工具；`market-analysis` / `stock-analysis` / `macro-analysis` 删除 `wind_financial_reference_content`；改走 `lookup_yahoo_ohlc` + `web_search`/`web_fetch`；缺指标 unavailable；启动窄刷新已安装旧文案；产业链龙虾金融为验证层。国内结构化行情见 D-148 `coworker/cn_market/`（另案进行中；不把 AKShare 打进核心依赖）。
- **左栏详情始终左中（2026-08-18，D-144）**：K 线/现货左栏卡片一律垂直居中，不再因内容长短贴顶。
- **行情操作芯片悬停才显（2026-08-18，D-143）**：对话内顶部固定占位、悬停只淡入（不挡标题/图例、图画布不位移）；全屏 lightbox 仍常显。
- **全屏不透 + 现货区间/焦点（2026-08-17，D-142）**：lightbox 近不透明；line/area 支持 stages + focusLabel 默认固定；短左栏垂直居中；guidance 默认拉够历史。
- **现货十字线 + 融文铬层（2026-08-17，D-141）**：line/area/bar 与 K 线同左栏+十字线+点击固定；默认最新价；成功图无图/源切换、无灰框，仅全屏图标与芯片提示。**操作芯片顶部固定占位、悬停淡入（D-143）**；全屏内仍常显。
- **K 线滚轮缩放与默认最新窗（2026-08-17，D-140）**：蜡烛图默认显示最新约 90 根；滚轮缩放 + 拖动平移（X）；可见区 Y 自适应；收紧左右空白；X 轴连续交易日均匀刻度。
- **K 线 OHLC 数组兼容（2026-08-17，D-139）**：手抄 candlestick 时 `ohlc` 可写 `[o,h,l,c]` 四元组或 `{o,h,l,c}`；解析器归一成对象。Yahoo 仍优先 short-ref。
- **K 线阶段标注（2026-08-17，D-138）**：蜡烛图可选 `stages`；悬停左栏详情（日期→OHLC→区间/驱动）；**单击固定**后可滚读；**挂载默认最新**（D-141）；**全屏**更大字号与约 180 根默认窗；极值防裁切；拖动/滚轮与固定提示。Yahoo short-ref 可同级附带 `stages`。
- **K 线国内红涨绿跌（2026-08-17，D-137）**：蜡烛图阳红阴绿（同花顺/文华习惯）；折线色板不变。
- **Yahoo OHLC 短引用出图（2026-08-17，D-136）**：K 线数字不经模型手抄；工具返回 `chart_spec`，气泡正中 ````chart` 只写 `from_tool`+`symbol`，GUI 回查本轮 tool 出图；手抄长度不齐时解析器 `min` 截齐兜底。
- **行情默认趋势图（2026-08-17，D-134）**：有 ≥2 点时间序列时，价格回答须附 ```chart`（表+要点+图）；空态价格卡文案、`_INLINE_CHART_GUIDANCE`、`chem-price-daily` 已对齐。仍不引入 deterministic helper / Fast Router。
- **Yahoo OHLC + 蜡烛图（2026-08-17，D-135）**：第一方 `lookup_yahoo_ohlc`（非官方 Yahoo Chart，免密钥 best-effort）；ChartSpec `candlestick` + `ohlc`；缺省 `version` 视为 1；多标的分多张 K 线图。化工现货仍用 MCP + line。
- **Inline Chart 快路径（2026-08-17，D-133）**：聊天即时图走 ```chart` → ChartSpec v1 → Chart.js（`ChartBlock`）；流式不出图；全局 guidance 优先 inline、禁止仅为可视化调 chart-image/shell/Node。`chart-image` 仅静态导出。解析兼容 `x.labels` / `xLabel`/`x_label`/`x.title`。多 series 用 Okabe–Ito 改编期刊定性色板（首色 ChemClaw `#2563eb`，第二色朱红 `#D55E00`）。回归：`chartSpec`+`ChartBlock`+`Markdown`；`tsc --noEmit` OK。第二轮（数值确定性归一化 / Fast Router）未做。
- **产物栏交付约定（2026-08-17，D-132）**：会话根目录为最终产物；`._chemclaw/charts/` 为内部过程文件。knowledge 会话隐藏遗留顶层 `charts/`；打开芯片时把当前 workspace 内的 Windows 绝对路径安全转为相对路径；RightRail 不再静默只显示 16 条。**会话 workspace 不跟随 shell cwd**；已写入 `._chemclaw/...` 的污染路径读取时截回会话根。
- **D-165 按需上下文 + Flash 真流式（2026-08-19）**：真实 `SessionManager -> build_engine -> TurnEngine.run` 已接入每轮 `TurnPlanner -> TurnPlan`；FAST/KNOWLEDGE `tools=None`、Skill catalog=0，并用新会话 prompt policy v1 出站投影短 prompt；行情、定向 Agent、普通工作区与可视化任务分别只装配相关 prompt sections，旧会话无标记继续 legacy。明确 Agent 动作按工作区/Memory/调度/消息/Skill/销售能力包投影，附件、Plan/Discuss、后台、Persona、durable resume、pending control 与未知 MCP/connector 保留完整能力。`search_skills` 只返元数据；reasoning 请求与展示解耦，上游有则实时显示。`prompt_projection_enabled` built-in = **候选 ON**；本地 GUI WS、权限/审批、Memory/Skill、压缩、Provider/Router、行情图与 GUI build 已过，**NEW FAIL = none identified**。真实 ApiHub Flash N=5 + 长答 **PASS**：问候实际 prompt=85 tokens、tools/skills=0、TTFT P50=2.88s/P95=6.88s；6 个主回答全为 direct、fallback=0；长答 745 个正文 delta。上游 reasoning delta=0，因此不显示思考属于 Provider 未返回，并非 GUI 隐藏。夹具：`docs/chemclaw/fixtures/apihub_cn_d165_gui_probe.json`。计划/日志：[`D-165`](../superpowers/plans/2026-08-19-chemclaw-on-demand-context-streaming.md) / [`execution log`](../superpowers/plans/2026-08-19-chemclaw-on-demand-context-streaming-execution-log.md)。不引入 Harness，不设默认子 Agent。
- **性能/路由改造 Plan v5（2026-08-13）**：Plan + execution log 已入库。[`…-v5.md`](../superpowers/plans/2026-08-13-chemclaw-performance-router-v5.md) / [`…-execution-log.md`](../superpowers/plans/2026-08-13-chemclaw-performance-router-v5-execution-log.md)。**HARD STOP A–G + §65 steps 46–55 final regression 已完成**。**Step 56–59（独立授权）已落地**：`request_routing_enabled` + `tool_projection_enabled` + **`structured_tools_true_streaming_enabled`（仅 known-safe）** + **`emergency_finalization_enabled`** built-in = **候选 ON**；unknown/custom compat **仍 buffered + salvage-safe**；FAST/KNOWLEDGE 强制 EF OFF；kill switch OFF 可回 legacy hard-limit。hard-ceiling / Stop / pending / durable-resume / unfinished side-effect：**NEW FAIL = none**（`test_durable_resume_approval_executes_tool` 仍为既有 EXISTING FAIL）。真实 GUI Critical Product Smoke A–P = **ENV BLOCKED — manual validation pending**。**四开关独立 rollout 已全部完成**；D-165 已补齐真实会话每轮接线。
- **默认身份自称（2026-08-13，D-131）**：默认 `cowork` 的 system prompt / Agent title / 前端 short·full 名统一为 **ChemClaw**（不再「我是 Cowork」）；路由 id 仍为 `cowork`。回归：`pytest` identity 3 passed；`personaScope`+Sidebar **10 passed**。
- 产品设计：书面规格已于 2026-07-29 获得用户批准。
- 实施计划：阶段 1“首条真实纵向链路”已获用户批准。
- 销售增长智能：外贸/内贸/商机/转化设计已于 2026-08-07 获批。**已授权并实现（D-091—D-103、D-105—D-122、D-127）**：四龙虾包；PubChem/GLEIF/国内登记；TED；SAM；Comtrade；海关；询盘转报价；清单；SMTP；HubSpot（笔记/创建联系人/**字段更新/任务创建**）；化工社合集试点+Triage；API 公开查询；SAM/Comtrade 境外可选；VAT/汇率/维基；**化工社只读检索**（D-118）+ **写反应首包**（D-119）+ **公开 SVG 落盘 Tool**（D-120）+ **压缩硬裁提示中性化/二次收紧摘要**（D-121）+ **四销售龙虾专属空态三卡**（D-122）。默认仍为 ChemClaw/`cowork`，销售 Agent 默认禁用。**本机销售环点检（2026-08-09）用户确认通过**。
- **化工多平台内容重构（2026-08-10，D-104 / D-107；2026-08-12，D-128）**：选用 Plan B；**M1+M2+M3 代码已落地**：`platform-rewrite-lobster` + 四核心 Skill + **`chem-hook-cta-pack`（按需）**、确定性扫描、合成夹具、**12 条回归语料**、空态三卡；knowledge 会话只读挂载 `skills`；**M3** managed 词表热升级 + `user.csv` 覆盖不冲掉 + `rule_set.version`；默认仍为 `cowork`，新 Agent 默认禁用；不自动发帖。定向 pytest（platform-rewrite + bootstrap + packaging）**38 passed**。**2026-08-13 已重打 NSIS**（staged sidecar 含 bundled/builtin；安装后 frozen `load_skill` 运行时补验仍可在干净 `%APPDATA%\\ChemClaw` 上做）。见 [platform-rewrite/README.md](platform-rewrite/README.md)、[HANDOFF_PLATFORM_REWRITE.md](HANDOFF_PLATFORM_REWRITE.md)、[计划](../superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md)。
- **上游 Wave B（2026-08-11，D-125）**：已合入 `chemclaw-clean`（fast-forward）。OpenWorker [#471](https://github.com/andrewyng/openworker/pull/471) ask_user 2.0：富选项（说明/推荐/预览）+ 最多 4 题分组 stepper；旧单题/字符串 options/Inbox JSON 兼容；GUI 全 i18n。验证：`pytest` ask+durable **15 passed**；`tsc` OK；`ask-upgrades` e2e **2 passed**。
- **上游 Wave C（2026-08-11，D-126）**：已合入 `chemclaw-clean`（fast-forward）。OpenWorker [#472](https://github.com/andrewyng/openworker/pull/472) Memory V1 四段移植（core → settings/REST → GUI/Undo → CLI/TUI）。语义：关=停写入；已有记忆仍可读/注入新会话；写开关 live；user rules 会话启动时固定。验证：`pytest` memory+api **52 passed**；GUI `tsc` OK；Transcript/i18n/audit **55 passed**；`python -m coworker.cli --help` OK。
- **上游 Wave A（2026-08-11，D-124）**：已合入 `chemclaw-clean`：[#415](https://github.com/andrewyng/openworker/pull/415) DNS pin、[#416](https://github.com/andrewyng/openworker/pull/416) tomllib/3.10、[#419](https://github.com/andrewyng/openworker/pull/419) GUI `tsc` CI、[#417](https://github.com/andrewyng/openworker/pull/417) GUI README 路径。计划：[chemclaw-upstream-file-by-file-upgrade-plan-2026-08-11.md](chemclaw-upstream-file-by-file-upgrade-plan-2026-08-11.md)。
- **本机 NSIS 安装包（2026-08-19 15:40 重打）**：用户点名自本 worktree `chemclaw-clean` @ `eb635fb` + 工作区未提交 D-167（内置 chem MCP）重打；未签名 `ChemClaw_0.1.7_x64-setup.exe`（约 **49.7 MiB** / 52.1 MB，mtime 15:40）于 `surfaces/gui/src-tauri/target/release/bundle/nsis/`。无 updater 签名密钥，不含自动更新制品。staged sidecar 验收：**108** `SKILL.md` + **7** builtin persona（含 `export-sales-lobster` / `platform-rewrite-lobster`）；含 `builtin_mcp.bundle` + `builtin_servers.json`；sidecar 内无 `sessions`/transcripts 目录。聊天只在 `%APPDATA%\\ChemClaw`，不进安装包；要无旧聊天+最新 seed 技能请先改名备份该目录再首次启动。
- **安装包纠偏（2026-08-11，D-123）**：旧包未打入 `skills/bundled`/`personas/builtin`，运行时又读 `%APPDATA%\\coworker`，表现为「带旧聊天、缺新龙虾」。已按 D-123：sidecar 打入本树 bundled/builtin；默认状态目录 `%APPDATA%\\ChemClaw` / macOS `~/.config/chemclaw`（不迁移旧 coworker 数据）。**请装到空目录，不要覆盖 `D:\\ChemClaw` 旧工程树**；勿把桌面快捷方式指到旧目录里的 exe。
- **macOS DMG（2026-08-11）**：`packaging/build_dmg.sh` 的 APP 名改为读 `tauri.conf.json` `productName`（ChemClaw）；Release workflow 稳定产物名为 `ChemClaw-macos-arm64.dmg` / `ChemClaw-macos-x64.dmg`。须在 **macOS runner**（GitHub Actions `workflow_dispatch` 或标签 `app-v*`）或本机 Mac 构建，Windows 不能交叉编译。已推送 `chemclaw-clean` @ `9b0ac4c` 与标签 `app-v0.1.7-chemclaw-macos`。若 Actions 页仍为 0 runs：到仓库 Settings → Actions → General 允许 Actions 后再 **Re-run** / `workflow_dispatch`。无 Apple 证书时为未签名包：Mac 上右键打开或 `xattr -cr ChemClaw.app`。
- **架构调整（2026-08-03）**：采用方案 A，从 OpenWorker 最新 `main`（含 2026-08-01 Skills PR #391）重建 ChemClaw 层，丢弃自研 `capabilities` 模块。
- 当前阶段：阶段 1，上游 Skill + ChemClaw 品牌/汉化/导航（进行中，待用户界面验收）。
- 当前分支：`chemclaw-UI`，D-172 开始时提交 `98d9ce6`（工作树包含尚未提交的 D-168—D-172；push 须点名）
- **当前开发 Worktree**：`D:\OpenWorker\openworker\.worktrees\chemclaw-UI`
- 旧 Worktree（只读备份，待确认后删除，本次不删）：`D:\OpenWorker\openworker\.worktrees\chemclaw-design`（分支 `design/chemclaw-foundation` / 标签式备份 `backup/broken-2026-08-03` 已在 `backup` 远程）
- 业务代码（本 Worktree）：
  - ✅ 基于 upstream/main（OpenWorker Skills 官方实现）
  - ✅ ChemClaw 品牌 + 全界面汉化（cherry-pick 自旧分支）
  - ✅ D-006 主导航：对话 / 技能 / 智能体 / 定时任务 / 连接 / 设置（D-168 已退役 D-098 侧栏「客户清单」页）
  - ✅ D-066 智能体拆包联装：`package_scan` / `package_install`；`POST /v1/personas/install` 支持 `zip_b64`/`data_b64`/`package_dir` + 逐项 `decisions`；`skill_ids` + `persona_detail` 暴露 prompt/skills/路径
  - ✅ D-069 OpenClaw 工作区合成 + 冲突批量/汉化：无 ChemClaw persona 且有 IDENTITY/SOUL 时，将 IDENTITY/SOUL/AGENTS/USER/TOOLS/MEMORY 等合成进一个智能体提示词（不当作多个智能体）；`memory/` 不整树导入；预览「全部覆盖/全部跳过」+ i18n
  - ✅ 技能页使用上游 `SkillsTab`，已汉化；不再使用自研 `SkillsView` / `capabilities`
  - ✅ 智能体页（`PersonasTab`）控件与内置文案已接入 i18n；导航品类名「智能体」+ 单色龙虾图标（D-064）
  - ✅ 新建对话 A1：主按钮按标星默认；▾ 中文选择器；`surfaced` 过滤；回答区显示本会话智能体名；空会话主标题统一「与 xxx 畅谈」（含 ChemClaw/`cowork`；▾ 选中立即 `setAgent`）（D-067）
  - ✅ 智能体详情：列表右侧恢复 Sliders 图标；从智能体页进入可返回智能体；详情页加载/返回中文化（D-065）
  - ✅ Zip 联装：上传带 `filename`；旧后端 `provide a dir…` 映射为重启提示；**需重启 sidecar** 才能加载含 `zip_b64` 的后端
  - ✅ Mermaid 边标签：`agent.py` 全局 `_DIAGRAM_GUIDANCE`（D-063）；AGENTS.md 约定；产业链 Skill + skill-creator 补强；**不对用户展示**缺标签提示
  - ✅ 全部智能体右侧栏显示产物；相对路径/artifact 文档链统一 ArtifactChip，单击打开预览；结束后长回答从「N 个步骤」提出
  - ✅ 步骤组生命周期默认态（D-070）：进行中默认展开、成功结算收起、失败/中断保持展开；手动覆盖优先；不改 ThinkingBlock/raw/密度档位
  - ✅ 默认技能接线：`build_engine(default_skill_ids=…)` 提醒 load_skill（D-068）
  - ✅ 智能体只读详情：system_prompt / skills / install_path（D-065）
  - ✅ 首次启动 seed 完整内置 Skills（Serenity 七个中文投研 + builtin-skills 除 computer-use + chem-* 系列；含 references/scripts；可删且不回种）
  - ✅ Skill 名支持中文；zip 上传保留附属文件与扩展 frontmatter
  - ❌ 已移除薄提示词版 `serenity.industry-chain-mapping`（若开发态仍残留，可在技能页手动删除一次）
  - ✅ 自动更新入口已关闭（`UPDATES_ENABLED = false`）
  - ✅ 空模型流不再静默落成空白助手消息（`TurnEngine` 改为可重试 ERROR）
  - ✅ OpenAI 兼容流遇 `incomplete chunked read` 时自动重试并回退非流式；错误文案中文化
  - ✅ 对话内中文 `artifact:` 链接打开产物：解码 react-markdown 的 percent-encode，避免误报「文件已移动/删除」
  - ✅ 产物预览期间手动展开左侧栏不再被自动打回（预览开闭边沿折叠 + 稳定 `onPreviewChange`）
  - ✅ 对话与 MD 报告 fenced mermaid 真实渲染（图/源码、遮罩全屏、SVG/PNG；流式不出图；防抖占位）
  - ✅ Mermaid 全屏：以矢量 SVG（viewBox）铺满视口，缩放改 CSS 宽高而非 bitmap transform，避免又小又糊
  - ✅ Mermaid 全局主题改为 `neo`（彩色现代主题；图内 `%%{init}%%` / `classDef` 仍可覆盖）
  - ✅ Mermaid 悬停/聚焦才显示框线与工具栏（默认融文；错误态始终露出；工具栏 visibility 保占位防抖）
  - ✅ Mermaid 渲染失败补救（D-074）：语法失败自动就地修 1 次并显示「正在修正图表…」；仍失败保留「修复图表」；成功图/过长/库加载失败不进模型修图；`POST /v1/sessions/{id}/mermaid-repair` + `message_updated`
  - ✅ 设置页 Context compaction 已汉化；产品默认 **70% / 100,000 tokens**（D-129；设置仍可调到最高 95% / 2,000,000；已有 prefs 不迁移）
  - ✅ （2026-08-12 D-130）摘要可靠性首包：摘要输入改为按摘要模型窗口计算的保守 token 硬预算（未知模型按 32k；普通最多 24k、重试最多 8k）；失败日志区分 reasoning-only / 空回复 / 截断 / 超限 / 限流 / 超时且不记正文；两次失败后先生成确定性 continuity ledger（todo、产物路径、命令、MCP、最近结论、用户原话）再续跑；canonical transcript 不变。
  - 回归：`pytest tests/test_compaction.py tests/test_compaction_engine.py tests/test_providers.py`：**75 passed**；GUI i18n/localization：**23 passed**；`npm run build`：通过（仅既有 chunk-size/dynamic-import 警告）。
- ✅ （2026-08-05 D-073）长程任务不再因上下文过大阻塞：压缩失败不弹阻塞式 QUESTION；出站工具大回包统一裁剪到 40,000 字符并溢出落盘；压缩后续跑依赖 `<compacted-history>`（**2026-08-06 已撤销** `task-progress.md` 落盘与「查看任务进度」入口）
- ✅ （2026-08-06 D-075）Agent Runtime 提速与体验 A–C：产物错误中文化；禁止本地 browser 自检；只读 MCP 并行 + 30s 默认超时（慢查询可用 `CHEMCLAW_MCP_TOOL_TIMEOUT=120` 覆盖后重启 sidecar）；MCP 结构化摘要；Trim 中文硬裁；**已撤销**任务进度 md / MCP 批次落盘；规格/计划见 `2026-08-06-chemclaw-agent-runtime-ux-*`（里程碑 D 待做）
- ✅ （2026-08-06 D-076）首包空窗 UX：live Thinking 首包阶段默认展开；无 reasoning 时龙虾等待文案按前→后池约每 3s 轮播（中英）；不再长期「正在等待 Agent…」；规格/计划见 `2026-08-06-chemclaw-first-token-wait-ux-*`
  - ✅ （2026-08-07 D-079）对齐后续跑空窗：答完 ask_user / 发送后乐观 running；锚点含 resolved question；「收到反馈」文案池与首发「挠头」池分流
  - ✅ 回归：`npm test -- --run src/firstTokenWaitCopy.test.ts src/FirstTokenWaitLabel.test.tsx src/i18n.test.tsx src/localization-audit.test.ts`：33 passed
  - ✅ （2026-08-07 D-080）默认智能体 ChemClaw/`cowork` 空态：去掉 HubSpot / GitHub+Slack 门控卡；三条改为研究备忘录 / 价格走势 / 本地文件夹提炼；lede 化工向；标题「与 {name} 畅谈」不变；chain-lobster 空态保持；prefill 中英 i18n
  - ✅ 回归：`npm test -- --run src/i18n.test.tsx src/localization-audit.test.ts`：22 passed；e2e `session-intro.spec.ts` 已同步为 memo/price/folder
  - ✅ （2026-08-07 D-081）拆除遗留 `surfaces.chat/code` 强制回弹 cowork：▾ 选代码/问答后空态不再被打回 ChemClaw；可见性只认智能体页 enabled/surfaced
  - ✅ 回归：`npm test -- --run src/surfacesAgentGate.test.ts src/i18n.test.tsx src/localization-audit.test.ts src/components/Sidebar.test.tsx`：31 passed
  - ✅ （2026-08-07 D-082）代码工作区门禁推迟弹出 + 可关闭：新建代码会话先空态；发送/推荐/CTA 再选文件夹；FolderGate 始终「关闭」
  - ✅ 回归：`npm test -- --run src/folderGatePolicy.test.ts src/components/FolderGate.test.tsx src/surfacesAgentGate.test.ts src/i18n.test.tsx src/localization-audit.test.ts`：28 passed
  - ✅ （2026-08-07 D-083）问答空态：标题改为「有什么想问的？」；三条轻量推荐（解释/对比/追问清单）；无工作区
  - ✅ 回归：`npm test -- --run src/components/SessionIntro.chat.test.tsx src/i18n.test.tsx src/localization-audit.test.ts`：23 passed
- ✅ （2026-08-07 D-084）试用禁用上游云登录：`CLOUD_SIGNIN_ENABLED=false`；隐藏登录与 Gallery；login/managed/gallery API 硬闸；Manual + ApiHub 不变
  - ✅ 回归：`pytest tests/test_cloud_server.py`：18 passed；`npm test -- --run src/cloudSignInGate.test.tsx src/components/Sidebar.test.tsx src/i18n.test.tsx src/localization-audit.test.ts`：32 passed
- ✅ （2026-08-07 D-085）本机资料：显示名 + 可选本地头像；侧栏不再「未登录」；设置→通用可编辑
  - ✅ 回归：`pytest tests/test_local_profile.py`：6 passed；`npm test -- --run src/components/Sidebar.test.tsx src/i18n.test.tsx src/localization-audit.test.ts src/cloudSignInGate.test.tsx`：32 passed
- ✅ （2026-08-06 D-077）报告网页版曾落地自动后台烹饪；**（2026-08-07 修订）** 因失败率过高废止固定流水线：文档版为主阅读；网页版改为可选、先对齐再对话内生成；白话问 +「做网页版」按钮注入意图；拆除设置/入队/三态文案/再下厨 API；保留右侧 HTML 预览沙箱；规格见 `2026-08-06-chemclaw-report-webpage-cook-design.md`（已修订）
  - ✅ （2026-08-07）拆除回归：`pytest tests/test_webpage_optional_prompts.py tests/test_skills.py::test_build_engine_chat tests/test_settings.py`：11 passed；`npm test`（requestWebpage/Markdown/sessionResume/i18n/localization-audit/htmlPreviewSandbox）：49 passed
- ✅ （2026-08-07 D-078）短气泡恢复 + 价格表/交互行情图 + 预览沙箱放宽：有最终 MD 时气泡仅结论/要点/链接；龙虾默认 `chem-price-daily`（MD 价格表、网页可悬停走势图可用 CDN）；沙箱允许外链 script + 只读 GET，禁 POST 外泄
  - ✅ 回归：`pytest tests/test_webpage_optional_prompts.py tests/test_skills.py::test_build_engine_chat`：4 passed；`npm test -- --run src/htmlPreviewSandbox.test.ts`：6 passed
  - ✅ 设置页上下文用量条（原 Composer 卡片）已汉化：标题「输入框」、开关与说明走 `t()` + `interfaceMessagesZh`
  - ✅ 后台对话继续与回切追齐：离开设置/其他对话不杀 turn；同会话重选不误清 streaming；`ready.running` + `turn_done` REST 追齐最终回答（D-061）
  - ✅ 跨会话并行回答（D-062）：`stream()` 每路独立 OpenAI SDK 客户端，避免切新对话把后台 turn 打成 Connection error；WS 事件按绑定 session 过滤防 Interrupted 串台；不做全局对话数软上限（后台 turn 也占 running）
  - ✅ `/` 技能弹出列表：`max-h-56 overflow-y-auto`，技能过多时可滚动且不挤掉输入框；键盘 ↑↓ 时 scrollIntoView 跟选中项
  - ✅ `/` 介绍优先搜索：按 description 子串/子序列优先打分排序，中文场景词可命中英文 id 技能；name 仍为次要通道
  - 🔄 对话挂载条等待在上游 Skill 稳定后单独处理
- 浏览器源码预览：默认显示简体中文，可切换英文并在刷新后保留选择。
- 运行态修复（2026-08-03，开发 state）：
  - OpenAI 兼容网关 `base_url` 补全为 `…/v1`（缺 `/v1` 会导致 0 chunk 空回答）
  - 默认模型改为流式稳定的 `kimi-k2.5`（原 `deepseek-v4-flash` 在该网关上工具流易断）
  - （2026-08-05 D-071）新鲜安装代码默认改为 `apihub-cn:deepseek-v4-flash`；已有 prefs 不改
  - 真实 WS 链路验证：`agent=chat` → 助手返回 `OK`
  - 回归状态（2026-08-04，bundled skills）：
  - `pytest tests/test_skills_store.py tests/test_skill_bootstrap.py tests/test_skills.py tests/test_skills_api.py`：71 passed, 1 skipped
  - 内置目录：`coworker/skills/bundled/` 共 43 个完整 skill（无 `computer-use`、无薄版 industry-chain）
  - 回归状态（2026-08-04，Context compaction）：
  - `pytest tests/test_compaction_engine.py tests/test_compaction.py`：31 passed
  - `npm test`（i18n + localization-audit）：21 passed
  - 回归状态（2026-08-05，跨会话并行 / D-062）：
  - `pytest tests/test_providers.py`：29 passed（含双线程独立 stream 客户端、Connection error 重试）
  - `pytest tests/test_openai_responses.py tests/test_model_errors.py tests/test_provider_router.py`：68 passed
  - `npm test -- --run src/sessionResume.test.ts`：8 passed（含 WS 事件 session 绑定过滤）
  - 回归状态（2026-08-04，后台对话继续 / 回切追齐）：
  - `pytest tests/test_server.py::test_ws_ready_reports_running tests/test_session_events.py`：7 passed
  - `npm test -- --run src/sessionResume.test.ts src/itemsFromMessages.test.ts`：13 passed
  - 回归状态（2026-08-05，`/` 技能列表滚动）：
  - `npm test -- --run src/components/Composer.skills.test.tsx`：9 passed
  - 回归状态（2026-08-05，`/` 介绍优先搜索）：
  - `npm test -- --run src/slashSkillMatch.test.ts src/components/Composer.skills.test.tsx`：18 passed
  - 回归状态（2026-08-05，D-066 智能体拆包联装）：
  - `pytest tests/test_persona_package_install.py tests/test_persona_connections.py::test_persona_detail_endpoint tests/test_persona_loading.py tests/test_persona_registry.py`：26 passed
  - 回归状态（2026-08-05，D-069 工作区合成 + 冲突批量/汉化）：
  - `pytest tests/test_persona_package_install.py`：9 passed（含顶层 AGENTS 等模板不误装、MEMORY.md 进提示词、无 IDENTITY 时 AGENTS.md 仍可作普通 persona）
  - `npm test -- --run src/localization-audit.test.ts src/i18n.test.ts`：22 passed
  - 真实 `serenity-full-package.zip` 探针：合成 `serenity`，composed_from 含 IDENTITY/SOUL/AGENTS/USER/TOOLS/MEMORY
  - 回归状态（2026-08-05，智能体 UX + Mermaid 边标签）：
  - `pytest tests/test_skills.py::test_build_engine_chat`：passed（含 `_DIAGRAM_GUIDANCE`）
  - `npm test -- --run src/mermaidEdgeLabels.test.ts src/components/Sidebar.test.tsx`：10 passed
  - 规格：`docs/superpowers/specs/2026-08-05-chemclaw-agents-mermaid-labels-design.md`；决策 D-063–D-068
  - 回归状态（2026-08-05，空态/详情/zip 修补）：
  - `npm test -- --run src/components/Sidebar.test.tsx src/localization-audit.test.ts`：26 passed
  - `pytest tests/test_persona_package_install.py`：6 passed
  - ✅ 界面语言：`useI18n` 无 Provider 时回退改为 zh-CN（不再是 en-US）；一次性把误落在英文的 `chemclaw.locale` 恢复为简体中文（设置里仍可改回 English）；空态任务文案收入 `intro.*` 词条
  - ✅ 设置页语言卡片：标题独占一行、下拉按内容宽度左对齐换行，排版与「主题」卡片一致
  - 回归状态（2026-08-05，步骤/产物/Mermaid 提示）：
  - `npm test -- --run src/components/Transcript.test.tsx src/components/Markdown.test.tsx src/localization-audit.test.ts`：43 passed
  - 回归状态（2026-08-05，步骤组生命周期 D-070）：
  - `npm test -- --run src/components/Transcript.test.tsx`：21 passed
  - ✅ ApiHub 一等提供商（D-071）：设置「模型」置顶 `ApiHub CN` / `ApiHub Intl`；独立密钥；共用云图标；新鲜默认 `apihub-cn:deepseek-v4-flash`（不迁移已有 prefs）
  - 回归状态（2026-08-05，ApiHub providers）：
  - `pytest tests/test_providers.py tests/test_provider_router.py tests/test_model_errors.py tests/test_settings.py`：相关用例通过（`test_config` 中 symlink 测因 Win 权限失败，与本改动无关）
  - ✅ 产业链龙虾内置（D-072）：id `chain-lobster`，显示名「产业链龙虾」；13 默认 Skill；空态三条通俗推荐；全局 M4 Mermaid + G4 grilling 指针；过程 Skill 全量 bundled（superpowers + mattpocock）不挂默认 `skills:`；默认新建对话仍为 ChemClaw/`cowork`
  - 回归状态（2026-08-05，D-072）：
  - `pytest tests/test_chain_lobster.py tests/test_skills.py::test_build_engine_chat tests/test_persona_loading.py tests/test_persona_registry.py`：22 passed
  - `npm test -- --run src/localization-audit.test.ts src/i18n.test.ts`：22 passed
  - `scripts/vendor_process_skills.py` 修复：相对路径隐藏段跳过（避免 Windows `.chemclaw-dev` 误杀）；bundled 含 `grilling`/`grill-me`/`grill-with-docs`/`brainstorming` 等
  - 回归状态（2026-08-06，Mermaid 失败补救 D-074）：
  - `pytest tests/test_mermaid_repair.py`：7 passed
  - `npm test -- --run src/components/MermaidBlock.test.tsx src/components/Markdown.test.tsx src/localization-audit.test.ts src/i18n.test.ts`：47 passed
  - 规格：`docs/superpowers/specs/2026-08-06-chemclaw-mermaid-repair-design.md`；计划：`docs/superpowers/plans/2026-08-06-chemclaw-mermaid-repair.md`
  - 回归状态（2026-08-06，D-075 Agent Runtime A–C + 撤销任务进度 md）：
  - `pytest tests/test_artifact_walk.py tests/test_outbound_clip.py tests/test_mcp.py tests/test_compaction.py`：39 passed
  - `npm test -- --run src/components/RightRail.artifacts.test.tsx src/localization-audit.test.ts src/i18n.test.ts`：24 passed
  - 规格：`docs/superpowers/specs/2026-08-06-chemclaw-agent-runtime-ux-design.md`；计划：`docs/superpowers/plans/2026-08-06-chemclaw-agent-runtime-ux.md`（里程碑 D 待做；任务进度 md 已按产品决定撤销）
  - MCP 超时运维：`CHEMCLAW_MCP_TOOL_TIMEOUT=120` 后重启 sidecar（默认 30s 暂不回滚）
  - 回归状态（2026-08-11，D-120 化工社 SVG 落盘）：
  - `pytest tests/test_huagongshe_provider.py tests/test_public_api_lookups.py`：16 passed（`--basetemp=.pytest-tmp/huagongshe-svg`）
  - `fetch_huagongshe_svg` 回包无 SVG 正文；产物写入 `huagongshe_assets/`；压缩成功 notice 已中文化
  - 回归状态（2026-08-11，D-121 压缩硬裁提示）：
  - Trim 文案改为「上下文已自动精简以继续」；摘要失败二次 `tight_span`；`pytest tests/test_compaction.py tests/test_compaction_engine.py`：**32 passed**
- 回归状态（2026-08-03）：
  - `pytest tests/test_engine.py`（空流 + 流式 + 无工具）：3 passed
  - `pytest` stream 重试/回退 + model errors：12 passed
  - `npm test`（i18n + localization-audit）：21 passed
  - `npm test -- --run src/navArtifactPreview.test.ts`：4 passed
  - Mermaid：`mermaidExports` + `MermaidBlock` + `Markdown` 定向单测（含 theme `neo` 断言与「同文案重渲染不重复 mermaid.render」）；真实链路探针：scrollHeight 稳定、滚轮可到页底、5s 内无图卸载
  - `npm run build` 通过（含 mermaid.core chunk）
  - UpdateBanner 单测因 ChemClaw 关闭自动更新而预期失败（非回归）

## 下一道门禁

1. 用户在 `chemclaw-UI` 打开界面验收：品牌 ChemClaw、默认中文、主导航「智能体」、技能页、Mermaid neo、新建对话 ▾ 中文选择器、空会话主标题「与 xxx 畅谈」随 ▾ 变化、智能体页 Sliders 详情、zip 联装（先重启服务）。
2. 验收满意后删除旧 `chemclaw-design` worktree（`git worktree remove`）；在此之前勿在旧树继续开发。
3. 二期：智能体非内置编辑 / 内置另存为 / 本会话切换+按条 agent_id；对话挂载条；依赖型 Skill 安装器（D-019）。
4. 销售主线含 D-105/D-109/D-127 HubSpot、D-106 SAM、D-108/D-110 海关、**D-113—D-120**（公开查询 + VAT/汇率/维基 + **化工社只读/写反应/SVG 落盘**）、内容重构 **D-128 M3**。**用户侧**补勾 D-108/109/110/127。**下一刀须点名**：① 合集 P0；②（可选）确认打安装包以补验 M3 frozen `load_skill`。

## 文档索引

- [Cursor 完整工程交接（Agent Harness 后续 Phase 3—6）](CURSOR_HANDOFF_2026-08-20.md)
- [完整产品设计](../superpowers/specs/2026-07-29-chemclaw-product-design.md)
- [销售增长智能设计（D-086—D-112）](../superpowers/specs/2026-08-07-chemclaw-sales-growth-intelligence-design.md)
- [外贸拓客内置能力包计划](../superpowers/plans/2026-08-07-chemclaw-export-sales-builtin-pack.md)
- [内贸拓客内置能力包计划](../superpowers/plans/2026-08-07-chemclaw-domestic-sales-builtin-pack.md)
- [商机雷达内置能力包计划](../superpowers/plans/2026-08-07-chemclaw-opportunity-radar-builtin-pack.md)
- [外贸转化内置能力包计划](../superpowers/plans/2026-08-07-chemclaw-export-engagement-builtin-pack.md)
- [PubChem 化学身份 Provider 计划](../superpowers/plans/2026-08-07-chemclaw-pubchem-identity-provider.md)
- [GLEIF 法定主体 Provider 计划](../superpowers/plans/2026-08-09-chemclaw-gleif-legal-entity-provider.md)
- [询盘转报价内置首包计划](../superpowers/plans/2026-08-09-chemclaw-inquiry-to-quote-builtin-pack.md)
- [退役 GUI 客户清单侧栏（D-168）](../superpowers/plans/2026-08-19-chemclaw-retire-lead-list-nav.md)
- [客户清单工作台计划（D-098，侧栏已退役）](../superpowers/plans/2026-08-09-chemclaw-lead-list-workbench.md)
- [SMTP 发送审批计划（D-099）](../superpowers/plans/2026-08-09-chemclaw-smtp-send-approval.md)
- [HubSpot CRM 审批写入（D-105）](../superpowers/plans/2026-08-10-chemclaw-hubspot-crm-write-approval.md)
- [HubSpot 创建联系人审批（D-109）](../superpowers/plans/2026-08-10-chemclaw-hubspot-create-contact-approval.md)
- [HubSpot 字段更新/任务创建审批（D-127）](../superpowers/plans/2026-08-12-chemclaw-hubspot-crm-update-task-cta.md)
- [国内登记 Provider（D-100）](../superpowers/plans/2026-08-09-chemclaw-cn-registry-provider.md)
- [TED / Comtrade 队列](../superpowers/plans/2026-08-09-chemclaw-next-providers-queue.md)
- [TED TenderProvider（D-101）](../superpowers/plans/2026-08-09-chemclaw-ted-tender-provider.md)
- [SAM.gov TenderProvider（D-106）](../superpowers/plans/2026-08-10-chemclaw-sam-tender-provider.md)
- [Comtrade TradeFlowProvider（D-103）](../superpowers/plans/2026-08-09-chemclaw-comtrade-provider.md)
- [海关企业级文件 Provider（D-108）](../superpowers/plans/2026-08-10-chemclaw-customs-enterprise-file-provider.md)
- [海关 XLSX 支持（D-110）](../superpowers/plans/2026-08-10-chemclaw-customs-xlsx.md)
- [单位与不确定度单包（D-111）](../superpowers/plans/2026-08-10-chemclaw-uncertainty-and-units.md)
- [化工社合集 Triage（D-112）](HUAGONGSHE_SKILL_TRIAGE.md)
- [API 公开查询（D-113 / D-114）](../superpowers/plans/2026-08-10-chemclaw-public-api-lookups.md)
- [public-apis 短名单连通探针（D-115/D-116）](PUBLIC_API_PROBE_2026-08-10.md)
- [合集 Triage 计划（D-112）](../superpowers/plans/2026-08-10-chemclaw-huagongshe-skill-triage.md)
- [客户清单进阶 UX（D-102）](../superpowers/plans/2026-08-09-chemclaw-lead-list-advanced-ux.md)
- [CRM/科研远期说明](../superpowers/plans/2026-08-09-chemclaw-crm-and-research-defer.md)
- [化工多平台内容重构交接](HANDOFF_PLATFORM_REWRITE.md)
- [化工内容重构内置能力包计划（D-104/D-107 · M1+M2 已落地）](../superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md)
- [化工内容重构说明](platform-rewrite/README.md)
- [已批准决策](DECISIONS.md)
- [领域术语](DOMAIN.md)
- [销售主线门禁验收（点检清单）](GATE_VERIFY_2026-08-09.md)
- [客户清单点检示例 JSON](fixtures/smoke-lead-list.json)
- [测试、开发环境与源码预览](TESTING.md)
- 仓库级协作入口：`AGENTS.md`
- [阶段 1 实施计划](../superpowers/plans/2026-07-29-chemclaw-first-vertical-slice.md)
- [Agent Runtime 提速规格（D-075）](../superpowers/specs/2026-08-06-chemclaw-agent-runtime-ux-design.md)
- [Agent Runtime 里程碑 D 计划](../superpowers/plans/2026-08-06-chemclaw-agent-runtime-ux.md)

## 路线图摘要

1. 项目文档、Git/Worktree 和测试基线。
2. ChemClaw 品牌、中文化、真实 Skill 页面、Serenity 代表 Skill、对话挂载和 Mermaid 闭环。
3. 完整 Skill/Agent 平台与第一个可日常使用的 ChemClaw 安装程序。
4. SAG 检索、备份恢复和大数据导入。
5. 2D、3D 和探索模式。
6. 双链化工百科、标准产业链图和交互价格图。

## 当前环境检查

- 日常开发请使用 **`chemclaw-UI` Worktree**；不要从旧聊天记录推断分支，以本节当前状态和 `git status` 为准。
- Python 下载缓存、开发状态和 pytest 临时目录统一放在 `D:\OpenWorker\.chemclaw-dev`。
- 拉 upstream：`git fetch upstream main`（remote：`https://github.com/andrewyng/openworker`）。
- 完整版本、命令、测试数字、启动顺序和已知缺陷以 [TESTING.md](TESTING.md) 为准。

## 新任务推荐开场

> 继续 ChemClaw 阶段 1（当前分支与 worktree 均为 `chemclaw-UI`）。请先阅读 AGENTS.md、项目控制台、已批准规格、TESTING.md 和实施计划。不要覆盖尚未提交的 D-168—D-172；一次只执行指定 Task。
