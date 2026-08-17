# ChemClaw 性能、准确性与智能路由完整改造 Plan（Cursor Auto Safe v5）

> 目标仓库：`zoeyzhang233666/openworker`  
> 目标分支：`chemclaw-clean`  
> 执行方式：交给 Cursor Auto **分段执行**；不得一次性跨越 V5 Hard Stop；A–G 每个 HARD STOP 建议使用独立 Cursor 对话窗口  
> 修订原则：在原 Plan 的性能目标上增加“既有能力不可回归”硬约束；Router 只做优化，不得成为产品能力总开关。  
> 核心目标：让 ChemClaw 在普通聊天时接近网页 AI 的即时体验，同时在化工专业事实、法规、安全、实时市场和深度研究任务中保留工具验证与高质量交付能力，并完整保留 Memory、Skills、Plan/ask_user、Resume、Automation、Connectors、MCP、Persona 与 OpenAI-compatible textual tool-call 兼容能力。
>
> **V5 审阅基准说明（2026-08-13）：** 本版修订曾对照 `chemclaw-clean` 当时的真实仓库结构审阅，包括 `Config.max_iterations`、`TurnEngine`、`build_engine()` 的大规模工具注册、OpenAI-compatible streaming buffering/retry 与 textual tool-call salvage。此说明不是固定代码事实；每个 Auto run 仍必须以当时当前仓库为准重新读取和验证。

> **V5 技术安全修订范围：完整沿用 v4 的技术方案与 HARD STOP A–G，不改变 Router / Streaming / Retry / Budget / Tool Policy / Finalization 技术目标。v5 只进一步强化三类执行保险：**
>
> 1. **HARD STOP C 的 reasoning / soft-budget 基础设施对 legacy path 默认 inert**：在 Router 未显式启用、或本轮没有显式 `ExecutionProfile` 时，不得因为新增 32/50 soft target / Converge / Deliver plumbing 改变原有 request execution。
> 2. **所有 risky built-in defaults 在 A–G + final regression 完成前始终保持 OFF**：阶段内只允许测试显式 ON/OFF；不得在 HARD STOP E/F/G 中“顺手”把默认值翻 ON。默认启用必须放到独立 rollout run，一次只启用一个故障域。
> 3. **跨窗口执行日志成为正式交接机制**：每个 HARD STOP 后允许、且建议新开 Cursor 对话；新 run 必须用仓库治理文件 + Git + execution log 恢复事实，不依赖旧聊天上下文。
>
> **沿用的 5 个高风险技术修订：**
> 1. 保留现有 `max_iterations=150` 作为 legacy hard ceiling；`32/50` 改为 AGENT/DEEP 的 soft target，不再作为默认硬砍能力。
> 2. `max_retries=0` 只用于 ChemClaw 自己接管 retry 的 streaming client；non-stream `complete()` 不全局关闭 SDK retry，除非同步补齐等价 transport retry。
> 3. FAST_CHAT/KNOWLEDGE 改为 **pure-answer 正向白名单**：只有能明确证明不需要产品动作/工具能力时才 `tools=None`；不确定就保留 legacy AGENT 能力。
> 4. `NO_EXTERNAL_NETWORK` / `NO_SEARCH` 使用统一的内部工具分类 helper；未知工具在禁网时默认不暴露，但在普通 AGENT/DEEP 中默认保留，避免新增 connector/MCP 被静默误伤。
> 5. structured-tools true streaming 与 Emergency Finalization 都必须最后实现/测试，并保留 kill switch；A–G + final regression 期间 built-in default 仍保持 OFF，默认启用只允许在独立 rollout run 逐项评估；任何 capability gate/兼容性测试失败时保持保守旧行为。

> **V5 强制的 12 个 Cursor Auto 防破坏保险（优先级高于普通实现建议）：**
> 1. **Router 总 kill switch**：新增语义清晰的 `request_routing_enabled`（具体命名可遵循当前 Config 风格）。关闭时必须跳过新 Router / classifier / route fast-path，恢复本 Plan 之前的 legacy request execution 选择，不得因为 Router 代码已存在而改变旧能力。
> 2. **Tool Projection 独立 kill switch**：新增 `tool_projection_enabled`。关闭时 Router 即使仍可观测/打点，也不得把 provider-visible schema 裁窄为 `tools=None` 或子集；应回到 legacy full-schema exposure（仍受原有 agent/persona/connector/session 注册边界约束）。Router kill switch 与 projection kill switch 必须分别测试，不能只用一个开关覆盖两个故障域。
> 3. **每个新 Auto run 重新同步仓库治理**：不能只读 `AGENTS.md` 一次。每次 HARD STOP 后的新 run 都必须按当前 `AGENTS.md` 要求重新读取 `docs/chemclaw/README.md`、产品设计、`DECISIONS.md`、`DOMAIN.md` 和当前相关实施计划；若这些文件与本文冲突，以仓库当前已批准约束为准，并停止报告冲突，不得静默自行裁决。
> 4. **Phase Scope Lock**：每段开始先列出“预计修改文件/符号”。除测试、必要配置和与当前段直接相关的最小接线外，不得预改后续 Phase 文件。若发现需要超出预计范围的跨模块重构，先停止并汇报原因，不得以“顺手整理架构”为由扩散修改。
> 5. **Baseline Failure Fingerprint**：每段开始记录 baseline SHA/status、已有失败用例名与失败摘要；段末必须区分 `existing failure`、`new failure`、`not run`、`environment-blocked`。`skip` / `xfail` / 无法启动环境不能被汇报成“能力已验证通过”。
> 6. **Rollback Point**：每个 HARD STOP 都必须产生可回退边界。若工作区干净且不混入用户已有改动，优先形成一个小型本地 checkpoint commit；若不能安全提交，则至少保存当前 SHA、`git diff --stat`、完整 diff/patch 获取方式。**禁止自动 push、merge、tag、rebase 或覆盖用户已有未提交修改。**
> 7. **Provider-visible Tool Schema Parity Snapshot**：在 HARD STOP D 之前记录代表性 agent/persona/session 的 legacy provider-visible tool names；HARD STOP E 必须对比 projection 后结果。普通 AGENT/DEEP 在没有明确 ToolPolicy 限制时，任何未被安全分类的新 `extra_tools`、connector、MCP、动态工具都不得因分类表遗漏而静默消失。
> 8. **Silent Capability Loss = Regression**：即使 pytest 全绿，只要 provider schema、pending-state handling、实际 product action 或 UI smoke 表明旧能力不可达，也按新增 regression 处理，必须回退/收窄本段。不得用“模型理论上还能回答”替代“产品动作真实仍可调用”。
> 9. **HARD STOP E 提前人工产品 smoke**：Capability Preservation Gate 后、structured-tools true streaming 前，必须至少人工/真实应用验证：普通聊天、Memory 写入、forced/default Skill、ask_user/plan/resume、Scheduling/Self-wake（环境允许时）、selected persona、`不要联网 + 本地文件`、至少一个 connector/MCP 或明确记录环境不可用。未完成时只能汇报 `automated gate passed; manual validation pending`，不能宣称 Router/Projection 已完全验收。
> 10. **Risky Built-in Defaults 全程保持 OFF，直到独立 Rollout**：`request_routing_enabled`、`tool_projection_enabled`、structured-tools true streaming、Emergency Finalization 在 HARD STOP A–G 及最终 targeted/full regression/manual smoke 全部完成前，built-in default 必须始终保持 OFF。阶段内测试可以显式 ON/OFF，但任何 HARD STOP 都不得把“测试通过”解释成“允许修改默认值”。兼容性仍有疑问时保持 OFF/legacy-safe 是合格结果。
> 11. **Legacy-Inert Budget / Reasoning Plumbing**：HARD STOP C 只能建立可选的 reasoning / soft-budget / phase plumbing。在 `request_routing_enabled=false`、Router 尚未接线、或没有显式 `ExecutionProfile` 的 legacy execution 中，不能自动套用 AGENT≈32 / DEEP≈50 soft target、Converge/Deliver guidance 或新的 reasoning default。旧 session 应继续只受既有 `config.max_iterations`、model settings 与原状态机控制。真正的 route-specific budget 行为只能由后续 Router 明确产出的 profile 激活。
> 12. **Cross-Window Execution Log / Handoff**：正式执行前建议把本文保存到 `docs/superpowers/plans/2026-08-13-chemclaw-performance-router-v5.md`，并建立 `docs/superpowers/plans/2026-08-13-chemclaw-performance-router-v5-execution-log.md`。每个 HARD STOP 必须追加当前起止 SHA/status、用户原有 dirty changes、实际修改范围、测试分类、kill-switch 状态、rollback point、尚存风险与下一段允许范围。新 Cursor run 必须重新读取该日志，但 **Git + 当前仓库已批准治理文档优先于日志**；三者冲突时 STOP，不得猜测。


> **Cursor Auto 强制规则：** 每个高风险 Phase 都必须“治理/基线同步 → 范围锁定 → 改动 → targeted tests → capability check → rollback point”。出现任何新的能力回归时，停止后续优化，优先回退/收窄当前 Phase；不得为了继续执行 Plan 而放宽旧能力测试。**HARD STOP A–G 即使全部测试通过也必须停止当前 Agent run**，不得自动进入下一段。


> ## ⛔ V5 Cursor Auto Hard-Stop Protocol（执行治理，不改变技术方案）
>
> 本节优先级高于“直接执行完整 Plan”“继续下一 Phase”等任何宽泛执行描述。**章节顺序用于说明设计；真正允许的实施顺序以 Section 65 为准。**
>
> 到达任一 `HARD STOP` 时，无论测试是通过还是失败，Cursor Auto 都必须：
>
> 1. **立即停止实现后续步骤**；不得预先修改下一段文件、不得“顺手”实现下一 Phase；
> 2. 完成本段要求的 targeted tests / capability checks，并记录真实结果；
> 3. 输出本段 `Changed files`、`git diff --stat`、关键 diff 摘要、测试结果、baseline failures / new failures、尚存风险；
> 4. 明确写出：`HARD STOP <ID> reached — downstream phases NOT started.`；
> 5. **结束当前 Agent run**。只有用户之后再次明确发出“继续执行 HARD STOP <ID> 之后的下一段”等新指令，才能继续；
> 6. 不得把“前面测试全绿”“Plan 要求最终全部完成”“上下文还有余量”视为越过 HARD STOP 的授权；
> 7. 如果本段出现新增 capability regression：优先回退/收窄本段，重新测试；若仍不能安全解决，则保留旧行为并在 HARD STOP 报告中说明，**不得带着回归进入下一段**。
> 8. 报告本段开始时实际重读的仓库治理文件及发现的新增约束；不得用上一 run 的记忆替代。
> 9. 报告本段“预计修改范围 vs 实际修改范围”；若实际超出，必须解释为什么仍属于当前段最小必要修改。
> 10. 报告 rollback point（checkpoint commit 或 SHA + diff 获取方式）以及是否存在用户原有 dirty changes；不得覆盖/吸收无关用户改动。
> 11. 测试报告必须显式标识 `PASS / EXISTING FAIL / NEW FAIL / NOT RUN / ENV BLOCKED`；不能把未执行项折算为 PASS。
> 12. 更新 v5 execution log；如果日志与 Git/当前治理文档不一致，明确记录冲突并停止，不能让日志覆盖仓库事实。
>
> **HARD STOP 只限制自动连续执行，不改变任何 Router / Streaming / Retry / Budget / Tool Policy / Finalization 技术目标。**

---

# 0. 总目标

当前 ChemClaw 的问题不是单一的“模型慢”，而是多个机制叠加：

1. OpenAI-compatible provider 的 streaming 当前存在完整 buffering，导致部分路径“看起来完全不流式”；
2. 默认 Agent 最大轮数过高，当前默认约为 150；
3. 简单请求也可能进入完整 Agent Loop；
4. Chat persona 虽然自身没有 tool factory，但 build engine 后仍统一注册大量 research/domain/product-control tools；
5. 普通 greeting 也可能进入 reasoning；
6. SDK retry、ChemClaw retry、fallback 可能叠加；
7. 长任务接近 hard limit 时没有明确收敛阶段；
8. 当前 hard limit 到达后可能只得到 `max_iterations_exceeded`，而没有高质量最终成品；
9. 所有任务共享过多 Tool Schema，增加首 token 延迟和模型工具选择复杂度；
10. 化工领域又不能简单粗暴地“全部禁用工具”，因为 CAS、物性、安全、法规、价格、供应商等事实需要验证；
11. 当前 ChemClaw 还包含 memory、skills、ask_user、plan mode、request_directory、scheduling/self-wake、messaging、connectors、MCP、workspace/file、durable resume 等产品能力；Router 如果只按“回答是否需要外部事实”裁工具，会误伤这些既有能力；
12. OpenAI-compatible 路径还包含 textual tool-call salvage 兼容逻辑，不能为了真流式把 Ollama/Qwen/Hermes 等模型的工具调用文本直接泄露到 UI。

因此本次改造必须同时满足两个目标：

```text
性能优化
+
既有能力兼容
```

Router 的定位必须是：

```text
optimization layer
```

不是：

```text
product capability authority
```

推荐最终决策链：

```text
User request
   ↓
Session / Persona / Pending-State Guard
   ↓
Product Action Gate
   ↓
Explicit Tool / Network Policy
   ↓
Pure-Answer Positive Eligibility Gate
   ↓
Local Fast Gate
   ↓
Chemical / Current-Fact Risk Gate
   ↓
Tiny Classifier（仅真正模糊时）
   ↓
RequestRoute
   ↓
ExecutionProfile
   ↓
Tool Schema Projection
   ↓
TurnEngine / Provider
```

最终系统仍保留五类主要 Route：

```text
                         ┌─────────────────┐
                         │   FAST_CHAT     │
                         │ 0 tools / 1 call│
                         │ reasoning off   │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │   KNOWLEDGE     │
                         │ 0 tools / 1 call│
                         │ stable knowledge│
                         └────────┬────────┘
                                  │
User → Guards → Router → Risk Gate┼──────────────┐
                                  │              │
                         ┌────────▼────────┐     │
                         │    VERIFIED     │     │
                         │ targeted tools  │     │
                         │ hard≈6          │     │
                         └────────┬────────┘     │
                                  │              │
                         ┌────────▼────────┐     │
                         │     AGENT       │     │
                         │ soft≈32 / hard≤cfg │     │
                         └────────┬────────┘     │
                                  │              │
                         ┌────────▼────────┐     │
                         │ DEEP_RESEARCH   │◄────┘
                         │ soft≈50 / hard≤cfg │
                         └─────────────────┘
```

但以下情况拥有比 RequestRoute 更高的优先级：

```text
pending ask_user / approval / plan / durable resume
forced skill / selected persona capability
memory action
schedule / self-wake action
send_message / send_file action
connector / MCP action
workspace / local file action
explicit product-control action
```

这些场景不能因为“请求看起来简单”而被切成 `tools=None`。

核心原则：

> **稳定、低风险、非实时知识直接答；精确、高风险、可验证事实做最小必要验证；真正复杂任务进入 Agent；真正研究任务才进入 Deep Research。**

同时增加兼容性原则：

> **性能路由只能减少不必要的模型成本，不能撤销用户已经拥有、已经选择、已经进入中的 ChemClaw 产品能力。**

> **Streaming 优先改善 `tools=None` 和结构化工具调用路径；任何可能破坏 textual tool-call salvage 的路径必须保留兼容保护。**

---

# 1. 总体完成标准

改造完成后应满足：

```text
输入：“你好”

Route = FAST_CHAT
Classifier calls = 0
Answer model calls = 1
Tool calls = 0
Reasoning shown = 0
Tools sent to provider = None
Streaming = true
```

```text
输入：“什么是苯？”

Route = KNOWLEDGE
Classifier calls = 0（尽可能）
Answer model calls = 1
Tool calls = 0
Streaming = true
```

```text
输入：“苯的 CAS 是多少？”

Route = VERIFIED
Targeted tools ≈ [lookup_chemical_identity]
不暴露无关 tender / VAT / FX / customs / SAM.gov 等工具
最终给出验证后的简短答案
```

```text
输入：“查一下今天苯的国际市场价格”

Route = VERIFIED 或 AGENT
必须使用当前/实时数据工具
```

```text
输入：“深度研究全球苯产业链、供需、主要生产商与未来五年趋势，并多来源交叉验证”

Route = DEEP_RESEARCH
soft target ≈ 50
legacy hard ceiling = config.max_iterations（默认仍为 150）
Explore → Converge → Deliver
```

同时必须满足以下能力保护用例：

```text
输入：“记住我以后喜欢简短回答”

不能：
FAST_CHAT + tools=None

必须：
保留 memory action 能力
完成实际记忆写入流程
```

```text
输入：“明天上午 9 点提醒我联系 BASF”

不能：
FAST_CHAT / KNOWLEDGE 直接文字回答

必须：
保留 scheduling 能力
```

```text
输入：“不要联网，读取本地 CSV 并整理成表”

不能：
因为“不要联网”而 tools=None

必须：
禁止 external network
但仍允许本地 file/workspace tools
```

```text
输入：“不用任何工具，只根据已有知识解释苯的芳香性”

必须：
NO_TOOLS
→ KNOWLEDGE
→ provider tools=None
```

```text
输入：“继续”
前一轮存在 pending plan / ask_user / durable resume / active execution

必须：
优先恢复原有状态机
不能被 Router 当成普通 KNOWLEDGE
```

OpenAI-compatible streaming 还必须满足：

```text
tools=None
→ 真流式

structured tool-call provider
→ 在不破坏工具累积的前提下真流式

textual-tool-call salvage compatibility mode
→ 不允许 <tool_call> / <function=...> 等内部工具调用文本直接显示给用户
```

---

# 2. 非目标

本次不要：

- 重写整个 TurnEngine；
- 引入 LangGraph / CrewAI 等新框架；
- 修改 ToolRegistry 公共接口除非非常必要；
- 重写权限模型；
- 大范围重构前端；
- 修改化工业务 Skill 本身；
- 用另一个大模型完成所有请求分类；
- 让 classifier 每次都运行；
- 给所有请求默认 50/80 轮；
- 删除用户已有 `max_iterations` 配置能力；
- 在没有长期任务回归证据前，把现有 `max_iterations=150` legacy hard ceiling 直接降为 32/50；
- 对所有 OpenAI SDK client 全局设置 `max_retries=0`，却不给 non-stream 路径补等价 transport retry；
- 把 router 结果永久写入 conversation history；
- 把内部 reasoning 当作默认用户可见内容；
- 因本任务顺手修 unrelated failures；
- 让 Router 覆盖 selected persona / forced skill / pending interaction / durable resume 的既有语义；
- 因“不要联网”误禁本地文件、memory、skill、plan、schedule 等非联网工具；
- 为了 true streaming 删除或弱化 textual tool-call salvage；
- 为了性能把 unknown custom OpenAI-compatible endpoint 默认假设成完全支持 structured tool calls；
- 通过 unregister/rebuild Engine 的方式做 per-turn tool filtering；
- 为了通过新测试删除旧能力或降低原有权限/恢复/审批测试覆盖。

---

# 3. Phase 0 — Baseline

修改前运行：

```bash
pytest -q tests/test_providers.py
pytest -q tests/test_engine.py
pytest -q tests/test_engine_stop.py
pytest -q tests/test_config.py
pytest -q tests/test_compaction_engine.py
```

然后：

```bash
pytest -q
```

记录现有失败。

如果存在 unrelated failure：

- 记录；
- 不顺手修复；
- 最终报告说明 baseline failure 与本次修改后的状态。

---

# 4. Phase 1 — P0：实现真正 Streaming，但保留 OpenAI-compatible Tool Salvage 兼容

目标文件：

```text
coworker/providers/openai_provider.py
```

## 4.1 当前问题

当前 streaming path 会先完整消费 provider stream，再统一 yield。

典型结构类似：

```python
buffered = _collect_stream_chunks(...)

for chunk in buffered:
    yield chunk
```

这导致：

```text
上游已经在持续返回 token
↓
ChemClaw 仍无可见输出
↓
整段完成
↓
UI 突然一次性出现
```

这会让：

- text 看起来不流式；
- reasoning 看起来不流式；
- 长回答用户等待感非常明显。

但当前 buffering 还有一个兼容性副作用：

```text
某些 Ollama / Qwen / Hermes / custom OpenAI-compatible 模型
不会正确返回 structured tool_calls
↓
而是把工具调用写进普通 text
↓
流结束后 _maybe_salvage_tool_calls()
↓
把 text 转成 ToolCall，并清空展示文本
```

因此不能简单把：

```python
if text_delta:
    yield StreamChunk(text_delta=text_delta)
```

无条件应用到所有 tools-enabled compat 请求。

否则用户可能先看到：

```text
<tool_call>...
<function=write_file>...
{"name":"lookup_chemical_identity", ...}
```

然后系统才在流结束时发现它其实是工具调用。

这是明确禁止的回归。

## 4.2 第一阶段目标行为

优先保证最重要、最安全的性能收益：

### Path A：`tools is None`

必须真正流式：

```text
provider chunk
↓
立即 parse
↓
立即 yield StreamChunk
↓
TurnEngine
↓
ASSISTANT_DELTA / REASONING_DELTA
↓
UI
```

FAST_CHAT / KNOWLEDGE 的主要性能收益来自这里。

### Path B：tools enabled + provider/model 明确支持 structured tool calls

**V2 执行顺序变更：这一能力不在第一批直接启用。** 第一批先让所有 `tools enabled` 路径继续走安全兼容行为；只有在 Router/Tool Projection 的 Capability Preservation Gate 通过后，才对“明确已知支持 structured tool calls”的 provider/model 开启，并必须保留 kill switch。

最终允许真正流式：

```text
text/reasoning delta → 即时 yield
structured tool_call delta → 内部累积
```

最终保持正确 ToolCall。

### Path C：tools enabled + textual-tool-call salvage 兼容风险未知或已知存在

第一版必须保守：

```text
不允许可能的 tool-call text 泄露到 UI
```

允许以下任一实现，按当前代码最小侵入选择：

1. capability/compat flag：该 provider/model 继续安全 buffering；
2. bounded prefix holdback + incremental textual tool-call parser；
3. 完整 incremental salvage parser；
4. 对 unknown custom compat endpoint 使用安全默认，仅对确认支持 structured tool calls 的路径开启 tools-enabled true streaming。

优先级：

```text
不破坏原有工具能力
>
tools-enabled 路径也必须 100% 真流式
```

也就是说，本次 Definition of Done 不要求牺牲 Qwen/Ollama 工具能力来换取所有工具路径的即时文本。

## 4.3 推荐实现结构

不要继续让 `_collect_stream_chunks()` 成为所有请求的唯一入口。

推荐拆成：

```python
def _stream_structured_chunks(...):
    ...
```

以及兼容路径，例如：

```python
def _stream_requires_safe_tool_salvage(...):
    ...
```

或保持现有 `_collect_stream_chunks()` 作为兼容 fallback。

在真正流式路径中逐 chunk 累积：

```python
text_parts = []
reasoning_parts = []
tool_accum = {}
finish_reason = None
usage = None

visible_output_emitted = False
provider_progress_seen = False
tool_progress_seen = False
```

逻辑：

```python
for chunk in upstream_stream:
    parse usage

    if chunk contains any semantic provider delta:
        provider_progress_seen = True

    if reasoning_delta:
        reasoning_parts.append(reasoning_delta)
        visible_output_emitted = True
        yield StreamChunk(reasoning_delta=reasoning_delta)

    if text_delta:
        text_parts.append(text_delta)
        visible_output_emitted = True
        yield StreamChunk(text_delta=text_delta)

    if structured tool_call delta:
        tool_progress_seen = True
        accumulate tool calls

    if finish_reason:
        finish_reason = ...
```

stream 正常结束后：

```python
turn = AssistantTurn(
    text="".join(text_parts) or None,
    reasoning="".join(reasoning_parts) or None,
    tool_calls=...,
    finish_reason=finish_reason,
    usage=usage,
)

yield StreamChunk(turn=turn)
```

## 4.4 Tool Call 必须继续正确累积

不要因为 true streaming 破坏 split arguments：

```text
chunk 1: {"pa
chunk 2: th":"a.py"}
```

最终仍必须得到：

```python
{"path": "a.py"}
```

必须保留：

- structured tool call accumulation；
- malformed JSON → `_raw` 兼容；
- `_maybe_salvage_tool_calls()` 现有语义；
- Qwen/Hermes XML/function 格式 salvage；
- bare JSON/toolname textual salvage；
- unknown tool name 过滤。

## 4.5 不允许“先显示、后撤回”工具调用文本

不要实现：

```text
先把 text delta 发 UI
↓
流结束发现是 textual tool call
↓
尝试从 UI 撤回
```

原因：

- 事件已经发出；
- partial persistence 可能已经保存；
- Stop 可能发生在中间；
- 前端不一定支持可靠撤回；
- transcript 语义会变复杂。

必须在 provider 层避免把潜在 textual tool-call 内容作为用户可见 delta 发出去。

## 4.6 Safe Default

V2 再加一条硬约束：

```text
tools enabled + capability 不明确
→ 保持 compat-buffered / salvage-safe
→ 不因为“看起来像 OpenAI-compatible”就开启 structured-tools true streaming
```

structured-tools true streaming 必须由一个可快速关闭的配置/内部开关控制（具体命名可遵循当前 Config 风格），并且只在已验证 provider/model 上启用。kill switch 关闭后必须无缝回到当前 buffering + salvage 行为，而不是改变 ToolRegistry/runtime 执行语义。


对未知 custom OpenAI-compatible endpoint：

```text
如果 tools=None
→ true streaming

如果 tools!=None 且无法确认 structured tool-call compatibility
→ 保守 compatibility path
```

后续可以通过 capability matrix 扩大 tools-enabled true streaming 覆盖率，但不作为本次破坏兼容性的理由。

---

# 5. Phase 2 — P0：修正 Streaming Retry 语义

## 5.1 核心原则

### 情况 A：没有任何 semantic provider progress

```text
request
↓
连接异常
↓
provider 尚未产生 text/reasoning/tool-call delta
```

允许 retry。

### 情况 B：已经产生 text/reasoning/tool-call 语义进度

```text
provider 已经开始生成实际回答或工具调用
↓
连接断开
```

禁止重启完整模型请求。

原因：

- 用户可能已经看到 partial text；
- textual/tool-call compatibility path 即使尚未显示，也可能已经生成了不同的工具参数；
- 第二次完整生成可能与第一次分叉；
- 容易造成重复文本或重复/不同工具调用。

因此 retry gate 不能只看：

```python
visible_output_emitted
```

必须看：

```python
provider_progress_seen
```

## 5.2 provider progress 定义

以下任一出现即：

```python
provider_progress_seen = True
```

- non-empty reasoning delta；
- non-empty text delta；
- structured tool-call id/name/arguments delta；
- textual-tool-call compatibility parser 已看到有意义的候选工具调用前缀；
- 任何会影响最终 AssistantTurn 内容的语义 delta。

仅 usage-only / heartbeat / empty choices 不算 semantic progress。

## 5.3 推荐逻辑

```python
if transport_error:
    if not provider_progress_seen:
        retry
    else:
        raise
```

这比只检查 visible text 更安全。

## 5.4 与 compatibility buffering 的关系

即使兼容路径暂时没有向 UI yield：

```text
buffered partial text/tool call 已产生
```

也应视为 provider progress。

不要因为“用户还没看到”就无限重做完整请求。

---

# 6. Phase 2.1 — Retry 次数

推荐：

```python
MAX_STREAM_ATTEMPTS = 2
```

即：

```text
Attempt 1
↓
如果在 semantic provider progress 前失败
↓
Attempt 2
```

Attempt 2 仍失败时：

- 如果仍完全没有 provider progress，可考虑一次 non-stream fallback；
- 如果已经产生任何 provider progress，直接 error；
- 不允许无限 retry；
- 不允许默认 3 次 stream + complete 叠加；
- fallback 也必须走现有 tool-call salvage / parameter-fix 语义。

必须补测试覆盖：

```text
no progress → one retry
text progress → no retry
reasoning progress → no retry
structured tool-call progress → no retry
textual-tool-call candidate progress → no retry
```

---

# 7. Phase 3 — P0：显式 SDK Timeout + 收口 Streaming 隐藏 Retry

目标文件：

```text
coworker/providers/openai_provider.py
```

V2 不允许把 `max_retries=0` 全局套到所有 OpenAI SDK client。当前 `complete()` 仍承担 non-stream、fallback、compaction/内部调用等路径；如果只关闭 SDK retry 而不补 transport retry，会让这些路径比改造前更脆。

推荐把 SDK client 创建策略拆成“共同 timeout + streaming retry ownership”：

```python
def _make_sdk_client(*, streaming_retry_owned: bool = False) -> Any:
    kwargs = {
        "api_key": key,
        "timeout": httpx.Timeout(
            connect=15.0,
            read=120.0,
            write=30.0,
            pool=15.0,
        ),
    }
    if streaming_retry_owned:
        kwargs["max_retries"] = 0
    # non-stream: 不主动设置 0，保留 SDK 当前默认/现有行为
    return OpenAI(**kwargs)
```

然后：

```text
stream() / _stream_client()
→ streaming_retry_owned=True
→ SDK max_retries=0
→ retry 由 ChemClaw 的 provider_progress 逻辑唯一负责

complete() / _ensure_client()
→ 不强制 max_retries=0
→ 保留当前 SDK retry 行为
```

目标是避免 streaming 路径出现：

```text
OpenAI SDK retry
+
ChemClaw stream retry
+
non-stream fallback
```

叠加，同时不牺牲 non-stream 的既有网络韧性。

## 7.1 不要设置过度激进 timeout

第一版建议：

```text
connect = 15 sec
read    = 120 sec
write   = 30 sec
pool    = 15 sec
```

不是为了 10 秒强杀，而是为了明确 host-level 边界。

如果当前项目已有 timeout/config 机制，优先复用；不要在多个 provider helper 中复制不同常量。

## 7.2 兼容性

当前依赖为宽范围 `openai>=1.0`。

因此 Cursor 应：

1. 确认当前实际支持的 constructor；
2. 不使用当前 SDK 不支持的参数；
3. 必要时补 provider-level compatibility helper；
4. 不为了 timeout 修改整个 provider abstraction；
5. **不得**为了统一代码路径把 non-stream client 也强制 `max_retries=0`。

## 7.3 必须新增 Retry Ownership Test

至少验证：

```text
stream client → SDK retry disabled / ChemClaw owns retry
complete client → 未被强制 max_retries=0
stream semantic progress 后 → ChemClaw 不 regenerate
non-stream transient failure → 不因本次改造丢失原 SDK 级韧性
```

如果当前 injected fake client 无法直接观察 constructor 参数，可把 client kwargs 构造抽成纯 helper 做 unit test，不要为了测试引入真实网络。

---

# 8. Phase 4 — Reasoning 策略

这是这次新增的关键部分。

用户说：

```text
你好
```

不应该：

```text
先展示/等待思考
↓
再回答
```

## 8.1 Reasoning 不等于用户可见进度

严格区分：

```text
Internal reasoning
```

和：

```text
Tool progress / narration
```

默认产品行为应为：

```text
Internal reasoning
→ 不展示
```

```text
正在搜索 PubChem…
正在核对法规…
正在读取文件…
→ 可以展示
```

不要把原始 reasoning 当作默认“工作进度”。

## 8.2 ExecutionProfile 加 Reasoning 配置

新增：

```python
@dataclass(frozen=True)
class ExecutionProfile:
    route: RequestRoute
    max_iterations: int              # hard ceiling
    target_iterations: int | None   # soft target; FAST/KNOWLEDGE/VERIFIED 可为 None
    tools_enabled: bool
    budget_guidance_enabled: bool
    emergency_finalization_enabled: bool
    reasoning_mode: str
```

推荐：

```text
FAST_CHAT       reasoning = off
KNOWLEDGE       reasoning = low/default
VERIFIED        reasoning = low/default
AGENT           reasoning = default
DEEP_RESEARCH   reasoning = default/high only if provider supports
```

不要强制所有模型统一传：

```python
reasoning_effort="none"
```

## 8.3 Provider Capability Driven

新增 provider helper，例如：

```python
def fast_response_settings(
    self,
    model: str,
    settings: dict,
) -> dict:
    ...
```

或者能力字段：

```python
supports_reasoning_effort
supports_disable_reasoning
```

FAST_CHAT：

```python
if provider/model supports disabling reasoning:
    apply provider-specific setting
else:
    do not pass unsupported parameter
```

避免兼容网关 400。

## 8.4 FAST_CHAT 不展示 reasoning delta

即使 provider 意外返回 reasoning：

```text
FAST_CHAT
→ 不发用户可见 REASONING_DELTA
```

可以保留内部 final turn 中必要 metadata，但不要默认 UI 展示。

---

# 9. Phase 5 — Agent Budget（V2：Soft Target + Legacy Hard Ceiling）

修改：

```text
coworker/config.py
```

**V2 不降低现有 hard ceiling。** 当前 built-in `max_iterations=150` 暂时保留，继续作为 legacy hard ceiling / 用户可覆盖的最终上限。

推荐新增 soft target：

```python
max_iterations = 150                 # legacy hard ceiling，保持不变
agent_target_iterations = 32         # soft target
deep_research_target_iterations = 50 # soft target
verified_max_iterations = 6          # VERIFIED 的独立小 hard budget
```

如果 Cursor 判断新增两个 target config 字段会导致不必要的配置迁移，可以把 `32/50` 先作为内部 route defaults；**但不得通过把 `max_iterations` 默认值改成 32 来实现 soft target。**

推荐有效预算：

```text
FAST_CHAT       hard=1
KNOWLEDGE       hard=1
VERIFIED        hard=min(verified_max_iterations, max_iterations)
AGENT           soft≈min(agent_target_iterations, max_iterations)
                hard=max_iterations
DEEP_RESEARCH   soft≈min(deep_research_target_iterations, max_iterations)
                hard=max_iterations
```

soft target 的含义：

```text
接近 32/50
→ 进入 Converge / Deliver
→ 尽量收敛并完成交付
→ 不是立即 hard stop
```

hard ceiling 的含义：

```text
达到 config.max_iterations
→ 才进入现有 hard-limit 语义 / 可选 emergency finalization
```

这样普通任务会明显更早收敛，但不会把原来可能需要 40/60/80 轮的长执行能力直接砍掉。

## 9.1 32/50 是 Soft Target，不是能力上限

以下情况尤其不能因为新 Router 把已开始的工作流强行缩短成 1/6/32/50 轮：

```text
durable resume
pending approval / ask_user / plan continuation
forced skill execution
selected persona 的正在进行中的执行任务
显式 continuation of AGENT / DEEP
```

这些情况应继承 active flow 的 hard ceiling，并使用 soft target 作为收敛提示，而不是新的终止条件。

## 9.2 显式用户配置优先

如果用户已有 workspace/global 配置：

```toml
max_iterations = 60
```

则：

```text
AGENT hard ceiling = 60
DEEP hard ceiling  = 60
soft target 分别取 min(32, 60) / min(50, 60)
```

如果用户把 `max_iterations` 配得更小，例如 24：

```text
AGENT/DEEP hard ceiling = 24
soft target 也不得超过 24
```

不要悄悄把用户显式配置扩回 150，也不要用 route defaults 覆盖它。

## 9.3 Soft Target 配置策略

如果加入：

```toml
agent_target_iterations = 40
deep_research_target_iterations = 70
```

必须始终满足：

```python
effective_target = min(configured_target, config.max_iterations)
```

若不加入新公开配置字段，则保持内部默认 32/50，并在最终报告说明。

## 9.4 不新增没有必要的 persona budget API

第一版不要为了这一点大改 persona schema。

优先使用：

- 当前 route profile；
- 当前 config hard ceiling；
- route soft target；
- active continuation state；
- durable resume state。

如果仓库已有 per-persona/per-task budget 字段，才复用；没有就不要凭空引入大范围 schema migration。

---

# 10. Phase 6 — Agent 收敛机制

对于：

```text
AGENT
DEEP_RESEARCH
```

使用：

```text
Explore
Converge
Deliver
```

## 10.1 自动计算阶段（基于 Soft Target，不基于 Hard Ceiling）

V2 不能再用 `profile.max_iterations`（默认 150 hard ceiling）直接按 75% 计算收敛，否则优化会退回到 100+ 轮才开始收敛。

推荐：

```python
hard = profile.max_iterations
target = profile.target_iterations or hard
target = min(target, hard)

converge_at = max(
    1,
    int(target * 0.75),
)

deliver_at = max(
    converge_at + 1,
    target - 4,
)
```

默认 AGENT soft target=32：

```text
1–23   Explore
24–27  Converge
28–32  Deliver
33–hard ceiling  Extended Delivery（只补关键缺口，不重新 broad explore）
```

默认 DEEP soft target=50：

```text
1–36   Explore
37–45  Converge
46–50  Deliver
51–hard ceiling  Extended Delivery（必要时继续，但保持收敛状态）
```

具体边界根据实现 off-by-one 保持一致即可。

关键语义：

```text
到达 soft target
≠ TURN_END
≠ max_iterations_exceeded

只有到达 hard ceiling
才进入真正 hard-limit 语义
```

---

# 11. Phase 6.1 — Convergence Context

只在 outbound view 注入：

```text
Iteration budget notice:

You are in the convergence phase.

Stop broad exploratory research.
Only perform additional searches or reads when they fill a material evidence gap
that could change the conclusion.

Batch independent low-risk reads/searches into the same tool-call turn whenever possible.

Start consolidating evidence, resolving contradictions, and preparing the final deliverable.
```

禁止写入：

```python
self.messages
```

---

# 12. Phase 6.2 — Delivery Context

接近 soft target 的 delivery 阶段：

```text
Iteration budget notice:

You are in the delivery phase.

Stop broad exploration now.

Use the evidence already collected.
Only perform a new tool call if it is strictly necessary to complete or verify
the final deliverable.

Prioritize:
1. resolve critical remaining contradictions;
2. complete/update the deliverable;
3. verify coherence;
4. answer the user.

Do not start a new research branch.
```

如果已经进入真正 hard ceiling 的最后 2 轮，才注入更强的最终警告：

```text
Only 2 hard-ceiling model iterations remain.
Finish the deliverable now.
Do not initiate new exploratory work.
```

不要在 soft target 的“最后 2 轮”假装系统马上会强制终止。

---

# 13. Phase 6.3 — Emergency Finalization（V5：最后实现 + Kill Switch；默认启用独立 Rollout）

Emergency Finalization 是**新语义**，不得和 Router/streaming/budget 第一批一起默认开启。

实施要求：

```text
HARD STOP G：实现 guard + tests
→ built-in default 继续 OFF
→ Router/Tool Projection Capability Gate 通过
→ engine/stop/plan/resume regression 通过
→ 46–55 final regression / manual smoke 完成
→ 新的独立 rollout run 中才允许评估 built-in default 是否候选 ON
```

必须有可快速关闭的 config/内部 kill switch，例如语义上：

```python
emergency_finalization_enabled: bool
```

具体命名遵循当前项目风格即可。A–G 与 final regression 阶段 built-in default 必须保持关闭；只有独立 post-regression rollout run、且前置 gate 全部满足时，才允许**单独**把 Emergency Finalization 作为最后一个候选默认开关测试。若任何兼容性问题无法安全解决，保持关闭并在最终报告说明，**不得为了满足 checklist 强行开启。**

在测试显式启用、或 rollout 最终获准启用后，撞到真正 hard ceiling 时，不直接结束。

普通可终结状态下执行一次：

```text
tools disabled
model-only finalization
```

Prompt：

```text
The tool-call iteration budget has been exhausted.

You may not call any more tools.

Using only the evidence and tool results already present in the conversation,
produce the best possible final answer now.

If a deliverable file was already created, reference it correctly.

If some requested work could not be completed, clearly state the remaining gap,
but still provide the most useful finished result possible.
```

只执行一次。

不要重新进入 loop。

最终保留 backward-compatible status：

```python
{
    "status": "max_iterations_exceeded",
    "best_effort_finalized": True,
}
```

## 13.1 Emergency Finalization Guard

以下情况绝对不能触发 model-only finalization：

```text
user Stop / interrupt
pending ask_user
pending permission approval
pending propose_plan / plan approval
pending request_directory
durable resume 尚有 unanswered trailing tool calls
当前 turn 已进入 suspended/pending 状态
```

这些状态必须继续服从现有状态机。

不能出现：

```text
用户还没批准
↓
系统因为 hard limit 先做“最终回答”
```

也不能：

```text
用户按 Stop
↓
系统又额外发起一次 finalization model call
```

## 13.2 未完成写操作的处理

如果 hard limit 到达时：

```text
deliverable file 尚未创建
CRM/send_message/write_file 尚未执行
```

finalization 不得假装任务已完成。

只能：

- 使用已有结果；
- 明确说明未完成项；
- 不再调用工具；
- 不虚构文件路径/发送结果/CRM 状态。

---

# 14. Phase 7 — 新的智能路由体系

新增：

```text
coworker/request_router.py
```

建议新增/集中（具体文件名可按仓库风格）：

```text
coworker/tool_policy.py  # pure internal helper：network_scope / usage_class
```

但 Router 只负责：

```text
当前请求应该采用哪种回答/执行强度
```

Router 不负责：

```text
撤销 persona 能力
撤销 pending interaction
撤销 durable resume
撤销 forced skill
撤销用户明确要求的产品动作
```

## 14.1 Route 类型

保持五类：

```python
class RequestRoute(str, Enum):
    FAST_CHAT = "fast_chat"
    KNOWLEDGE = "knowledge"
    VERIFIED = "verified"
    AGENT = "agent"
    DEEP_RESEARCH = "deep_research"
```

不新增大规模 Agent framework。

## 14.2 RouteDecision

```python
@dataclass(frozen=True)
class RouteDecision:
    route: RequestRoute
    source: str
    reason: str
    confidence: float = 1.0
    allowed_tool_names: tuple[str, ...] | None = None
```

`source`：

```text
override
pending_state
product_action
local
risk
inherit
classifier
legacy_fallback
```

## 14.3 Tool/Network Policy 独立于 Route

不要把：

```text
不要联网
不要搜索
不用工具
```

都折叠成 route。

建议新增轻量 policy：

```python
@dataclass(frozen=True)
class TurnToolPolicy:
    no_tools: bool = False
    no_search: bool = False
    no_external_network: bool = False
```

也可以用等价 enum/字段，只要语义分开即可。

Route 解决：

```text
回答/执行复杂度
```

ToolPolicy 解决：

```text
本轮允许哪些工具类别
```

---

# 15. Phase 7.1 — Router 总流程

严格按以下优先级：

```text
User
 ↓
1. Pending-State Guard
 ↓
2. Selected Persona / Forced Skill / Active Execution Guard
 ↓
3. Product Action Gate
 ↓
4. Explicit Tool/Network Policy
 ↓
5. Pure-Answer Positive Eligibility Gate
 ↓
6. Local Fast Gate
 ↓
7. Chemical / Current-Fact Risk Gate
 ↓
8. 仍模糊？
      ↓
   Tiny Classifier
      ↓
9. Safe Legacy Fallback
      ↓
10. ExecutionProfile + Tool Projection
```

Classifier 只处理真正模糊请求。

## 15.1 Pending-State Guard

以下状态优先于 Router：

```text
pending ask_user
pending permission
pending plan approval
pending request_directory
durable resume
unanswered trailing tool calls
```

这些请求不应该重新被当成一个独立 FAST_CHAT/KNOWLEDGE 问题。

例如：

```text
上一轮 ask_user 问：“请选择 A/B”
用户：“A”
```

不能：

```text
“A” → FAST_CHAT
```

必须进入现有 interaction/resume flow。

## 15.2 Selected Persona / Forced Skill Guard

Router 不能替换用户选中的 Agent/Persona。

Router 只能在：

```text
该 persona 已拥有的 registry/capability 范围内
```

做 tool schema projection。

如果用户通过 `/skill`、forced skill、default skill 机制要求技能执行：

```text
load_skill / skill execution capability
```

不能因为文本看起来像写作/翻译就被 FAST_CHAT 的 `tools=None` 切掉。

第一版安全策略：

```text
forced skill / product-action skill request
→ 至少 AGENT profile 或 legacy-compatible execution path
```

## 15.3 Product Action Gate

以下意图默认不能进入纯 `tools=None` fast path：

```text
记住 / 忘记 / 保存偏好
提醒 / 定时 / 计划任务 / self-wake
发消息 / 发文件
连接 / 使用 connector / MCP
读取/修改本地文件
代码执行 / shell
安装/加载/运行 skill
创建/修改 CRM 数据
请求目录
需要 ask_user/approval 的交互
```

这些应：

```text
→ AGENT
```

或复用当前明确的 existing product flow。

注意：

```text
“帮我写一封邮件”
```

如果只是生成邮件正文，可 FAST_CHAT。

但：

```text
“把这封邮件发给 Jack”
```

是 product action，必须保留发送工具。

## 15.3A Pure-Answer Positive Eligibility Gate（V2 核心）

FAST_CHAT/KNOWLEDGE 不再通过“没有检测到 product-action 关键词”来推断安全，而必须通过**正向证明**。

只有明确落入以下 pure-answer 类别，且同时通过 pending/persona/skill/product-action/policy guards，才允许进入 `tools=None`：

```text
明确 greeting / thanks / acknowledgement / goodbye
纯翻译（输入内容已给全）
纯润色 / 改写（输入内容已给全）
对用户已提供内容做摘要/格式调整
纯 brainstorm / 标题/措辞生成，且不要求写文件/发送/保存
稳定、低风险、非实时概念解释，且不要求验证或产品动作
```

以下情况**不能因为没命中关键词就默认 FAST_CHAT/KNOWLEDGE**：

```text
意图不清晰的短指令
未来新增的 connector/MCP/product action
自定义 persona 的专用工具动作
无法判断是否需要本地文件/状态/记忆的请求
classifier/route parser 异常
```

V2 安全原则：

```text
能明确证明是 pure answer
→ FAST_CHAT / KNOWLEDGE

不能明确证明
→ legacy-safe AGENT / 当前 persona execution behavior
```

性能偶尔少优化一次，比静默切断产品能力安全。

## 15.4 Risk Gate 仍然负责事实验证

Product Action Gate 与 Chemical Risk Gate 是两个不同维度：

```text
查苯 CAS
→ VERIFIED

把苯 CAS 查询结果写到本地文件
→ AGENT（并允许 targeted chemical + file tools）
```

不要让单一 route category 丢失组合能力。

---

# 16. Phase 7.2 — FAST_CHAT

直接进入 FAST_CHAT 的典型请求：

```text
你好
您好
hi
hello
hey
谢谢
thanks
好的
ok
明白
再见
```

以及纯生成型请求：

```text
帮我润色这句话
翻译下面内容
写一封邮件正文
给我想几个标题
```

前提必须同时满足（**正向白名单，不是排除法**）：

- 当前请求能明确归入 Section 15.3A 的 pure-answer 类别；
- 用户已提供必要内容；
- 不依赖外部事实；
- 不要求文件/connector/memory/schedule/skill 等产品动作；
- 当前没有 pending interaction/resume；
- 没有 forced skill；
- ToolPolicy 没有要求保留某类工具。

FAST_CHAT：

```python
tools_enabled = False
max_iterations = 1
reasoning_mode = "off"
```

必须：

```text
classifier calls = 0
provider tools = None
```

## 16.1 FAST_CHAT 不是“所有短请求”

以下虽然很短，也不能 FAST_CHAT：

```text
记住这个
明天提醒我
发给 Jack
读取这个文件
继续
A
同意
运行测试
```

必须先经过 pending/product-action guard。

---

# 17. Phase 7.3 — KNOWLEDGE

用于稳定、低风险、非实时的普通知识。

例如：

```text
什么是苯？
为什么苯有芳香性？
SN1 和 SN2 有什么区别？
什么是酯化反应？
PE 和 PP 有什么区别？
```

特点（必须正向确认）：

- 当前请求能明确归入 stable pure-answer knowledge；
- 知识稳定；
- 不要求精确实时数值；
- 不涉及法规；
- 不涉及危险决策；
- 不要求外部验证；
- 不需要 memory/file/schedule/connector/skill 等产品动作；
- 如果无法确定以上条件，禁止为了性能默认 KNOWLEDGE，走 legacy-safe fallback。

配置：

```python
tools_enabled = False
max_iterations = 1
reasoning_mode = "low/default"
```

## 17.1 KNOWLEDGE 与用户约束

如果用户说：

```text
不要搜索网络，直接解释苯为什么有芳香性
```

可以：

```text
KNOWLEDGE
no_search=True
```

如果用户说：

```text
不用任何工具，只根据已有知识回答
```

则：

```text
KNOWLEDGE
no_tools=True
provider tools=None
```

如果用户说：

```text
不要联网，读取本地文件并总结
```

不能 KNOWLEDGE，因为这是本地产品动作：

```text
AGENT
no_external_network=True
local file tools 仍可用
```

---

# 18. Phase 7.4 — VERIFIED

这是 ChemClaw 最重要的专业差异化路径。

VERIFIED 用于：

```text
问题不一定复杂
但事实需要精确验证
```

例如：

```text
苯的 CAS 是多少？
100-42-5 是什么？
这个物质的分子式是什么？
苯的闪点是多少？
该物质是否易燃？
它是否在某危险化学品目录中？
REACH 对该物质有哪些限制？
这个公司现在是否仍在运营？
当前汇率是多少？
今天苯的市场价格如何？
```

配置：

```python
max_iterations = min(config.verified_max_iterations, config.max_iterations)  # hard, default 6
tools_enabled = True
budget_guidance_enabled = False
emergency_finalization_enabled = guarded_kill_switch
reasoning_mode = "low/default"
```

VERIFIED 不做 broad research。

目标：

```text
1–3 个精准工具
↓
快速验证
↓
直接回答
```

## 18.1 VERIFIED 不能覆盖产品动作

例如：

```text
查苯的 CAS，然后写进 report.md
```

不能只 VERIFIED 后停住。

应：

```text
AGENT
allowed tools 至少包含：
lookup_chemical_identity
+
必要 file tool
```

## 18.2 用户禁网时的 VERIFIED

如果请求需要现实验证，但用户明确：

```text
不要联网
```

系统不能偷偷联网。

应根据可用本地/缓存/非联网数据源决定：

```text
有符合 policy 的验证工具
→ 可验证

没有
→ 明确说明无法在当前约束下完成外部验证
```

不要为了满足 VERIFIED 强行违反 ToolPolicy。

---

# 19. Phase 7.5 — 化工事实风险分级

新增：

```python
class VerificationLevel(str, Enum):
    NONE = "none"
    PREFER = "prefer"
    REQUIRED = "required"
```

## NONE

例如：

```text
解释芳香性
解释 SN2
苯是什么
```

→ KNOWLEDGE

## PREFER

例如：

```text
苯的分子量是多少？
苯的沸点是多少？
```

如果有专业 provider，优先 VERIFIED。

## REQUIRED

以下类别建议强制 VERIFIED/AGENT：

### Chemical Identity

```text
CAS
InChI
SMILES
分子式
化学名称
同义词映射
CAS → 物质
```

### 精确物性

```text
沸点
熔点
闪点
密度
蒸气压
爆炸极限
```

尤其用户要求精确数值时。

### Safety / Toxicology

```text
危险分类
毒性
致癌性
易燃性
安全储存
应急处置
```

### Regulatory

```text
REACH
TSCA
危险化学品目录
运输分类
禁限用
法规状态
```

### Commercial / Current

```text
价格
供应商
产能
公司状态
当前市场
最新公告
```

### Legal / Entity

```text
公司注册
VAT
主体身份
```

### Time-sensitive

```text
今天
最新
当前
实时
最近
2026 年目前
```

当这些词真正用于现实事实查询时。

---

# 20. Phase 7.6 — AGENT

用于：

```text
多步骤任务
workspace 操作
文件读写
代码修改
连接器
memory/schedule/message 等产品动作
forced skill
多步信息查询
需要多工具协作
```

例如：

```text
读取这个文件并分析
修改 engine.py
运行测试
查几个供应商然后整理成表
比较几家公司
读取 CSV 后筛选进口商
记住我喜欢简短回复
明天提醒我联系 BASF
把结果发给 Jack
用指定 skill 处理这份内容
```

配置：

```python
max_iterations = config.max_iterations                   # hard ceiling，built-in default 仍为 150
target_iterations = min(agent_target, max_iterations)   # soft target≈32
tools_enabled = True
reasoning_mode = "default"
```

AGENT 默认不自动升级 DEEP。

## 20.1 Tool 集合可以是“组合最小集”

AGENT 不等于必须把全 registry 都发给模型。

如果 Product Action Gate 已明确任务类型：

```text
查 CAS + 写文件
```

可以投影为：

```text
chemical identity tools
+
必要 file tools
+
always-required control tools
```

但第一版如果组合裁剪不够确定：

```text
宁可保留 legacy available tools
不要误删能力
```

兼容性优先。

---

# 21. Phase 7.7 — DEEP_RESEARCH

只有明确研究意图才进入：

```text
深度研究
全面调研
尽职调查
尽调
完整行业报告
市场研究报告
竞争格局报告
多来源研究
交叉验证多个来源
systematic research
deep research
due diligence
comprehensive market report
```

不要因为：

```text
详细解释
深入讲讲
分析一下
```

就进入 DEEP。

配置：

```python
max_iterations = config.max_iterations          # hard ceiling，默认仍 150
target_iterations = min(deep_target, max_iterations)  # soft≈50
tools_enabled = True
reasoning_mode = "default"
```

DEEP 仍然服从：

- selected persona；
- explicit network/tool policy；
- permissions；
- Stop；
- compaction；
- durable resume；
- convergence/delivery budget。

如果用户说：

```text
深度研究，但不要联网
```

不要偷偷联网。

可以使用符合 policy 的本地资料/文件/已有 evidence；若不足，要明确约束。

---

# 22. Phase 7.8 — 用户显式 Tool / Search / Network Policy

这是本次必须修改的高风险点。

不要再把：

```text
不要搜索
不要联网
不要查资料
不用工具
只根据已有知识回答
```

全部视为同一个“禁工具”指令。

至少拆成三类：

## 22.1 NO_TOOLS

典型：

```text
不用工具
不要调用任何工具
只根据已有知识回答
不要查任何东西
```

语义：

```python
no_tools = True
```

provider：

```python
tools = None
```

如果任务本身必须靠产品动作才能完成，例如：

```text
不用工具，把文件改掉
```

这是不可同时满足的约束。

系统应说明无法在“不用工具”约束下实际修改文件，而不是偷偷调用。

## 22.2 NO_SEARCH

典型：

```text
不要搜索
不要上网搜
不要查网页
```

语义：

```python
no_search = True
```

禁止：

```text
web_search
web_fetch（如果语义属于联网检索）
搜索型外部 research provider
```

但仍可允许：

```text
local file
memory
skill
schedule
plan/ask_user
明确非搜索型本地工具
```

是否允许用户点名的特定 connector/API lookup，按原产品语义和用户措辞判断；不要自动等同于 NO_TOOLS。

## 22.3 NO_EXTERNAL_NETWORK

典型：

```text
不要联网
离线处理
只用本地数据
```

语义：

```python
no_external_network = True
```

禁止所有需要外网的工具：

```text
web
remote connector
remote MCP
PubChem / GLEIF / VAT / FX / SAM / TED / Comtrade 等远程 provider
```

仍可允许：

```text
workspace file tools
local shell（仍服从权限）
memory
local skill
todo
plan / ask_user
local deterministic transforms
```

## 22.4 “不要查资料”的默认解释

优先解释为：

```text
不要外部检索 / 不要主动查资料
```

而不是自动禁止 memory/file/skill/product-control 工具。

如果上下文明确说：

```text
“不要查任何东西，也不要用任何工具”
```

才升级为 NO_TOOLS。

## 22.5 约束优先级

用户显式约束必须高于 route 对工具的需求：

```text
VERIFIED + NO_EXTERNAL_NETWORK
```

不能偷偷调用联网验证工具。

正确行为：

```text
能用符合约束的数据源验证 → 验证
不能 → 明确说明验证受限
```

## 22.6 V2：统一 Tool Network / Search Classification

不要在 Router、Engine、policy filter 多处散落硬编码工具名。新增一个**内部纯 helper**（不要求修改 ToolRegistry 公共接口）统一判断工具属性。

建议两个正交维度：

```python
network_scope = LOCAL | REMOTE | UNKNOWN
usage_class   = SEARCH | PRODUCT_CONTROL | FILE | MEMORY | SKILL | OTHER
```

可以优先读取现有 metadata；metadata 不足时，在一个集中模块/helper 里做保守映射。不要把分类表复制到多个文件。

最低要求：

```text
web / PubChem / GLEIF / VAT / FX / SAM / TED / Comtrade
remote connectors / remote MCP
→ REMOTE

workspace/file/local shell/local deterministic transforms
memory/local skill/todo/plan/ask_user
→ LOCAL

无法可靠判断的新 custom tool
→ UNKNOWN
```

Policy 语义：

```text
NO_EXTERNAL_NETWORK:
  REMOTE  → remove
  UNKNOWN → remove（安全默认，不能偷偷联网）
  LOCAL   → keep

NO_SEARCH:
  usage_class=SEARCH → remove
  local/product-control 非搜索工具 → keep
  UNKNOWN → 不仅因为 unknown 就删除；若同时 NO_EXTERNAL_NETWORK，再按 network_scope 规则处理

普通 AGENT/DEEP（无禁网约束）：
  UNKNOWN → keep legacy capability
```

这条规则同时防两类错误：

1. 用户明确说“不联网”时，新 connector/MCP 因分类遗漏而偷偷联网；
2. 普通任务中，新 custom tool 因 Router 不认识而被永久静默裁掉。

必须给 helper 写纯 unit tests。

---

# 23. Phase 7.9 — Follow-up Inheritance

例如：

```text
Turn 1:
深度研究全球 PA66 市场
→ DEEP_RESEARCH

Turn 2:
继续
→ DEEP_RESEARCH
```

支持：

```text
继续
接着
继续查
继续研究
再往下
再补几个
go on
continue
keep going
```

可以保存：

```python
self._last_route
```

但 route inheritance 不是最高优先级。

必须先检查：

```text
pending interaction
active execution
durable resume
new explicit policy
new explicit product action
```

例如：

```text
Turn 1: 深度研究全球 PA66
Turn 2: 继续，但不要联网
```

应：

```text
route 继承 DEEP
policy 更新为 no_external_network=True
```

例如：

```text
Turn 1: AGENT 正在执行
Turn 2: Stop
```

Stop 优先，不能继承 route 后继续跑。

只在明显 continuation 时继承。

---

# 24. Phase 7.10 — Route 不 Sticky

必须：

```text
Turn 1: 深度研究...
→ DEEP

Turn 2: 继续
→ DEEP

Turn 3: 谢谢
→ FAST_CHAT

Turn 4: 你好
→ FAST_CHAT
```

Route 是：

```text
per-turn
```

不是 per-session mode。

---

# 25. Phase 7.11 — Tiny Classifier

只处理：

```text
pending/product-action/local/risk gate
都无法确定
```

的真正模糊请求。

例如：

```text
分析一下 BASF 在中国未来的机会
```

可能：

```text
KNOWLEDGE
AGENT
DEEP_RESEARCH
```

这时才 classifier。

## Prompt

```text
Classify the user's CURRENT request into exactly one category:

FAST_CHAT
- Greetings, acknowledgements, writing, rewriting, translation,
  summarization of supplied content, brainstorming, or trivial conversation,
  only when no product action/tool execution is required.

KNOWLEDGE
- Stable non-current knowledge that can reasonably be answered directly.
  Includes conceptual chemistry explanations that do not require exact external verification
  and do not require a ChemClaw product action.

VERIFIED
- A short or moderate request where one or a few precise facts should be checked
  using authoritative external/domain tools. Includes chemical identity, exact properties,
  safety, regulations, legal/entity status, current prices, or time-sensitive facts.

AGENT
- Requires product actions or execution: memory, scheduling, messaging, skills,
  workspace/file operations, coding, connectors, MCP, multiple tools,
  multi-step execution, or moderate research.

DEEP_RESEARCH
- Explicitly asks for comprehensive multi-source investigation, due diligence,
  systematic research, or a substantial research report.

Rules:
- Never classify a known pending interaction/resume as FAST_CHAT or KNOWLEDGE.
- Product actions belong to AGENT even when the user message is short.
- Prefer FAST_CHAT/KNOWLEDGE only when no external evidence and no product action are materially required.
- Prefer VERIFIED over AGENT when a small number of targeted checks is enough and no additional product action is requested.
- Prefer AGENT over DEEP_RESEARCH unless deep research is explicit.
- Do not use DEEP_RESEARCH merely because the user says "detailed".
- Return exactly one token:
FAST_CHAT
KNOWLEDGE
VERIFIED
AGENT
DEEP_RESEARCH
```

## 设置

```python
tools = None
temperature = 0
max_tokens = 8
```

如 provider 支持：

```python
reasoning_effort = "none"
```

## Timeout

```python
ROUTER_TIMEOUT_SECONDS = 5.0
```

## Retry

```text
最多 1 次 classifier call
不 retry
```

## 25.1 Failure Fallback — 必须改成 Legacy-Safe

禁止：

```text
classifier failure
→ KNOWLEDGE
→ tools=None
```

因为这可能让 memory/file/schedule/connector 等请求突然失能。

推荐：

```python
def safe_fallback(...):
    if pending_state:
        return legacy_current_flow

    if product_action_suspected:
        return AGENT

    if verification_required:
        return VERIFIED

    if local_gate_confidently_says_fast_or_knowledge:
        return that_route

    return AGENT  # legacy-compatible unrestricted execution profile
```

这里的 fallback `AGENT` 不是说所有失败都要重型研究，而是：

```text
无法安全证明可以裁能力时
→ 保留当前 legacy tool behavior
```

性能偶尔退化一次，比功能静默失效安全。

`source` 记录：

```text
legacy_fallback
```

便于后续统计 classifier failure。

---

# 26. Phase 8 — ExecutionProfile

## 26.0 V5 Legacy-Inert Activation Rule

HARD STOP C 只允许先建立**可选、默认不改变旧路径**的 reasoning / soft-budget infrastructure。

在以下任一条件成立时：

```text
request_routing_enabled = false
OR
Router 尚未接入当前 request execution
OR
本轮没有显式 ExecutionProfile
```

必须保持：

```text
legacy request execution
→ hard ceiling 继续来自现有 config.max_iterations
→ 不自动应用 AGENT≈32 / DEEP≈50 soft target
→ 不自动注入 Converge / Deliver phase guidance
→ 不因为新增 plumbing 改写旧 reasoning defaults
```

也就是说，`32/50` 是 **route-selected ExecutionProfile 的行为参数**，不是 `TurnEngine` 一出现新字段就全局生效的默认。

推荐实现形态之一：

```python
execution_profile: ExecutionProfile | None = None
```

当 `execution_profile is None` 时，Engine 走本 Plan 之前的 legacy budget/reasoning 行为。只有后续 Router 在已启用状态下显式构造 profile，才激活 route-specific target / guidance。

如果当前代码结构更适合其他表达方式，可以调整 API，但必须保留上述语义与回归测试。

新增：

```python
@dataclass(frozen=True)
class ExecutionProfile:
    route: RequestRoute
    max_iterations: int              # hard ceiling
    target_iterations: int | None   # AGENT/DEEP soft target
    tools_enabled: bool
    allowed_tool_names: tuple[str, ...] | None
    budget_guidance_enabled: bool
    emergency_finalization_enabled: bool
    reasoning_mode: str
    tool_policy: TurnToolPolicy
```

如果不希望 `ExecutionProfile` 直接依赖 policy dataclass，也可以并列保存，只要 provider projection 能同时读取。

推荐 profile：

```python
FAST_CHAT_PROFILE:
    max_iterations = 1
    target_iterations = None
    tools_enabled = False
    allowed_tool_names = ()
    budget_guidance_enabled = False
    emergency_finalization_enabled = False
    reasoning_mode = "off"

KNOWLEDGE_PROFILE:
    max_iterations = 1
    target_iterations = None
    tools_enabled = False
    allowed_tool_names = ()
    budget_guidance_enabled = False
    emergency_finalization_enabled = False
    reasoning_mode = "low"

VERIFIED_PROFILE:
    max_iterations = min(config.verified_max_iterations, config.max_iterations)  # hard, default 6
    target_iterations = None
    tools_enabled = True
    allowed_tool_names = route-selected subset
    budget_guidance_enabled = False
    emergency_finalization_enabled = guarded_kill_switch
    reasoning_mode = "low"

AGENT_PROFILE:
    max_iterations = config.max_iterations       # hard ceiling，built-in 仍为 150
    target_iterations = min(agent_target, config.max_iterations)  # soft≈32
    tools_enabled = True
    allowed_tool_names = None
    budget_guidance_enabled = True
    emergency_finalization_enabled = guarded_kill_switch
    reasoning_mode = "default"

DEEP_RESEARCH_PROFILE:
    max_iterations = config.max_iterations       # hard ceiling，built-in 仍为 150
    target_iterations = min(deep_target, config.max_iterations)   # soft≈50
    tools_enabled = True
    allowed_tool_names = None
    budget_guidance_enabled = True
    emergency_finalization_enabled = guarded_kill_switch
    reasoning_mode = "default"
```

## 26.1 Profile 只影响本轮 outbound execution

不要把 profile 写入 canonical history。

不要修改：

```text
self.messages 中的用户原话
durable resume 所需 tool call / tool result
existing notice semantics
```

## 26.2 Profile 不得降低 active state 的能力

如果当前是：

```text
resume / pending / forced skill / product action
```

ExecutionProfile 必须由 guard 后的结果构造。

不能先选 FAST_CHAT，再试图在后面“补回”缺失能力。

---

# 27. Phase 9 — P0：Per-turn Tool Filtering

当前 Registry 可以继续包含所有工具。

不要每回合 rebuild Engine。

不要 unregister 工具。

provider 调用时根据：

```text
active agent/persona registry
+
RouteDecision
+
TurnToolPolicy
+
pending/product capability guard
```

生成本轮 tool schema。

## 27.1 Pure FAST_CHAT / KNOWLEDGE

只有在已经**正向确认 Section 15.3A pure-answer eligibility**，并且：

```text
无 pending
无 product action
无 forced skill
无 selected persona 必须工具能力
no special execution state
router/classifier 没有不确定性
```

时才：

```python
tools = None
```

这仍然是硬要求。

不是：

```text
Prompt 告诉模型“不要用工具”
```

而是 API 层根本不发送 Tool Schema。

## 27.2 VERIFIED

只暴露最小必要验证工具。

例如：

### “苯的 CAS 是多少？”

```python
allowed_tool_names = (
    "lookup_chemical_identity",
)
```

### “100-42-5 是什么？”

```python
allowed_tool_names = (
    "lookup_chemical_identity",
)
```

### “当前汇率”

```python
allowed_tool_names = (
    "lookup_fx_rate",
)
```

### “EU VAT 是否有效”

```python
allowed_tool_names = (
    "validate_eu_vat",
)
```

### “查企业主体”

```python
allowed_tool_names = (
    "lookup_legal_entity",
)
```

### “法规状态”

根据 repo 实际 available tools/MCP：

```text
chemical identity
relevant regulatory connector
web search
web fetch
```

不要把：

```text
SAM.gov
tenders
quote
customs
trade
send_message
...
```

无关工具全部传给模型。

## 27.3 AGENT / DEEP 默认兼容策略

第一版不要激进裁剪 AGENT/DEEP。

推荐：

```text
明确可以安全识别任务工具集合
→ targeted subset

否则
→ 保留当前 agent/persona 已注册的 legacy tool schemas
```

特别是：

```text
memory
skills
ask_user
plan
request_directory
scheduling
self-wake
messaging
connectors
MCP
workspace/file
```

不能仅因为“看起来和化工事实无关”就被删掉。

## 27.4 ToolPolicy 最终过滤

在 route/tool subset 之后应用用户约束：

```text
NO_TOOLS
→ []

NO_SEARCH
→ 去掉 search/web research 类

NO_EXTERNAL_NETWORK
→ 去掉所有 remote/network tools
   保留 local/product-control tools
```

如果过滤后任务无法完成：

```text
不要自动解除约束
```

由模型/系统明确说明限制。

---

# 28. Phase 9.1 — ToolRegistry Schema Filtering / Projection

优先最小侵入实现。

可以在 Engine 层新增 helper：

```python
def _tool_schemas_for_profile(
    registry: ToolRegistry,
    profile: ExecutionProfile,
    *,
    mandatory_tool_names: set[str] | None = None,
) -> list[dict] | None:
    ...
```

逻辑：

```text
1. 读取 registry.schemas()
2. 根据 route allowed_tool_names 做投影
3. 合并本轮 mandatory capability tools
4. 通过 Section 22.6 的统一 tool classification 应用 no_search/no_external_network/no_tools
5. UNKNOWN 工具：禁网时排除；普通 AGENT/DEEP 保留
6. 空集合 → None
```

如果改 ToolRegistry 公共接口风险较小，也可以：

```python
def schemas(
    self,
    allowed_names: set[str] | None = None,
):
    ...
```

但优先避免公共接口变化。

## 28.1 Mandatory Tool 不是全局 always-on

不要把所有 control tool 永远发送给 FAST_CHAT。

`mandatory_tool_names` 只来自当前状态，例如：

```text
forced skill
active scheduling request
message send request
pending capability continuation
```

纯 greeting 仍必须：

```python
tools=None
```

## 28.2 过滤的是 Schema，不是 Runtime Registry

ToolRegistry 仍保留完整工具，确保：

- durable resume 可以执行历史里的 pending tool call；
- engine permission/registry lookup 语义不变；
- session live setting/filter 不需要 rebuild；
- tool execution path 不因本轮 schema projection 被永久改变。

## 28.3 Projection 不得自行猜测 Network 属性

`_tool_schemas_for_profile()` 不应拥有第二套工具分类规则。所有 `NO_SEARCH` / `NO_EXTERNAL_NETWORK` 判断必须调用 Section 22.6 的统一 helper。

```text
normal AGENT/DEEP + UNKNOWN tool → keep
NO_EXTERNAL_NETWORK + UNKNOWN tool → remove
```

新增/动态 connector、MCP、extra_tools 的行为必须由同一规则覆盖。

---

# 29. Phase 9.2 — FAST_CHAT Context

只 outbound 注入：

```text
Fast chat mode is active for this turn.

Answer directly.
No tools are available for this pure-answer turn.
Do not create a research plan, todo list, artifact, or progress narration.
Do not claim to have searched, browsed, checked, or verified external information.
```

前提：

```text
pure FAST_CHAT 已通过 capability guard
```

不进入 canonical history。

---

# 30. Phase 9.3 — KNOWLEDGE Context

```text
Knowledge mode is active.

Answer directly from stable domain/general knowledge.
No tools are available for this pure-answer turn.

Do not claim external verification.
If the user requests an exact, current, regulatory, safety-critical,
or identity-sensitive fact that should be externally verified, be cautious
about certainty rather than inventing verification.
```

如果本轮不是 pure-answer KNOWLEDGE，而 guard 判断存在产品动作，则不应该走这个 profile。

---

# 31. Phase 9.4 — VERIFIED Context

```text
Verified-answer mode is active.

Use only the provided targeted tools needed to verify the requested factual claim.

Do not broaden the task into general research.
Prefer authoritative/domain-specific tools over broad web search when available.

Respect the user's tool/search/network restrictions.
Once the required fact is verified, answer directly and stop.
```

---

# 32. Phase 9.5 — AGENT Context

```text
Standard agent mode is active.

Use tools only when they materially help complete the request.
Do not turn a straightforward task into broad research.

Preserve the user's selected persona/skill and current workflow.
Respect explicit no-search/no-network/no-tools constraints.
Batch independent low-risk lookups in the same tool-call turn when possible.
```

---

# 33. Phase 9.6 — DEEP_RESEARCH Context

```text
Deep research mode is active.

Build evidence across multiple relevant sources when appropriate.
Cross-check important claims.
Resolve material contradictions.
Use the iteration budget deliberately.
Stop collecting repetitive evidence once the conclusion is stable.

Respect explicit tool/network restrictions and existing session state.
```

---

# 34. Phase 10 — Encouraging Batched Tool Calls

修改：

```text
coworker/agent.py
```

加入通用简短 guidance：

```text
Tool efficiency:
When multiple read-only searches, lookups, or file reads are independent,
request them together in the same assistant tool-call turn instead of serializing
them across separate model iterations.
Only serialize calls when a later call genuinely depends on an earlier result.
```

当前 Engine 已支持低风险工具并发，因此要让模型利用。

---

# 35. Phase 11 — Conservative Duplicate Tool Detection

只检测：

```text
完全相同 tool name
+
完全相同 arguments
```

连续重复。

记录最近：

```python
self._recent_tool_signatures
```

signature：

```python
(
    tool_call.name,
    json.dumps(
        tool_call.arguments,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ),
)
```

如果同一个 signature 达到 3 次：

下一轮 outbound context：

```text
You have repeated an identical tool call several times.
Do not call it again unless there is a concrete reason to expect a different result.
Use the evidence already collected and move toward completion.
```

不要硬禁止。

第一版不要做：

- embedding similarity；
- semantic duplicate detection；
- another LLM judge；
- fuzzy query matching。

---

# 36. Phase 12 — Instrumentation

记录每个 turn：

```text
route
route_source
route_reason
router_elapsed_ms
classifier_used
profile_max_iterations
tools_enabled
allowed_tool_count
reasoning_mode
```

新增兼容/能力保护观测：

```text
pending_state_guard_hit
product_action_gate_hit
forced_skill_guard_hit
selected_persona_guard_hit
tool_policy_no_tools
tool_policy_no_search
tool_policy_no_external_network
legacy_fallback_used
mandatory_tool_count
tool_projection_mode
```

记录 model call：

```text
iteration
budget_phase
elapsed_ms
first_visible_delta_ms
stream_attempts
tool_count
finish_reason
```

记录 provider：

```text
stream attempt
stream mode = direct | structured | compat_buffered
provider progress seen?
visible output seen?
tool progress seen?
transport failure type
retry?
fallback?
textual_tool_salvage_used?
```

不要记录：

- API key；
- 完整用户 prompt；
- 敏感 tool result；
- 完整邮件/文件内容。

Instrumentation 的目的不是改变产品语义，而是能够发现：

```text
Router 是否误把产品动作切成 FAST_CHAT
classifier failure 是否频繁走 legacy fallback
custom endpoint 是否频繁进入 compat_buffered
```

---

# 37. 推荐性能指标

后续统计：

```text
FAST_CHAT %
KNOWLEDGE %
VERIFIED %
AGENT %
DEEP_RESEARCH %
```

以及：

```text
median TTFT per route
p95 TTFT per route
median total latency
classifier invocation rate
average tool calls per VERIFIED turn
average iterations per AGENT
average iterations per DEEP
hard-limit hit rate
emergency-finalization rate
```

关键目标：

```text
classifier invocation rate 尽可能低
```

明显任务应由 local router 解决。

---

# 38. Compaction

本次不要顺手改变 compaction 核心行为。

保持：

```text
_compaction_due
_compact_now
compaction_state
context overflow recovery
```

长 conversation 中：

```text
FAST_CHAT / KNOWLEDGE
```

仍然可能需要 compaction。

Fast path 的目标是：

```text
不进入工具循环
```

而不是完全绕过历史管理。

---

# 39. 推荐修改文件

核心：

```text
coworker/providers/openai_provider.py
coworker/engine.py
coworker/config.py
coworker/agent.py
```

新增：

```text
coworker/request_router.py
```

可能修改：

```text
coworker/providers/base.py
coworker/providers/capabilities.py
coworker/tools/...
```

仅在：

- structured/textual tool-call compatibility capability；
- schema projection；
- network/search tool classification

确实需要时。

不要为了本 Plan 大改所有 ToolSpec metadata。

测试优先：

```text
tests/test_providers.py
tests/test_engine.py
tests/test_engine_stop.py
tests/test_config.py
tests/test_request_router.py
tests/test_compaction_engine.py
```

能力保护回归还要复用仓库已有测试：

```text
tests/test_memory.py
tests/test_skills_sessions.py
tests/test_ask_user_upgrades.py
tests/test_plan_mode.py
tests/test_durable_resume.py
tests/test_automation.py
tests/test_self_wake.py
tests/test_wake_resume.py
tests/test_connectors.py
tests/test_mcp_connectors.py
tests/test_persona_connections.py
tests/test_standing_approvals.py
tests/test_subscriptions.py
```

不要求无关地修改这些文件；优先让现有测试继续通过。

---

# 40. Router Unit Test Matrix

新增：

```text
tests/test_request_router.py
```

## FAST_CHAT

```text
你好
您好
hi
hello
谢谢
thanks
好的
```

断言：

```text
FAST_CHAT
classifier_calls = 0
```

## KNOWLEDGE

```text
什么是苯？
解释一下芳香性。
SN1 和 SN2 有什么区别？
详细解释一下苯为什么具有芳香性。
```

断言：

```text
KNOWLEDGE
not DEEP
```

## VERIFIED

```text
苯的 CAS 是多少？
100-42-5 是什么物质？
苯的闪点是多少？
REACH 对这个物质有什么限制？
这个 VAT 是否有效？
今天苯价格是多少？
```

断言：

```text
VERIFIED
```

并检查允许工具集合。

## AGENT — Workspace / Execution

```text
读取 pyproject.toml
修改 engine.py
运行测试
分析 CSV
查几家供应商并整理表
```

→ AGENT

## AGENT — Product Action Gate

```text
记住我以后喜欢简短回答
明天上午 9 点提醒我联系 BASF
把这个结果发给 Jack
用这个 skill 处理
加载 chem-xxx skill
连接 CRM 并创建任务
```

断言：

```text
AGENT / existing product flow
not FAST_CHAT
not KNOWLEDGE
```

## DEEP_RESEARCH

```text
深度研究全球苯产业链，并交叉验证多个来源
完整研究特种化学品市场并形成行业报告
做 BASF 中国业务尽调
```

→ DEEP_RESEARCH

## Explicit NO_TOOLS

```text
不用任何工具，只根据已有知识解释苯的芳香性
```

断言：

```text
KNOWLEDGE
policy.no_tools = True
```

## Explicit NO_SEARCH

```text
不要搜索网络，读取本地 CSV 并总结
```

断言：

```text
AGENT
policy.no_search = True
policy.no_tools = False
```

## Explicit NO_EXTERNAL_NETWORK

```text
不要联网，修改本地 report.md
```

断言：

```text
AGENT
policy.no_external_network = True
local file tools remain eligible
```

## Conflicting Constraint

```text
不用任何工具，把本地文件改掉
```

断言：

```text
不能偷偷调用工具
route 可为 AGENT/constraint-error path
policy.no_tools = True
```

最终由执行层说明约束冲突。

## Follow-up

上一轮 DEEP：

```text
继续
```

→ DEEP

上一轮 AGENT：

```text
继续查
```

→ AGENT

上一轮 DEEP，下一轮：

```text
谢谢
```

→ FAST_CHAT

上一轮 DEEP，下一轮：

```text
继续，但不要联网
```

→ DEEP + `no_external_network=True`

## Pending State Guard

构造：

```text
pending ask_user
用户回复 A
```

断言：

```text
router 不把 "A" 当 FAST_CHAT
```

构造 durable resume pending tool calls：

断言：

```text
resume path 优先
```

## Pure-Answer Positive Whitelist / Uncertain Fallback

至少加入：

```text
“你好” / 纯翻译 / supplied-text 摘要
→ pure-answer eligible

“帮我处理一下这个”
“继续做完”
未来/unknown product-like verb fixture
→ 不得仅因没命中关键词进入 tools=None
→ legacy-safe AGENT / active flow
```

断言：

```text
uncertain != KNOWLEDGE fast fallback
uncertain != FAST_CHAT tools=None
```

## Tool Network Classification

纯 helper 测试：

```text
local file/memory/plan → LOCAL
web/remote provider/remote connector → REMOTE
unknown custom extra_tool → UNKNOWN
```

Projection/policy 测试：

```text
NO_EXTERNAL_NETWORK + UNKNOWN → absent
normal AGENT + UNKNOWN → present
NO_SEARCH + local file/memory → present
```

## Classifier Failure

模糊 product-action-like request + classifier timeout：

断言：

```text
legacy_fallback / AGENT
not KNOWLEDGE
```

verification-required request + classifier timeout：

断言：

```text
VERIFIED
not KNOWLEDGE
```

---

# 41. Provider Test — True Streaming + Compatibility Modes

至少新增三类测试。

## 41.1 `tools=None` 必须真正流式

获取第一个：

```python
next(provider.stream(...))
```

时，上游 iterator 不应该已经全部被消费。

这是 FAST_CHAT/KNOWLEDGE 防止重新出现 buffering 的最重要 regression test。

## 41.2 Structured Tool Call Path（最终阶段 / Known-Safe Only）

该测试对应的 true streaming 功能只能在 Capability Preservation Gate 之后启用。测试必须同时覆盖 kill switch：

```text
kill switch OFF / capability unknown
→ compat buffered
→ salvage-safe

kill switch ON + provider/model known-safe
→ structured tools true streaming
```

fake upstream：

```text
text delta
structured tool call argument split
final chunk
```

断言：

- text 可及时 yield；
- tool arguments 最终正确累积；
- final `AssistantTurn.tool_calls` 正确；
- 不重复工具调用。

## 41.3 Textual Tool-Call Salvage Compatibility

覆盖当前支持的至少一种 textual 格式：

```text
<tool_call>...</tool_call>
```

或：

```text
<function=write_file>...</function>
```

断言：

```text
用户可见 text delta 中不得出现 tool-call markup
最终得到结构化 ToolCall
```

如果实现采用 compat-buffered：

```text
允许该 case 不即时 text streaming
```

但必须保证能力不回归。

再补 bare JSON/toolname salvage 的现有相关测试不被删除。

---

# 42. Provider Test — Retry Before Progress

第一次：

```text
transport failure
before any semantic provider progress
```

第二次：

```text
OK
```

断言：

```text
2 stream requests
最终 OK
```

同时验证：

```text
usage-only / empty heartbeat
```

不会错误地阻止合理 retry。

---

# 43. Provider Test — No Retry After Progress

至少覆盖：

## Text Progress

第一次：

```text
partial-
↓
transport failure
```

断言：

```text
partial 已 yield
stream requests = 1
no complete fallback
exception surfaced
```

## Reasoning Progress

```text
reasoning delta
↓
transport failure
```

断言：

```text
stream requests = 1
```

## Structured Tool Progress

```text
tool call name/args delta
↓
transport failure
```

断言：

```text
stream requests = 1
no regenerate
```

## Textual Tool Candidate Progress

兼容 parser/buffer 已看到有效工具调用前缀后 transport failure：

断言：

```text
stream requests = 1
```

---

# 44. Integration Test — “你好”

最高优先级测试。

执行：

```python
events = _collect(engine, "你好")
```

断言：

```text
route = FAST_CHAT
classifier calls = 0
answer provider calls = 1
tool calls = 0
```

provider invocation：

```text
tools=None
```

事件：

```text
TURN_START
ASSISTANT_DELTA...
ASSISTANT_MESSAGE
TURN_END
```

不能有：

```text
TOOL_PROPOSED
TOOL_STARTED
TOOL_FINISHED
```

---

# 45. Integration Test — “你好”无 reasoning

如果 test provider 返回 reasoning + text：

FAST_CHAT 应：

```text
不向用户发送 REASONING_DELTA
```

仍正常发送：

```text
ASSISTANT_DELTA
ASSISTANT_MESSAGE
```

如果系统内部需要保存 reasoning metadata，可保留，但 UI 不显示。

---

# 46. Integration Test — KNOWLEDGE 无工具

输入：

```text
什么是苯？
```

断言：

```text
tools=None
provider calls=1
```

---

# 47. Integration Test — VERIFIED 最小工具集合

输入：

```text
苯的 CAS 是多少？
```

Fake Router：

```text
VERIFIED
allowed tools = lookup_chemical_identity
```

Recording provider 断言：

```text
tool schemas 中只有 lookup_chemical_identity
```

不应该包含：

```text
search_tenders
lookup_fx_rate
validate_eu_vat
search_sam_opportunities
```

---

# 48. Integration Test — VERIFIED 预算

使用循环 provider。

设置：

```python
verified_max_iterations = 3
```

断言：

```text
最多 3 tool-enabled iterations
kill switch OFF → legacy hard-limit behavior
kill switch ON + guard safe → exactly one emergency finalization
```

测试中不要真的循环 6 次。

---

# 49. Integration Test — AGENT Budget

测试 soft target 与 hard ceiling 分离。测试配置可使用小数字：

```python
agent_target_iterations = 3
max_iterations = 6
```

验证：

- 第 3 轮附近进入 convergence/delivery；
- 不在 soft target=3 时直接 hard stop；
- 真正 hard ceiling=6 才进入 hard-limit 语义；
- Emergency Finalization 只有 kill switch 开启且 guard 允许时才调用。

---

# 50. Integration Test — DEEP Budget

设置：

```python
deep_research_target_iterations = 4
max_iterations = 7
```

验证：

- soft target 触发 phase 收敛；
- 4 轮后仍可在必要时继续；
- 7 才是 hard ceiling。

不要 unit test 真执行 50/150 次。

---

# 51. Integration Test — Route Context 不污染 History

断言：

```python
assert not any(
    "Fast chat mode" in str(m)
    or "Knowledge mode" in str(m)
    or "Verified-answer mode" in str(m)
    or "Iteration budget notice" in str(m)
    for m in engine.messages
)
```

---

# 52. Integration Test — Stop

FAST_CHAT streaming：

```text
partial
↓
Stop
```

确认：

- partial 保存；
- 没有第二次 call；
- 没有 fallback；
- 没有 tool call。

AGENT Stop 行为也保持原测试。

---

# 53. Config Tests

修改：

```text
tests/test_config.py
```

V2 默认断言：

```python
assert cfg.max_iterations == 150  # legacy hard ceiling 保持不变
assert cfg.verified_max_iterations == 6
```

如果实现公开 soft-target config 字段，再断言：

```python
assert cfg.agent_target_iterations == 32
assert cfg.deep_research_target_iterations == 50
```

如果 soft target 采用内部 route defaults，则不要为了测试强行扩大 Config API；改在 router/profile tests 中断言 32/50。

workspace override 示例：

```toml
max_iterations = 60
agent_target_iterations = 40
deep_research_target_iterations = 55
verified_max_iterations = 8
```

断言：

```text
AGENT hard ceiling = 60
AGENT soft target = 40
DEEP hard ceiling = 60
DEEP soft target = 55
VERIFIED hard = min(8, 60)
```

还要验证：

```text
max_iterations=24 时，soft target 自动 cap 到 24
已有显式 max_iterations override 不会被 route default 32/50 覆盖
```

V5 必须额外验证 legacy-inert 行为：

```text
request_routing_enabled=false / no explicit ExecutionProfile
→ legacy execution 不自动获得 target_iterations=32/50
→ 不自动进入 Converge/Deliver
→ 仍只由既有 max_iterations / model_settings / state machine 控制

显式 ExecutionProfile + routing test path
→ 才允许激活 route-specific soft target / reasoning guidance
```

---

## 53A. Capability Preservation Gate — Router / Tool Filtering 合入后立即执行

> **V4 额外前置：Legacy Schema Snapshot / Kill-Switch Gate**
>
> 在执行本节原有 capability suites 之前，先保存至少以下代表性场景的 provider-visible tool name snapshot：
>
> ```text
> default knowledge/cowork session
> selected persona session
> forced/default skill session
> connector/MCP enabled session（环境允许时）
> extra_tools / unknown custom tool fixture
> ```
>
> 然后验证：
>
> ```text
> request_routing_enabled = false
> → legacy request execution path
> → 不进入新 classifier/fast route
> → 旧 registry/tool availability 不因 Router 消失
>
> tool_projection_enabled = false
> → provider-visible tool schemas 与该 session 的 legacy snapshot 等价
> → 不得因为 route=FAST_CHAT/KNOWLEDGE 自动 tools=None
>
> tool_projection_enabled = true + normal AGENT/DEEP + UNKNOWN/dynamic tool
> → 默认保留（除非显式 NO_TOOLS / NO_SEARCH / NO_EXTERNAL_NETWORK 等策略要求排除）
> ```
>
> snapshot 比较不要求固定排序；比较工具名集合与关键 schema identity 即可，避免因无意义顺序变化产生脆弱测试。


这是本 Plan 新增的**强制中间验收门**。

不要等最后 `pytest -q` 才发现产品能力被切断。

至少验证以下场景：

### Memory

输入：

```text
记住我以后喜欢简短回答
```

断言：

```text
not pure FAST_CHAT
memory tool/capability remains available
```

并运行现有：

```bash
pytest -q tests/test_memory.py tests/test_memory_api.py
```

### Skills

forced/default skill 场景：

```text
/skill ...
用 xxx skill ...
```

断言：

```text
load_skill capability 不被 tools=None 切掉
```

运行：

```bash
pytest -q   tests/test_skills.py   tests/test_skills_sessions.py   tests/test_skill_readonly_roots.py
```

### ask_user / Plan / Durable Resume

运行：

```bash
pytest -q   tests/test_ask_user_upgrades.py   tests/test_plan_mode.py   tests/test_durable_resume.py
```

必须保证：

```text
pending reply / approval / resume
优先于 router fast path
```

### Scheduling / Self Wake

运行：

```bash
pytest -q   tests/test_automation.py   tests/test_automation_create.py   tests/test_self_wake.py   tests/test_wake_resume.py
```

### Connectors / MCP / Persona

运行：

```bash
pytest -q   tests/test_connectors_allowlist.py   tests/test_mcp_connectors.py   tests/test_persona_connections.py
```

### Approval / Standing Rules

运行：

```bash
pytest -q   tests/test_tools_permissions.py   tests/test_standing_approvals.py
```

### Local File + No Network

新增 targeted integration：

```text
不要联网，读取本地 fixture 并总结
```

断言：

```text
no_external_network=True
file tools present
web/remote tools absent
```

### V5 Critical Product Smoke（HARD STOP E 前置人工验收）

自动测试之外，必须在真实 ChemClaw surface 或尽可能接近真实 SessionManager/build_engine 的集成环境中检查：

```text
1. 你好 → 能即时回答，不触发 product action
2. 记住我以后喜欢简短回答 → 真实 memory 写语义仍可达
3. /skill ... 或默认 Skill → load_skill 仍可达
4. ask_user / plan / durable resume → pending continuation 不被 fast route 截断
5. 明天上午 9 点提醒我联系 BASF → scheduling capability 仍可达（环境允许时）
6. selected persona → persona/default skill/connector 边界仍按原行为工作
7. 不要联网，读取本地 fixture → 本地文件可用，remote/web 不暴露
8. connector/MCP 至少一例 → 正常 AGENT/DEEP 不因 tool projection 静默丢失（环境允许时）
```

若本机/CI 环境无法真实执行某项，报告必须写：

```text
ENV BLOCKED — manual validation pending
```

不能把这一项写成 PASS；用户可据此决定是否允许进入 HARD STOP F。

### Stop + Finalization Guard

构造：

```text
接近 hard limit
↓
user Stop
```

断言：

```text
no emergency finalization call
```

构造 pending ask_user/plan：

断言：

```text
no emergency finalization call
```


### V2 Extra Gate — Retry Ownership / Unknown Tool / Kill Switch

必须额外验证：

```text
stream SDK retry ownership 不影响 non-stream complete 韧性
NO_EXTERNAL_NETWORK + unknown custom tool → provider schema 中不存在
normal AGENT + unknown custom tool → legacy schema 仍存在
structured-tools streaming kill switch OFF → compat buffered
emergency finalization kill switch OFF → legacy hard-limit behavior
```

只有这个 Gate 通过，才能继续做 aggressive tool projection / instrumentation 收尾。

---

# 54. 每个 Phase 完成后的测试

## Streaming / Provider

```bash
pytest -q tests/test_providers.py
pytest -q tests/test_provider_router.py
```

必须额外覆盖：

```text
tools=None true streaming
structured tool-call accumulation（始终）
textual tool-call salvage 不泄露（始终）
retry-before-progress
no-retry-after-text/reasoning/tool progress
stream client retry ownership / non-stream retry preservation

Capability Gate 之前：
  tools-enabled structured true streaming 可保持 OFF / compat-buffered

Capability Gate 之后：
  known-safe structured true streaming + kill switch ON/OFF 都要测
```

## Router

```bash
pytest -q tests/test_request_router.py
```

必须覆盖：

```text
Product Action Gate
Pure-Answer Positive Eligibility Gate
uncertain request → legacy-safe fallback
NO_TOOLS / NO_SEARCH / NO_EXTERNAL_NETWORK
UNKNOWN custom tool policy
pending-state guard
classifier legacy-safe fallback
```

## Engine

```bash
pytest -q tests/test_engine.py
pytest -q tests/test_engine_stop.py
```

## Config

```bash
pytest -q tests/test_config.py
```

## Capability Preservation Gate

执行 Section 53A 的 targeted suites。

## Compaction

```bash
pytest -q   tests/test_compaction.py   tests/test_compaction_engine.py   tests/test_compaction_smoke.py
```

不要一次改完全部再跑测试。

推荐节奏：

```text
provider change
→ provider tests

router gate
→ router tests

tool projection
→ capability preservation gate

budget/finalization
→ engine/stop/plan/resume tests

最后
→ full regression
```

---

# 55. Full Regression

先运行本次最相关组合：

```bash
pytest -q   tests/test_providers.py   tests/test_provider_router.py   tests/test_request_router.py   tests/test_engine.py   tests/test_engine_stop.py   tests/test_config.py   tests/test_compaction.py   tests/test_compaction_engine.py   tests/test_compaction_smoke.py   tests/test_token_usage.py   tests/test_memory.py   tests/test_memory_api.py   tests/test_skills_sessions.py   tests/test_ask_user_upgrades.py   tests/test_plan_mode.py   tests/test_durable_resume.py   tests/test_automation.py   tests/test_self_wake.py   tests/test_wake_resume.py   tests/test_connectors_allowlist.py   tests/test_mcp_connectors.py   tests/test_persona_connections.py   tests/test_tools_permissions.py   tests/test_standing_approvals.py
```

如果某些文件名在当前分支已变化：

- 以当前 repo 为准；
- 选择等价测试；
- 不得因为文件名变化而跳过该能力类别。

最后：

```bash
pytest -q
```

必须记录：

```text
baseline failures
new failures
fixed/changed expected tests
```

不能只报告“多数通过”而忽略新增回归。

---

# 56. Manual Smoke Test A — Greeting

输入：

```text
你好
```

正确日志：

```text
route=fast_chat
source=local
classifier_used=false
tools_enabled=false
allowed_tool_count=0
max_iterations=1
reasoning_mode=off
```

正确结果：

```text
Classifier calls = 0
Answer model calls = 1
Tool calls = 0
```

---

# 57. Manual Smoke Test B — Stable Chemistry Knowledge

输入：

```text
什么是苯？为什么具有芳香性？
```

预期：

```text
KNOWLEDGE
1 model call
0 tools
无外部验证声明
```

---

# 58. Manual Smoke Test C — Chemical Identity

输入：

```text
苯的 CAS 是什么？
```

预期：

```text
VERIFIED
targeted chemical identity tool
快速返回
```

不要进入：

```text
32-round AGENT
```

---

# 59. Manual Smoke Test D — Safety / Regulation

输入：

```text
苯在欧盟 REACH 下有哪些重要限制？
```

预期：

```text
VERIFIED 或 AGENT
必须使用相关专业/实时验证工具
```

不能 KNOWLEDGE 直接拍脑袋回答。

---

# 60. Manual Smoke Test E — Market

输入：

```text
今天国际苯市场有什么重要变化？
```

预期：

```text
VERIFIED/AGENT
current-data tools enabled
```

---

# 61. Manual Smoke Test F — Deep Research

输入：

```text
深度研究全球苯产业链、供需、主要生产商和未来五年趋势，
要求多来源交叉验证并形成完整报告。
```

预期：

```text
DEEP_RESEARCH
soft≈50 / hard=config.max_iterations（默认 150）
Explore → Converge → Deliver
```

---

# 62. Manual Smoke Test G — Route Reset

连续输入：

```text
1. 深度研究全球 PA66 市场
2. 继续
3. 谢谢
4. 你好
```

预期：

```text
1 DEEP
2 DEEP
3 FAST_CHAT
4 FAST_CHAT
```

---

# 63. Manual Smoke Test H — Real Streaming + Tool Compatibility

## H1 — Pure answer true streaming

让 FAST_CHAT/KNOWLEDGE 模型生成长回答。

观察：

```text
首个 token 到达
↓
UI 立即出现
```

不能：

```text
整段完成
↓
一次性显示
```

## H2 — Structured tools-enabled streaming

对确认支持 structured tool calls 的 compat provider：

```text
普通 text delta
→ 可及时显示

tool call delta
→ 正确内部累积
```

不能破坏最终 ToolCall。

## H3 — Textual tool-call compatibility

对 Ollama/Qwen/Hermes 类 textual tool-call fixture：

观察：

```text
用户界面不能出现：
<tool_call>
<function=...>
内部 JSON tool call markup
```

最终必须仍转换成结构化 ToolCall。

允许该兼容路径为了安全继续局部/完整 buffering。

同样，如果非 FAST_CHAT 路径展示 narration：

```text
正在查询…
```

应该及时显示。

---

# 64. Manual Smoke Test I — Transport Failure

模拟 compat gateway：

```text
before any semantic provider progress
→ retry once
```

```text
after text progress
→ no retry
```

```text
after reasoning progress
→ no retry
```

```text
after structured tool-call progress
→ no retry
```

```text
after textual-tool-call candidate progress
→ no retry
```

确保：

- 没有重复文本；
- 没有重复工具调用；
- 没有 3 次 stream + complete 的旧式叠加。


---


# 64A. Manual Smoke Test J — Memory Action

输入：

```text
记住我以后更喜欢简短回答
```

预期：

```text
Product Action Gate hit
not pure FAST_CHAT
memory capability available
```

不能只回复：

```text
好的，我记住了
```

却没有实际进入当前 memory 写入语义。

---

# 64B. Manual Smoke Test K — Scheduling Action

输入：

```text
明天上午 9 点提醒我联系 BASF
```

预期：

```text
Product Action Gate hit
scheduling tool available
```

不能 FAST_CHAT 文本承诺后不创建任务。

---

# 64C. Manual Smoke Test L — No Network + Local File

输入：

```text
不要联网，读取本地 sample.csv 并整理成 Markdown 表
```

预期：

```text
Route = AGENT
no_external_network = true
local file tools = available
remote/web tools = absent
```

---

# 64D. Manual Smoke Test M — No Tools

输入：

```text
不用任何工具，只根据已有知识解释苯的芳香性
```

预期：

```text
Route = KNOWLEDGE
no_tools = true
provider tools = None
```

---

# 64E. Manual Smoke Test N — Pending ask_user / Plan / Resume

分别构造：

```text
pending ask_user → 用户回复 A
pending plan approval → 用户同意
durable resume pending tool call → resume
```

预期：

```text
existing state machine continues
router fast path does not intercept
```

---

# 64F. Manual Smoke Test O — Forced Skill / Selected Persona

选择一个依赖 `load_skill` 的 persona/skill。

输入对应任务。

预期：

```text
skill capability remains available
selected persona remains selected
```

不能因为请求表面上像“写作/总结”就 `tools=None`。

---

# 64G. Manual Smoke Test P — Classifier Failure

人为让 tiny classifier timeout。

输入：

```text
帮我把这个本地文件处理完并发出去
```

预期：

```text
source = legacy_fallback
Route = AGENT / legacy execution
```

不能：

```text
KNOWLEDGE
tools=None
```

---

# 64H. V5 Cross-Window Handoff — Execution Log

正式交给 Cursor Auto 前，建议把本 Plan 放入仓库：

```text
docs/superpowers/plans/2026-08-13-chemclaw-performance-router-v5.md
```

并建立：

```text
docs/superpowers/plans/2026-08-13-chemclaw-performance-router-v5-execution-log.md
```

execution log 每个 HARD STOP 追加而不是覆盖，至少记录：

```text
Run / HARD STOP ID
Start SHA
End/checkpoint SHA
Start git status --short
User-existing dirty changes
Governance/design files re-read
Allowed Section 65 step range
Expected files/symbols
Actual changed files
git diff --stat
Key diff summary
PASS
EXISTING FAIL
NEW FAIL
NOT RUN
ENV BLOCKED
request_routing_enabled built-in/test values
tool_projection_enabled built-in/test values
structured-tools streaming built-in/test values
emergency finalization built-in/test values
legacy provider-visible schema snapshot/parity（相关阶段）
Critical Product Smoke（相关阶段）
Rollback point
Remaining risks
Next run allowed range
```

新 Cursor 窗口的恢复顺序必须是：

```text
AGENTS.md / 当前已批准治理与设计
↓
Git SHA / status / log / current implementation
↓
v5 Plan
↓
execution log
```

execution log 不能成为新的“真相数据库”。如果它说“已完成 HARD STOP D”，但 Git/current code 不支持这个结论，必须 STOP 并报告冲突。

---

# 65. 推荐实施顺序（V5 Cursor Auto Safe 顺序）

严格按以下顺序，先锁住兼容性，再逐步打开优化。**structured-tools true streaming 与 Emergency Finalization 移到 Capability Gate 之后。**

> **V5 强制执行语义：Section 65 是唯一允许的自动实施顺序。每个 HARD STOP 都是“本次 Agent run 的终点”，不是普通检查点。即使测试全部通过，也不得在同一次 Auto run 中越过。A–G 建议分别使用独立 Cursor 对话窗口。**
>
> **每个 HARD STOP 后的新 run 开始前都重复执行：**
>
> ```text
> re-read AGENTS.md + ChemClaw README + approved design + DECISIONS + DOMAIN + relevant current plan
> → re-read v5 execution log
> → record git SHA/status + existing dirty changes
> → compare Git / governance docs / execution log；冲突则 STOP
> → restate this run's exact step range and expected files/symbols
> → confirm no downstream phase files were pre-touched
> ```
>
> **上下文恢复原则：** 不依赖上一 Cursor 聊天窗口。上一窗口的自然语言总结不是事实来源；事实来源优先级是“当前仓库已批准治理/设计约束 + Git/工作区真实状态”，execution log 只做交接索引。

```text
1. baseline：记录 git SHA / git status / existing failures
2. 记录现有 provider/tool salvage 行为
3. 为 textual tool-call salvage 补回归测试
```

## ⛔ HARD STOP A — Baseline / Compatibility Characterization

完成 1–3 后必须 STOP。

必须汇报 baseline SHA/status、现有失败、现有 streaming/retry/salvage 行为及新增 characterization tests。**不得在同一次 Agent run 中开始第 4 步。**

```text
4. tools=None true streaming（只做最安全收益）
5. streaming retry-before-progress / no-retry-after-progress
6. streaming client explicit timeout + max_retries=0
7. non-stream client 保持原 SDK retry ownership
8. provider targeted tests
```

## ⛔ HARD STOP B — Provider Streaming / Retry Boundary

完成 4–8 后必须 STOP。

必须证明：`tools=None` true streaming、textual salvage 未被破坏、semantic progress 后不 regenerate、stream/non-stream retry ownership 分离。**不得在同一次 Agent run 中开始 reasoning/budget/router。**

```text
9. reasoning-mode plumbing

10. 保留 max_iterations=150 hard ceiling
11. AGENT soft target≈32
12. DEEP soft target≈50
13. VERIFIED hard≈6
14. budget phases（soft target 驱动 Converge/Deliver）
15. engine budget tests（此时 Emergency Finalization kill switch 仍 OFF）
```

## ⛔ HARD STOP C — Reasoning / Soft-Budget Boundary

完成 9–15 后必须 STOP。

必须确认 built-in `max_iterations` 仍为 **150 hard ceiling**；AGENT `32`、DEEP `50` 仅为 soft target；Stop/resume/compaction 基础语义无新增回归；Emergency Finalization 仍保持 OFF。

**V5 额外硬条件：本阶段的 budget/reasoning plumbing 对 legacy path 必须 inert。** 在 `request_routing_enabled=false`、Router 尚未接线、或没有显式 `ExecutionProfile` 时，旧 session 不得自动获得 32/50 soft target、Converge/Deliver guidance 或新的 route reasoning default。必须有测试证明这一点。**不得在同一次 Agent run 中开始 Router。**

```text
16. request_router.py skeleton + request_routing_enabled kill switch（默认先 OFF）
17. Pending-State Guard
18. Selected Persona / Forced Skill Guard
19. Product Action Gate
20. Pure-Answer Positive Eligibility Gate
21. NO_TOOLS / NO_SEARCH / NO_EXTERNAL_NETWORK policy
22. centralized network_scope / usage_class helper

23. FAST_CHAT
24. KNOWLEDGE
25. chemical verification risk gate
26. VERIFIED
27. AGENT
28. DEEP_RESEARCH
29. continuation inheritance

30. tiny classifier
31. classifier timeout
32. legacy-safe fallback（uncertain 不得 fallback KNOWLEDGE）

33. ExecutionProfile（hard ceiling + soft target）
```

## ⛔ HARD STOP D — Router Semantics Before Tool Projection

完成 16–33 后必须 STOP。

必须先证明 pending-state、selected persona、forced skill、product action、ToolPolicy、pure-answer positive whitelist、classifier failure fallback 和 continuation inheritance 的路由语义正确。**此时不得做 aggressive/per-turn tool filtering；不得在同一次 Agent run 中开始第 34 步。**

```text
34. tool_projection_enabled kill switch（默认先 OFF）+ per-turn pure tools=None
35. VERIFIED targeted tool filtering
36. conservative AGENT/DEEP projection
37. tool policy final filtering
38. UNKNOWN/dynamic/extra_tools tool policy + legacy schema parity tests

39. Capability Preservation Gate + V5 Critical Product Smoke
    - memory
    - skills
    - ask_user
    - plan
    - durable resume
    - scheduling/self-wake
    - connectors/MCP/persona
    - permissions
    - local file + no network
    - unknown custom tool behavior
    - non-stream retry ownership
```

## ⛔ HARD STOP E — Capability Preservation Gate

完成 34–39 后必须 STOP，**即使 Gate 全绿也必须停**。

这一断点必须单独汇报每一类 capability 的测试结果和任何无法执行的环境原因。若出现新增能力回归，必须在本段回退/收窄 tool projection，不能继续。**不得在同一次 Agent run 中开启 structured-tools true streaming 或 Emergency Finalization。**

V5 额外要求：必须同时给出 `request_routing_enabled` / `tool_projection_enabled` **测试显式 ON/OFF** 的结果、legacy schema parity 摘要与 Critical Product Smoke 状态。若 manual smoke 尚有 `ENV BLOCKED`，只能写 `automated gate passed; manual validation pending`，不得写“Router/Projection 已完全验收”。**本 HARD STOP 不允许修改任何 risky built-in default；它们继续保持 OFF。**

只有 Gate 通过、且用户在新的执行指令中明确允许继续后，才进入：

```text
40. structured-tools true streaming implementation（known-safe only）
41. structured-tools kill switch / capability tests
42. textual salvage compatibility re-run
```

## ⛔ HARD STOP F — Structured-Tools Streaming Boundary

完成 40–42 后必须 STOP。

必须同时给出 kill switch **测试显式 ON/OFF**、known-safe provider/model 与 unknown/custom compat 的结果，证明关闭开关可回到 compat-buffered + salvage-safe。**structured-tools true streaming 的 built-in default 仍保持 OFF；不得在同一次 Agent run 中实现/启用 Emergency Finalization。**

只有上述再次通过、且用户在新的执行指令中明确允许继续后，才进入：

```text
43. Emergency Finalization implementation + test-only enablement（built-in default 仍 OFF）
44. Stop/pending/resume guards + kill switch tests
45. engine/stop/plan/resume regression
```

## ⛔ HARD STOP G — Emergency Finalization Boundary

完成 43–45 后必须 STOP。

必须证明 Stop、pending ask_user/approval/plan/request_directory、durable resume 不会触发错误 finalization；kill switch OFF 可保持 legacy hard-limit behavior。**Emergency Finalization built-in default 仍保持 OFF。不得在同一次 Agent run 中继续 instrumentation / cleanup / final regression。**

只有以上再次通过、且用户在新的执行指令中明确允许继续后：

```text
46. batching guidance
47. duplicate-tool warning
48. instrumentation

49. targeted regression
50. compaction regression
51. capability regression
52. full pytest
53. git diff --check
54. manual diff review
55. manual smoke tests A–P
```

完成 46–55 后必须先结束该 Agent run，并形成最终 regression 报告。**即使全部通过，也不得在同一次 run 修改 risky built-in defaults。**

## ⛔ V5 POST-REGRESSION ROLLOUT STOP — Default Enablement Boundary

只有 A–G、46–55、full pytest、manual diff review 与 manual smoke 已完成，且不存在 unresolved `NEW FAIL` / capability regression 后，用户才可以在**新的独立 Cursor run** 中授权默认开关 rollout。

Rollout 不是新的架构实现，只允许一次启用一个故障域，并在每一步后立即回归：

```text
56. request_routing_enabled built-in default：OFF → 候选 ON
    tool_projection / structured streaming / emergency finalization 仍 OFF
    → Router + pending/product-action/capability smoke

57. tool_projection_enabled built-in default：OFF → 候选 ON
    → legacy parity counterpart + Memory/Skills/ask_user/plan/resume/
      scheduling/persona/local-file-no-network/connector-MCP/unknown-tool smoke

58. structured-tools true streaming built-in default：仅 known-safe provider/model 候选 ON
    unknown/custom 仍 compat-buffered
    → structured + textual salvage + Stop/retry regression

59. Emergency Finalization built-in default：最后候选 ON
    → hard-ceiling + Stop + pending + durable-resume regression
```

每一步规则：

```text
一次只翻一个 built-in default
↓
立即运行该故障域 targeted + capability smoke
↓
出现任何 NEW FAIL / silent capability loss
→ 立刻恢复该开关 OFF
→ 不继续后续 rollout
```

如果最终仍有关键 `ENV BLOCKED`，允许的保守结果是对应 built-in default 继续 OFF；不得为了“完成 Plan”强行开启。

Rollout run 结束时必须输出最终建议默认值与证据，并 STOP；仍不得自动 push/merge。

不要一次改完全部再跑测试。

特别禁止：

```text
先实现 aggressive tool filtering
↓
最后才发现 memory/skill/schedule/resume 全坏了
```

也特别禁止：

```text
一开始就同时开启
structured-tools true streaming
+ emergency finalization
+ hard ceiling 150→32
```

正确顺序必须是：

```text
先 baseline + compatibility tests
↓
HARD STOP A
↓
先拿 tools=None streaming 的安全收益
↓
HARD STOP B
↓
reasoning + soft budget
↓
HARD STOP C
↓
先 guard + positive whitelist + route semantics
↓
HARD STOP D
↓
再 filter
↓
立即 capability gate
↓
HARD STOP E
↓
structured-tools true streaming（known-safe only）
↓
HARD STOP F
↓
Emergency Finalization
↓
HARD STOP G
↓
最后 instrumentation + full regression + smoke
↓
结束该 run
↓
独立 post-regression rollout（用户再次明确授权）
```

任何新的能力回归出现：

```text
STOP 后续优化
→ 收窄/回退当前 Phase
→ 重新跑对应 Gate
→ 未解决则保持旧行为并结束当前段
```

---

# 66. Cursor 执行要求

请直接修改代码，不要只输出建议。

> **V5 Auto 执行边界：**“请直接修改代码”只适用于**当前 HARD STOP 之前**的步骤。到达 HARD STOP A–G 时必须结束当前 Agent run；不得把本节理解为“自动完成整份 Plan”。继续下一段必须有用户新的明确指令。A–G 与 post-regression rollout 均建议使用新的独立 Cursor 对话。

开始前（**每一个新的 Auto run 都重复，不得只在 HARD STOP A 前做一次**）：

1. 阅读仓库 `AGENTS.md`；
2. 按 `AGENTS.md` 当前要求继续阅读 `docs/chemclaw/README.md`、已批准产品设计、`docs/chemclaw/DECISIONS.md`、`docs/chemclaw/DOMAIN.md`、当前相关实施计划；
3. 记录当前 `git rev-parse HEAD` / `git status --short`，识别用户已有 dirty changes，不覆盖、不混入；
4. 阅读当前实现；
5. 确认当前文件路径和 API 是否与本 Plan 一致；
6. 阅读 `openai_provider.py` 当前 textual tool-call salvage 实现；
7. 阅读 `build_engine()` 当前完整工具注册流程；
8. 阅读 pending ask_user / plan / request_directory / durable resume / Stop 实现；
9. 阅读 v5 execution log（存在时），并用 `git log --oneline -12` / `git show --stat HEAD` / 当前 status 交叉验证；日志不能覆盖 Git 或当前治理文档；
10. 列出本 run 仅允许执行的 Section 65 步骤范围、预计修改文件/符号、预期测试；
11. 如果代码/已批准决策已变化，以当前仓库为准；若与本文行为目标冲突，停止并报告冲突，不得静默改写已批准产品约束。

实现时：

- 小范围修改；
- 本 run 先声明预计修改范围；发现必须扩展到非当前 Phase 的核心模块时先 STOP 汇报；
- 不做 unrelated refactor；
- 不为了“统一架构”提前改下一 HARD STOP 才需要的文件/开关；
- 关键行为必须有测试；
- 不为了通过测试削弱断言；
- 旧测试如果验证的是明确被改变的旧行为，应更新；
- 保持 public interface 尽量兼容；
- 不引入新 Agent 框架；
- Router 只能裁 provider 可见 schema，不能永久删 runtime registry；
- `request_routing_enabled=false` 必须恢复 legacy request execution 选择；
- `tool_projection_enabled=false` 必须恢复当前 session 的 legacy provider-visible schema exposure；
- Router/Projection kill switch 必须互相独立，关闭一个不能依赖另一个才能恢复；
- 不把 selected persona 替换成 Router route；
- 不把 pending interaction 当普通新请求；
- 不把 NO_NETWORK 等同于 NO_TOOLS；
- 不为了 streaming 删除 salvage；
- classifier 失败时采用 legacy-safe fallback；
- 任何 aggressive optimization 必须先有 regression test；
- 不把 `max_iterations` built-in default 从 150 改成 32/50；32/50 只做显式 route-selected ExecutionProfile 的 soft target；在 Router OFF / no explicit profile 的 legacy path 中必须 inert；
- streaming client 与 non-stream client 的 SDK retry ownership 必须分开；
- FAST_CHAT/KNOWLEDGE 必须来自 pure-answer 正向白名单，不能靠“没检测到动作词”推断；
- `NO_EXTERNAL_NETWORK` 的 UNKNOWN custom tool 默认不发送；普通 AGENT/DEEP 的 UNKNOWN tool 默认保留；
- `extra_tools` / 动态 connector / MCP / 新增平台工具若分类 helper 不认识，普通 AGENT/DEEP 默认保留，不得因 metadata 缺失静默消失；
- structured-tools true streaming 与 Emergency Finalization 必须有 kill switch；阶段内只允许测试显式启用，built-in default 在 A–G + final regression 完成前始终 OFF；
- 如果任一 capability regression 新增失败，停止后续 Phase，不得继续堆叠优化后再统一处理；
- 不为了通过新 Router 测试删除/放宽 durable resume、approval、memory、skills、connector/MCP 等旧断言；
- `skip` / `xfail` / 环境不可用必须单列，不得计入通过率或写成“已验证”；
- 每个 HARD STOP 形成 rollback point；禁止自动 push/merge/tag/rebase；
- 每个 HARD STOP 更新 v5 execution log；新窗口不得依赖上一窗口聊天记忆恢复事实；
- 只有完成 A–G + 46–55 且用户新开独立 rollout run 明确授权后，才允许逐个评估 built-in default 是否从 OFF 改为 ON。

如果实现过程中发现本 Plan 某个优化与当前代码已有兼容机制冲突：

```text
优先保留当前能力
+
采用较保守优化
+
在最终报告注明
```

不要为了“严格照 Plan”故意破坏已有功能。

---

# 67. 必须保持的现有能力

不能回归：

```text
tool call accumulation
textual tool-call salvage
Qwen/Hermes/Ollama-style textual tool compatibility
parallel low-risk tools
serial write/shell tools
permissions
approval flow
standing approvals
ask_user
plan mode
request_directory
interrupt/Stop
durable resume
partial assistant persistence
compaction
model switching
reasoning metadata
token usage
provider routing
custom OpenAI-compatible endpoints
workspace config overrides
memory read/write semantics
skills/load_skill/forced skill
selected persona behavior
scheduling / automation
self-wake
messaging / send_file
connectors
MCP
subscriptions
```

额外兼容性要求：

```text
Router 不得成为上述能力的上级开关。
```

如果某个能力在当前 agent/persona 本来不可用，本 Plan 不要求凭空增加。

如果某个能力当前可用，本 Plan 不得因为性能优化让它静默消失。

V5 额外判定：

```text
provider-visible schema 中旧工具无理由消失
OR
product action 不再真实调用工具
OR
pending continuation 被错误当作新请求 fast-route
OR
kill switch OFF 无法恢复 legacy 行为
```

以上任一项都属于 capability regression，即使最终文字回答看起来“还可以”、即使 pytest 其余部分全绿，也必须处理。

---

# 68. Definition of Done

全部满足才完成：

## Streaming / Provider

- `tools=None` true streaming 已实现；
- provider 不再对 pure answer path 完整 buffering 后再 yield；
- structured tool-call path 仅在安全 provider/model + kill switch 开启时真流式；关闭开关可回到 compat buffering；
- textual tool-call salvage 兼容仍有效；
- `<tool_call>` / `<function=...>` 等内部 markup 不泄露到 UI；
- semantic provider progress 后不重新完整 retry；
- tool-call progress 也会阻止 regenerate；
- streaming SDK hidden retry 已由 ChemClaw 明确接管，non-stream 没有被误伤；
- timeout 有明确边界。

## Reasoning

- FAST_CHAT reasoning 可关闭；
- FAST_CHAT 不展示 reasoning；
- unsupported provider 不被强行传 reasoning 参数。

## Budget / Finalization

- built-in `max_iterations` legacy hard ceiling 默认仍为 150；
- AGENT route-selected soft target 默认≈32；
- Deep Research route-selected soft target 默认≈50；
- Router OFF / no explicit ExecutionProfile 的 legacy path 不自动应用 32/50 soft target、Converge/Deliver 或新的 route reasoning default；
- Verified default hard = 6；
- 显式 `max_iterations` config override 仍决定最终 hard ceiling；
- active continuation/resume 不被 Router 中途降成 1 轮；
- Agent/Deep 有 Explore → Converge → Deliver，且 phase 由 soft target 驱动、不是由 150 hard ceiling 的百分比驱动；
- Emergency Finalization 有 kill switch；A–G 与 final regression 期间 built-in default 始终 OFF；只有独立 post-regression rollout run 逐项验证后才允许候选默认开启；
- Stop 不触发 finalization；
- pending ask_user/approval/plan/resume 不触发错误 finalization。

## Router

- `request_routing_enabled=false` 可恢复 legacy request execution 行为；
- Router 是 per-turn optimization layer；
- pending-state guard 优先于 Router；
- selected persona/forced skill 能力不被 Router 覆盖；
- Product Action Gate 已实现；
- greeting 不调用 classifier；
- FAST_CHAT/KNOWLEDGE 只来自 pure-answer 正向白名单；uncertain request 走 legacy-safe fallback；
- “你好” = 0 classifier + 1 answer call + 0 tools；
- “什么是苯” = KNOWLEDGE + 0 tools；
- 精确化工事实进入 VERIFIED；
- Safety/Regulation/Current data 默认验证；
- VERIFIED 只暴露必要工具；
- AGENT 默认不会自动升级 DEEP；
- DEEP 只在明确研究意图下进入；
- classifier failure 不默认 fallback KNOWLEDGE；
- 模糊失败使用 legacy-safe fallback。

## Tool Policy / Filtering

- `tool_projection_enabled=false` 可恢复当前 session 的 legacy provider-visible schema exposure；
- Router 与 Tool Projection kill switch 分离并分别有测试；
- `NO_TOOLS`、`NO_SEARCH`、`NO_EXTERNAL_NETWORK` 语义分离；
- network_scope / usage_class 通过统一 helper 判断；
- `NO_EXTERNAL_NETWORK + UNKNOWN` 默认排除，普通 `AGENT/DEEP + UNKNOWN` 默认保留；
- dynamic `extra_tools` / connector / MCP / future platform tool 在普通 AGENT/DEEP 不因分类缺失静默丢失；
- “不要联网 + 本地文件操作”仍可工作；
- pure FAST_CHAT/KNOWLEDGE provider `tools=None`；
- runtime registry 没有被 per-turn filtering 永久删改；
- VERIFIED 最小工具集合；
- AGENT/DEEP 在无法安全裁剪时保留 legacy capabilities；
- route context/tool policy 不污染 canonical history。

## Capability Preservation

以下现有能力相关测试通过或无新增回归：

- memory；
- skills；
- ask_user；
- plan mode；
- request_directory；
- durable resume；
- automation/self-wake；
- connectors/MCP；
- persona；
- permissions/standing approvals；
- Stop；
- compaction；
- provider routing；
- custom OpenAI-compatible endpoints。

## Regression

- V5 HARD STOP A–G 均按要求分段执行；没有任何一次 Cursor Auto run 自动跨越硬断点；
- 每个新 Auto run 都重新读取并汇报仓库当前治理/设计约束，并用 Git + v5 execution log 恢复进度；
- 每个 HARD STOP 都有 rollback point；没有自动 push/merge/tag/rebase；
- HARD STOP D/E 已保存并比较 legacy provider-visible schema snapshot；
- HARD STOP E Critical Product Smoke 已完成，或未执行项明确标记 `ENV BLOCKED — manual validation pending`；
- Section 53A Capability Preservation Gate 已执行；
- targeted tests 已执行；
- full pytest 已执行；
- `git diff --check` 通过；
- manual smoke A–P 已完成或明确记录无法执行的环境原因；
- A–G + final regression 完成前四个 risky built-in defaults 均保持 OFF；
- 如执行默认开关 rollout，必须在独立 run 中按 routing → projection → known-safe structured streaming → emergency finalization 顺序逐个启用、逐个回归；任何失败均恢复当前开关 OFF 并停止后续 rollout。

---

# 69. Cursor 最终汇报格式

完成后必须输出：

```text
1. Changed files
2. 每个文件做了什么
3. Streaming 新语义
4. structured vs textual tool-call compatibility 策略
5. Retry 新语义
6. Timeout / SDK retry 设置
7. Reasoning 新策略
8. Router 实现
9. Pending-State / Product Action / Persona-Skill Guards
10. NO_TOOLS / NO_SEARCH / NO_EXTERNAL_NETWORK 语义
11. FAST_CHAT / KNOWLEDGE / VERIFIED / AGENT / DEEP 的判定规则
12. 每个 route 的 tools / reasoning / soft target / hard ceiling
13. VERIFIED 的最小工具暴露策略
14. AGENT/DEEP 的兼容性 tool projection 策略
15. Classifier failure fallback
16. Agent budget / convergence / delivery 行为
17. Emergency finalization guard
18. request_routing_enabled / tool_projection_enabled ON/OFF 结果
19. Legacy provider-visible tool schema parity 结果
20. Capability Preservation Gate + Critical Product Smoke 结果
21. Targeted tests 结果
22. Full pytest 结果
23. Baseline unrelated failures / NEW failures / NOT RUN / ENV BLOCKED
24. Rollback point（checkpoint commit 或 SHA + diff）
25. 实际修改范围 vs 预计修改范围
26. 尚存风险
27. 下一阶段建议
28. Legacy-inert budget/reasoning 验证结果
29. v5 execution log / cross-window handoff 状态
30. 四个 risky built-in defaults 当前实际值
31. 若已执行 rollout：每个默认值逐项启用的证据/回退结果
```

并单独列出以下 smoke result：

```text
Input: 你好

Route =
Classifier calls =
Answer model calls =
Tool calls =
Tools sent to provider =
Reasoning shown =
TTFT =
```

正确预期：

```text
Route = FAST_CHAT
Classifier calls = 0
Answer model calls = 1
Tool calls = 0
Tools sent to provider = None
Reasoning shown = 0
```

再列：

```text
Input: 什么是苯？

Route = KNOWLEDGE
Tool calls = 0
```

再列：

```text
Input: 苯的 CAS 是多少？

Route = VERIFIED
Allowed tools = [lookup_chemical_identity]
```

再列：

```text
Input: 不要联网，读取本地 sample.csv 并整理

Route = AGENT
No external network = true
Local file tools available = true
Remote tools sent = 0
```

再列：

```text
Input: 记住我喜欢简短回答

Product Action Gate =
Route/Profile =
Memory capability available =
Actual memory action completed =
```

再列：

```text
Textual tool-call compatibility smoke

Provider/model =
Stream mode =
Markup leaked to UI = false
Final structured tool call =
```

最后运行：

```bash
git diff --check
git diff
```

确认没有：

- API key；
- debug print；
- 临时代码；
- 无关格式化；
- 意外大范围重构；
- 为性能删掉的既有产品能力。

不要 commit / push，除非用户明确要求。

---

# 70. 最终架构原则

本次改造后，ChemClaw 应遵循以下原则：

> **简单聊天不思考、不用工具、直接流式回答。**

> **稳定的化工基础知识直接回答，不因“化工专业”就无脑跑工具。**

> **精确身份、精确物性、安全、法规、实时市场、企业状态等事实做最小必要验证。**

> **一两个工具能完成的事实验证不要进入长 Agent；AGENT 应以约 32 轮为收敛目标，而不是 32 轮硬砍。**

> **复杂执行任务、产品动作、文件/连接器/Skill/Memory/提醒等能力进入兼容的 Agent execution path。**

> **明确的系统性研究任务才进入 Deep Research。**

> **Router 是性能优化层，不是产品能力的总开关。**

> **selected persona、forced skill、pending approval/ask_user/plan、durable resume 等状态优先于 Router。**

> **“不要联网”“不要搜索”“不用工具”必须按不同约束执行，不能混为一谈。**

> **未知或失败的 Router/classifier 应优先保留 legacy 能力，而不是为了快把工具静默切掉。**

> **True Streaming 不能以破坏 OpenAI-compatible textual tool-call salvage 为代价。**

> **用户看到的是有价值的行动进度，不是内部 reasoning，也不是泄露出来的 tool-call markup。**

> **工具越少越好，但只裁掉能够证明无关的工具；无法安全证明时保留兼容能力。**

> **FAST_CHAT/KNOWLEDGE 必须“证明可以快”，而不是“没发现风险所以快”。**

> **禁网时 UNKNOWN 工具按不安全处理；普通执行时 UNKNOWN 工具按 legacy capability 保留。**

> **32/50 是 route-selected 收敛目标，150 是当前兼容 hard ceiling；Router OFF / no explicit profile 时 legacy path 不自动套用 32/50。先用软预算优化行为，再用数据决定未来是否降低硬上限。**

> **Router、Tool Projection、structured-tools true streaming 与 Emergency Finalization 都是可关闭增强；A–G + final regression 前 built-in defaults 统一保持 OFF，默认启用必须在独立 rollout run 逐个验证，不得成为无法回退的新核心依赖。**

> **质量由验证质量、能力完整性和最终交付决定，而不是由 Agent 轮数决定。**
