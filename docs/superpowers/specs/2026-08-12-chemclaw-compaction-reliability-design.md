# ChemClaw 上下文压缩可靠性设计

- 日期：2026-08-12
- 状态：待用户复核
- 范围：OPE-27 摘要调用、摘要输入预算、失败诊断与确定性降级

## 1. 背景与根因证据

ChemClaw 当前在达到阈值后调用一次摘要模型，失败后以更小的字符预算重试，仍失败则 Trim。生产现象是几乎只出现「上下文已自动精简以继续」。源码核查确认：

- 普通摘要 span 最多 400,000 字符，紧缩重试仍可有 80,000 字符；预算不读取摘要模型的真实上下文窗口。
- 摘要输出上限固定为 3,000 tokens；提示要求八个章节并重复列出全部用户消息。
- 只接受 `AssistantTurn.text`；`text` 为空且 `reasoning` 非空时仍统一报空摘要。
- 摘要默认复用会话模型与 Provider；两次尝试只改变输入，不改变模型、超时或输出行为。
- warning 未记录输入大小、耗时、finish reason、可见正文/推理长度和错误分类。

因此降低主上下文触发比例只能缓解首次触发过晚，不能修复摘要调用本身。

## 2. 目标

1. 每次摘要失败都能归类为输入超限、reasoning-only、空响应、不完整输出、超时、限流、网关错误或其他异常。
2. 摘要请求的输入预算由摘要模型上下文窗口决定；未知模型使用保守上限，不再发送接近 400,000 字符的请求。
3. 摘要默认只进行一次受预算约束的 LLM 调用；第二次使用更小投影。保留现有独立 `compaction_model` 路由能力，允许选择不同 Provider 的非推理模型。
4. 两次 LLM 摘要都失败时，先生成确定性 continuity ledger，再继续；canonical transcript 完全不变。
5. 用户成功文案保持「上下文已自动压缩（较早轮次已摘要）」；确定性降级保持中性文案「上下文已自动精简以继续」，不把机械提取伪装成 LLM 摘要。

## 3. 非目标

- 不替换 OpenWorker/ChemClaw 对话引擎。
- 不删除或改写持久 transcript。
- 不新增向量数据库、长期记忆服务或 SAG 依赖。
- 本首包不实现多次 map-reduce LLM 调用。单次严格投影上线后先用失败分类验证；只有投影确实造成连续性不足时才另案加入分块 LLM 摘要。
- 不改变权限、审批、MCP 或定时任务语义。
- 不在日志中记录用户原文、摘要正文、工具回包或凭据。

## 4. 方案选择

### 4.1 采用：单次严格投影 + 确定性降级

摘要前先把消息转换为压缩事件：用户意图、助手结论、工具名与参数摘要、工具状态、产物路径。工具原文仍是第一裁剪对象。投影按完整消息和 tool pair 边界，从新到旧装入 token 预算。一次正常调用失败后使用更小预算重试；两次失败进入 continuity ledger。

优点是请求数量不增加，最适合当前疑似不稳定的兼容网关；也能用结构化诊断验证后续是否需要 map-reduce。

### 4.2 暂不采用：立即做 map-reduce

map-reduce 能覆盖更多旧历史，但会把一次摘要变成多次网关调用。当前尚不清楚失败来自超限、reasoning-only 还是网关兼容；此时增加调用数会提高成本并放大瞬时失败。预算和诊断稳定后可复用本设计的事件边界与 token 估算另案实现。

### 4.3 不采用：只换默认模型

不同用户配置的 Provider 和凭据不同，不能硬编码一个所有安装都可用的摘要模型。继续保留「会话模型」默认值和现有模型选择器，但设置说明明确建议选择已验证的非推理模型；模型 ID 带 Provider 前缀时继续走独立 endpoint/profile。

## 5. 组件与接口

### 5.1 `SummaryBudget`

在 `coworker/compaction.py` 增加纯数据结构与纯函数：

```python
@dataclass(frozen=True)
class SummaryBudget:
    context_window: int
    input_tokens: int
    output_tokens: int
    safety_tokens: int
    tight: bool = False

def summary_budget(
    context_window: int | None,
    *,
    max_output_tokens: int = 3000,
    tight: bool = False,
) -> SummaryBudget: ...
```

规则：

- 已知模型读取 `providers.matrix.model_context_windows()`。
- 未知模型按 32,000 token context 处理。
- 普通投影输入最多 24,000 tokens；紧缩重试最多 8,000 tokens。
- 始终预留 3,000 输出 tokens、至少 2,000 safety tokens 和系统提示实际估算值。
- 若模型窗口较小，则输入预算继续缩小，绝不让估算的输入、输出和 safety 之和超过窗口。

### 5.2 保守文本 token 估算与事件投影

保留现有主上下文 `estimate_tokens` 行为，避免改变 OPE-27 触发语义；仅为 summarizer 新增保守文本估算：ASCII 约四字符一个 token，中文、其他非 ASCII 字符按至少一字符一个 token 计算，并计入消息标签和 JSON 标点。

`summarizer_messages` 接收 `SummaryBudget`，按完整事件边界裁剪。不得用字符串尾切割制造半个 tool pair。投影规则：

- user：保留文本，单条超长时按预算截断并标明省略。
- assistant：保留可见结论；工具调用只保留工具名和不超过 200 字符的参数摘要。
- tool：保留状态、短预览、产物路径；普通最多 400 字符，紧缩最多 120 字符。
- notice/system/reasoning 原文：不进入摘要正文。
- prior summary 也计入同一预算；超限时保留其较新的有效部分并标明省略。

程序机械保留用户消息，因此 LLM 提示删除「All user messages」章节，改为七节结构，降低输出压力。

### 5.3 `SummaryFailure` 与诊断

```python
class SummaryFailure(RuntimeError):
    reason: str
    input_tokens: int
    input_chars: int
    finish_reason: str
    text_chars: int
    reasoning_chars: int
```

原因至少包含：

- `empty_response`
- `reasoning_only`
- `incomplete_output`
- `context_overflow`
- `timeout`
- `rate_limited`
- `provider_error`

`summarize_span` 不接受 reasoning 作为摘要正文。`text` 为空而 reasoning 非空时抛出 `reasoning_only`；`finish_reason=length` 且输出缺少必要章节时抛出 `incomplete_output`。异常日志只记录元数据：attempt、model、预算、输入字符/token、耗时、reason、finish reason、text/reasoning 长度和异常类型，不记录正文。

### 5.4 摘要调用配置

继续复用现有 `compaction_model`，因此用户可以选不同 Provider 前缀的模型并走独立 endpoint/profile。本首包新增后端设置：

- `compaction_timeout_seconds`，默认 90，范围 15–300。
- `compaction_summary_input_tokens`，默认自动；只有 API/测试使用，不在普通 UI 暴露高级数字框。

引擎用 `asyncio.wait_for(asyncio.to_thread(...))` 限制等待；超时后继续第二次或确定性降级，不阻塞用户。由于 Python 线程中的 SDK 请求不能被强制终止，日志须标记 timeout，且同一 compaction 不再发起超过两次请求。

设置页保留现有摘要模型选择器，说明改为：建议选择稳定返回普通正文的非推理模型；带 Provider 前缀的模型使用该 Provider 配置。

### 5.5 确定性 continuity ledger

新增 `build_deterministic_state(messages, keep_tokens, prior)`，使用与 LLM compaction 相同的合法 boundary，把边界前的 span 机械提取为：

- 最新用户原话列表及累计省略数。
- 最近一次 `todo_write` 的 todo 内容和状态。
- 已写入/修改文件。
- 从工具参数和结构化结果中提取的产物路径。
- 最近命令及退出状态。
- MCP 查询与短结果预览。
- 最近最多三条 assistant 可见结论，每条严格裁剪。
- 使用过的工具列表。

该状态的 `trimmed=True`，`model_used=""`，摘要文案明确这是确定性精简而非 LLM 总结。若无法按 keep budget 选择边界，再复用现有最小 Trim 逻辑。

## 6. 数据流

1. 主 outbound 达到 OPE-27 阈值。
2. 引擎解析摘要模型及其 context window，计算普通 `SummaryBudget`。
3. 生成受预算约束的摘要投影并调用模型。
4. 若得到完整七节可见正文，保存 `CompactionState` 并显示摘要成功文案。
5. 若失败，记录结构化 warning；使用 tight budget 重试一次。
6. 若仍失败，调用 `build_deterministic_state`，显示中性精简文案并继续。
7. `apply_to_outbound` 只改变出站视图；保存、重载和 GUI transcript 继续使用 canonical messages。

## 7. 错误处理

- context overflow：第二次使用 tight budget；仍失败则确定性降级。
- reasoning-only：不暴露或复用隐藏推理；记录原因并进入第二次/降级。运维可据此改选非推理摘要模型。
- 429、5xx、连接错误：当前两次总上限不变；第二次前做短退避，但不弹 Retry 对话框。
- timeout：立即进入下一层；晚到的线程结果不得修改会话状态。
- 非空但缺章节或 `finish_reason=length`：视为不完整，不写入 summary state。
- continuity ledger 构造异常：最后才使用原有最小 Trim，仍不得阻塞 turn。

## 8. 测试与验收

### 8.1 单元测试

- 16k、32k、128k 和未知模型预算均满足 `input + output + safety <= context`。
- 中文、ASCII、JSON 和超长 user/tool 结果投影不超过预算。
- 裁剪不让 outbound 以 tool result 开头，也不拆散 assistant tool call 与结果。
- reasoning-only、空响应、`finish_reason=length` 和 provider overflow 得到不同失败原因。
- continuity ledger 保留 todo、产物路径、命令状态、MCP 查询、最近助手结论与用户原话。
- 旧 `CompactionState` 可以无迁移读取。

### 8.2 引擎测试

- 第一次成功只调用一次摘要模型并显示「上下文已自动压缩（较早轮次已摘要）」。
- reasoning-only 或超时会进行一次 tight 重试；两次失败后得到确定性 state，不出现 QUESTION。
- warning 可用 `caplog` 验证分类和数字字段，且不包含用户原文。
- 强制失败后主模型仍收到 `<compacted-history>`、最新用户要求、todo/产物和近期原文。
- canonical message 数量和原内容在 compaction 前后不变。

### 8.3 回归命令

```powershell
pytest tests/test_compaction.py tests/test_compaction_engine.py tests/test_providers.py
```

若设置页文案或 API 类型改变，再运行：

```powershell
npm test -- --run src/i18n.test.tsx src/localization-audit.test.ts src/components/SettingsView.test.tsx
npm run typecheck
```

## 9. 风险与回退

- 保守预算可能牺牲较老细节；通过用户原话、continuity ledger、产物路径和最近原文尾缓解。
- timeout 不能强杀已进入 SDK 的后台线程；限制每次最多两次并记录指标，后续可在 Provider 层补原生超时。
- 七节格式校验过严可能降低表面成功率；只校验关键标题集合，不要求固定措辞或英文。
- 新日志必须避免正文和凭据；测试专门断言用户样本文本不进入 warning。
- 回退时可撤销新预算/诊断/ledger 代码，旧 `CompactionState` 与 transcript 无需迁移。

## 10. 完成标准

- 摘要请求有模型感知的硬预算，普通路径不再允许 400,000 字符输入。
- 每次失败有无敏感内容的明确分类。
- 两次摘要失败后保留可继续工作的确定性状态，不只依赖 10% 硬裁。
- 摘要成功与确定性精简使用准确的中文文案。
- 定向后端测试通过；若改前端，则 i18n、类型检查和定向前端测试通过。
- `docs/chemclaw/README.md`、`DECISIONS.md` 和 `DOMAIN.md` 在实现完成后同步更新。
