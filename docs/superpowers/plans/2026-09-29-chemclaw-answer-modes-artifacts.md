# 回答模式与交付整改实施计划

状态：**第 1 项、第 2 项源码与离线验收已完成，真实性能/质量待验收**。规格：[诊断与设计](../specs/2026-09-29-chemclaw-answer-modes-artifacts-design.md)。本轮一个独立小任务：快速/深度执行模式；不调用真实模型或更换正在运行的程序。

本次完成：阅读当前状态/批准设计/决策/领域及稳定性和速度计划；检查执行、搜索、重复提醒、图表和报告交付源码；读取四个公开 GitHub 项目的相关资料；记录证据与未确认项。保留既有 `.gitignore` 和未跟踪文件。

## 建议逐项验收顺序

### 第 2 项实施细化（用户已要求开始下一项）

新增独立会话字段 `research_depth=fast|deep`，不复用权限 mode。新手动对话默认 fast，旧记录/定时任务/新建 Channel 后台会话维持 deep。fast 每段共享 6 次成功主/子模型调用，最后 1 次留主助手无工具整理，第三轮起提示收敛；deep 保留 300/15。请求失败/工具内部超时沿用现有策略，首版不承诺墙钟时限。

**用户本轮纠偏已采纳**：快速不等于缩小深研调用次数。第一轮就在原模型请求中要求确定最小完整交付、必要证据、最短路径与停止条件；优先已有材料和直接来源，为必要产物生成/验证预留步骤。不增设规划模型调用，不全面铺开后等额度截断。正常无工具最终答案（包括最后一轮）沿用 completed，不因达到第 6 轮强制暂停；仍有未执行工具、空答案、截断、模型错误或未完成子任务时保留相应暂停/等待状态。完成状态不等于事实质量自动验收，真实质量仍须第 5 项对照。

选项保存、WS ready/变更广播、每次发送/继续携带选择；运行中拒绝修改，选择本身不续额度。任务预算保存实际深度，普通消息、审批恢复不新增预算；明确继续时才按当前选择增加下一段额度，历史消耗保留。能力探测支持 reasoning_effort 时按模式设置低/高默认，用户已有模型参数优先，未知能力不发新参数。保持全部授权工具可发现；搜索去重/每查询限制留第 3 项。本轮验收覆盖持久化、旧记录、跨会话与重连、快答收尾/继续、共享预算、权限及中英文界面；不调用真实账号、不重启或发布。

1. **基线与速度定位**：复用 TurnTrace 加入各段时标，固定题库与质量评分；在独立测试状态中比较最小模型请求和完整引擎。真实账号调用按当前门禁另行授权，先离线注入延迟验证。不能以缩短提示或隐藏思考冒充解决上游等待。
2. **快速 / 深度的真实执行合同**：在现有入口/TurnPlan/预算保存显式研究深度，接通会话保存、重连、继续、模型能力参数与界面；保留基础联网、按需工具发现及原权限系统。先交付一个可独立验证的快速模式，不恢复业务关键词裁工具或强制委派。
3. **搜索收敛**：任务内 URL/查询复用，正文选择，证据缺口和停止原因；按模式设置有界工作预算，留综合余量。验证重复改写、真实冲突、新鲜度和失败重试，不用纯字符串去重误挡有价值补查。
4. **确定性 HTML 交付**：先封装现有 MD + ChartSpec → HTML，稳定主题、产物注册和结构化验证返回；同一内容直接预览/导出，减少模型搬文件。验证中文路径、空/缺文件、恢复/幂等、CDN 不可用、移动端和沙箱。只有此步通过后才修改默认报告交付文案。
5. **质量与真实对照**：模型不变比较工具轮次、tokens、耗时与盲评分；供应商对照单独进行。评测快答、深研、HTML、PNG，并回归 MCP、权限、审批、Channel 与定时任务。每项小提交、开关可回退；真实验收未通过不构建正式安装包。

第 2 项源码与离线验收完成；第 3—5 项尚未开始实现，授权仍有效，后续按独立任务推进。第 1 项真实模型/屏幕/质量对照待测；不能把离线测试通过当成首段目标达标。第 4 项作为独立交付改进，不必等待复杂深研改造完成。

## 第一项源码实施与离线验收（2026-09-29）

- 复用 TurnTrace 新增逐次主模型调用计时；生产 OpenAI 兼容 SDK 使用 request/response hook，不把观测字段传入模型参数。不同请求/线程隔离，停止后冻结；参数重试每次 HTTP 分列，空缺时标不猜测。旧 trace 兼容，仍只保存数值/枚举，无正文、URL、凭据。
- 增加工具批次（含审批）的墙钟时间、压缩阶段时间、引擎首正文、缓存 token 与已报告 usage 次数。并行工具不累计成串行等待；引擎首正文不冒充屏幕显示或有用结论。
- 固定 12 条 [评测题目](../../chemclaw/fixtures/answer-benchmark-cases.json)，包含卓创、HTML、PNG、失败与恢复；`scripts/summarize_answer_benchmark.py` 仅读导出的 JSON，按配置/题目/模型/离线或真实类型分组，报告样本数、中位数、状态、质量，缺失不计零，样本不足 20 不给 P95。完整 [口径与使用说明](../../chemclaw/answer-benchmark.md)。
- 新增 `tests/test_answer_latency.py` **10 passed**。真实 SDK + MockTransport 验证注入时标：准备 10ms、响应头 40ms、上游思考 60ms/content 100ms、结束 140ms（全部为离线控制值，**不是产品实测速度**）。另测兼容暂存、参数重试、失败后重试、停止及迟到响应、旧记录、汇总缺失值与数据分组。
- 最终 11 文件组合 **197 passed / 4 failed**：answer_latency、turn_tracing、providers、compat_incremental_stream、engine、runtime_budget、runtime_resume、turn_instrumentation、agent_harness_api、provider_router、compaction_engine。日志在本机 `.tmp-answer-latency-final/`。后续汇总指标补充后，新增测试文件再跑 **10 passed**（与组合重叠，不累加）。
- 4 项失败均已核对 `.tmp-stability-offline/results.json` 同名同类既有基线：`test_provider_extras_persist_on_message_and_survive_outbound`（尾部 checkpoint notice 被当 assistant，缺 `_gemini`）；`test_scenario_list_and_preview_use_live_planner_without_side_effects`（旧场景列表少 chemical_market_report）；`test_invalid_explicit_scenario_is_422_for_rest_and_input_rejected_for_ws`（旧 Scenario 硬路由期望 422，当前通用执行返回 200）；`test_ws_accepts_scenario_id_and_emits_trace_summary`（旧场景投影期望 chemical_identity，当前为空）。未恢复历史硬路由、未修改这些既有测试，不称全仓通过。
- `git diff --check` 通过。未修改 GUI 行为，因此未运行前端测试。没有真实模型/搜索调用、服务重启、消息外发、依赖安装、合并 main 或正式构建安装。

已知限制：入口 MCP 准备、实际屏幕绘制、有用结论时间及真实质量尚未测量；辅助压缩模型请求还未纳入主请求明细和 token 汇总。当前运行程序未加载这些源码，快速模式与 HTML 默认交付均未上线。

## 第二项源码实施与离线验收（2026-09-29）

- `research_depth` 贯穿会话 SQLite 迁移、Manager、WS ready/选择确认/发送/继续、TurnPlan preview 和共享预算快照；旧库真实缺列迁移为 deep。GUI 等服务端 ready 后显示独立中英文选择器，未就绪/运行中不可切换，重连和跨会话不串选择。发送/继续携带可见选择，并在同一事件循环无广播让出间隙地选定及认领任务。
- 首轮短路径策略进入原模型请求；后续只保留简短收敛提醒，避免每轮重复长规划。快速第 6 次只整理已有证据，正常无工具答案可完成；空答、截断、错误、强行工具调用、未完成子任务沿用真实暂停/等待。模型完成标志不等于答案事实质量已验证。工具权限、审批、显式禁止联网、只读子任务和定时任务继续沿用原机制。
- 预算持久化实际模式和累计 limit；切换按钮不续费式增加额度、普通消息/自动恢复不增段。明确继续按新选择分配一个新段，历史消耗保留，旧段未使用额度不扩大新快速段。旧 managed task 可在明确继续时转为新合同；自定义裸引擎预算保留兼容。
- 新增 `test_research_depth.py` **23 passed**，覆盖首轮策略、第三轮综合、正常最后一轮交付、异常收尾、主子共享、混合段继续、旧库迁移、空会话保存、后台默认、WS 选择/运行拒绝、支持/未知模型参数。原长任务集成测试显式选择 deep；自动化/Channel 的缩小预算测试桩接收新增关键词参数，不改变其原验收目标。
- 后端最终 **128 passed / 0 新失败**，17 文件按最后一次结果去重：research_depth、task_group_integration、automation_recovery、subagent_readonly、deliver_mcp、turn_tracing、runtime_budget、runtime_acceptance、durable_resume、task_budget、runtime_resume、model_selection、execution_profile、turn_planner、session_events、tools_permissions、answer_latency。日志：`.tmp-research-depth-final/`，修复后的 6 文件 `.tmp-research-depth-verified/`；首轮策略文本精简后单文件再验 `.tmp-research-depth-policy/`，重叠结果不累加。
- 扩展 `test_server.py` **37 passed / 7 failed**（`.tmp-research-depth-2/`）。7 项均核对 `.tmp-stability-offline/results.json` 同名同类既有失败：两项 artifact 错误枚举/旧英文断言、Windows POSIX 文件权限断言、checkpoint 尾部断言、workspace command trust 和 always allow 的旧权限假设、Google 中文错误/旧英文断言。没有恢复旧权限或文案来使其通过。
- GUI `useResearchDepth`、`useSessionModel`、`Composer.skills` **17 passed**；`npx tsc --noEmit` 通过。新测试覆盖待 ready、重连/迟到确认、运行拒绝回滚、跨会话选择、每次发送与继续携带模式、选择器功能与禁用态。`git diff --check` 通过。
- 未调用真实模型/搜索，未重启开发服务或更新正式程序，未安装/发布/合并 main。用户真实任务是否更快、更完整尚待同模型对照；网络等待及单个工具超时未在此项改变，因此不承诺秒出。下一项为任务内查询/URL 复用与证据停止；HTML 稳定交付仍为独立第 4 项。
