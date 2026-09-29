# 回答模式与交付整改实施计划

状态：**用户已授权开始；第 1 项的后端诊断、题库和离线验收已完成，真实性能基线待测**。规格：[诊断与设计](../specs/2026-09-29-chemclaw-answer-modes-artifacts-design.md)。本轮一个独立小任务：计时、题库及离线验收；不调用真实模型或更换正在运行的程序。

本次完成：阅读当前状态/批准设计/决策/领域及稳定性和速度计划；检查执行、搜索、重复提醒、图表和报告交付源码；读取四个公开 GitHub 项目的相关资料；记录证据与未确认项。保留既有 `.gitignore` 和未跟踪文件。

## 建议逐项验收顺序

1. **基线与速度定位**：复用 TurnTrace 加入各段时标，固定题库与质量评分；在独立测试状态中比较最小模型请求和完整引擎。真实账号调用按当前门禁另行授权，先离线注入延迟验证。不能以缩短提示或隐藏思考冒充解决上游等待。
2. **快速 / 深度的真实执行合同**：在现有入口/TurnPlan/预算保存显式研究深度，接通会话保存、重连、继续、模型能力参数与界面；保留基础联网、按需工具发现及原权限系统。先交付一个可独立验证的快速模式，不恢复业务关键词裁工具或强制委派。
3. **搜索收敛**：任务内 URL/查询复用，正文选择，证据缺口和停止原因；按模式设置有界工作预算，留综合余量。验证重复改写、真实冲突、新鲜度和失败重试，不用纯字符串去重误挡有价值补查。
4. **确定性 HTML 交付**：先封装现有 MD + ChartSpec → HTML，稳定主题、产物注册和结构化验证返回；同一内容直接预览/导出，减少模型搬文件。验证中文路径、空/缺文件、恢复/幂等、CDN 不可用、移动端和沙箱。只有此步通过后才修改默认报告交付文案。
5. **质量与真实对照**：模型不变比较工具轮次、tokens、耗时与盲评分；供应商对照单独进行。评测快答、深研、HTML、PNG，并回归 MCP、权限、审批、Channel 与定时任务。每项小提交、开关可回退；真实验收未通过不构建正式安装包。

第 2—5 项尚未开始实现，授权仍有效，后续按独立任务推进。第 1 项真实模型/屏幕/质量对照待测；不能把离线测试通过当成首段目标达标。第 4 项作为独立交付改进，不必等待复杂深研改造完成。

## 第一项源码实施与离线验收（2026-09-29）

- 复用 TurnTrace 新增逐次主模型调用计时；生产 OpenAI 兼容 SDK 使用 request/response hook，不把观测字段传入模型参数。不同请求/线程隔离，停止后冻结；参数重试每次 HTTP 分列，空缺时标不猜测。旧 trace 兼容，仍只保存数值/枚举，无正文、URL、凭据。
- 增加工具批次（含审批）的墙钟时间、压缩阶段时间、引擎首正文、缓存 token 与已报告 usage 次数。并行工具不累计成串行等待；引擎首正文不冒充屏幕显示或有用结论。
- 固定 12 条 [评测题目](../../chemclaw/fixtures/answer-benchmark-cases.json)，包含卓创、HTML、PNG、失败与恢复；`scripts/summarize_answer_benchmark.py` 仅读导出的 JSON，按配置/题目/模型/离线或真实类型分组，报告样本数、中位数、状态、质量，缺失不计零，样本不足 20 不给 P95。完整 [口径与使用说明](../../chemclaw/answer-benchmark.md)。
- 新增 `tests/test_answer_latency.py` **10 passed**。真实 SDK + MockTransport 验证注入时标：准备 10ms、响应头 40ms、上游思考 60ms/content 100ms、结束 140ms（全部为离线控制值，**不是产品实测速度**）。另测兼容暂存、参数重试、失败后重试、停止及迟到响应、旧记录、汇总缺失值与数据分组。
- 最终 11 文件组合 **197 passed / 4 failed**：answer_latency、turn_tracing、providers、compat_incremental_stream、engine、runtime_budget、runtime_resume、turn_instrumentation、agent_harness_api、provider_router、compaction_engine。日志在本机 `.tmp-answer-latency-final/`。后续汇总指标补充后，新增测试文件再跑 **10 passed**（与组合重叠，不累加）。
- 4 项失败均已核对 `.tmp-stability-offline/results.json` 同名同类既有基线：`test_provider_extras_persist_on_message_and_survive_outbound`（尾部 checkpoint notice 被当 assistant，缺 `_gemini`）；`test_scenario_list_and_preview_use_live_planner_without_side_effects`（旧场景列表少 chemical_market_report）；`test_invalid_explicit_scenario_is_422_for_rest_and_input_rejected_for_ws`（旧 Scenario 硬路由期望 422，当前通用执行返回 200）；`test_ws_accepts_scenario_id_and_emits_trace_summary`（旧场景投影期望 chemical_identity，当前为空）。未恢复历史硬路由、未修改这些既有测试，不称全仓通过。
- `git diff --check` 通过。未修改 GUI 行为，因此未运行前端测试。没有真实模型/搜索调用、服务重启、消息外发、依赖安装、合并 main 或正式构建安装。

已知限制：入口 MCP 准备、实际屏幕绘制、有用结论时间及真实质量尚未测量；辅助压缩模型请求还未纳入主请求明细和 token 汇总。当前运行程序未加载这些源码，快速模式与 HTML 默认交付均未上线。
