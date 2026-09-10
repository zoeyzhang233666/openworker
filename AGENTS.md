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

**D-166 化工现货/期货路由纠偏已实现**：明确现货只用 chem-data-hub `get_price_trend`，明确国内期货才用 `lookup_cn_futures_*`，WTI/Brent 用 Yahoo；裸甲醇/原油先 `ask_user`，执行守卫在权限审批前拦截未澄清/错误口径，durable resume 不丢原始市场意图。**D-181**：化工三口径默认放行 Web 有序降级（先结构化、空结果再联网补价并标来源）；仍禁交叉替代与 Yahoo 冒充国内期现。**D-177**：显式期现对照（现货+期货 / 期现基差 / 期货+套利）同一轮放行现货 MCP 与国内期货，禁止交叉替代。**D-178**：live「正在思考」挂载即强制展开+贴底跟滚，可与「正在运行 x 个步骤」同时展开。**D-183**：思考结束收起「思考过程」连续可见；settled thinking-only 间隙保留规划等待；TurnGroup 上方可展开 reasoning。**D-184**：研究套利句强制 DEEP_RESEARCH 窄父面+委派；LLM `Request timed out` 可重试并中文分层报错。**D-185**：对话与 MD 产物预览共用 KaTeX（`$…$`/`$$…$$`）。**D-186**：同槽位 live→hold→settled 交接，避免早期 assistant_delta / streamGate hold 造成真空白。**D-187**：用户手动 stop=immediate；智能体/系统 stop=wrap_up 先收尾；流式 read=300s；超时+已有工具 EF salvage。**D-179**：研究子智能体继承父市场口径；Upstream invalid 压缩重试+EF salvage；OHLC sidecar `series_name`；research+`grep`；Windows shell UTF-8；cowork 优先 read/grep。**D-180**：第一方 system/tool 提示默认简体中文。**D-188**：企微智能机器人 WebSocket channel。**D-195**：企微同 stream 过程刷新 + 终态短总结/COS 精装 HTML（仅 wecom；Chart.js 缩放全屏；HTML inline）。**D-195b**：精装页 GFM 表格 + Mermaid CDN + 版式升级。**D-195c**：企微不发 MD（转 HTML）；纯问答只回文字。**D-189**：MCP 连接诊断（`misconfigured`+`last_error`；引擎可补挂 MCP；ExceptionGroup 展开叶子异常）。**D-190**：内置 chem MCP 已退役；启动 `retire_builtin_mcp()` 清理旧种子；用户须手动添加 MCP。**D-192**：Channel `deliver_to_session` 后台轮次与 GUI WS 一致先 `prepare_mcp_tools`（企微/Slack 私信与订阅、self-wake）。**D-191**：启动「无模型」假状态修复（`model_ready`=任一可运行模型 + 默认自动纠偏；Vite token 路径 ChemClaw）。

**D-196/D-197（2026-09-01）修订当前门禁**：企微/个人微信/飞书/钉钉的 `ask_user` 精确回到发起会话，四平台托管会话支持 `/new`/`/reset`，个人微信扫码后授权可热刷新。D-197 **明确取代上文 D-166 的执行守卫描述**：市场意图/投影/prompt 仍引导正确来源，但 Engine 不再产生 `market-scope denied`，行情 Scenario allowlist 也不作第二层 MCP 硬拒绝。定向回归 166 passed, 1 skipped。

**D-198（2026-09-01）当前门禁**：桌面打开会话不能覆盖 Channel 的 `ask_user` 镜像；企微/个人微信必须收到与桌面同源的完整选项，发送失败检查 `SendResult` 并有限重试。个人微信以 `incremental_messages` 做节流分段流式；“开新的对话”“新的对话”“新建对话”等严格整句与 `/new` 等价，长句不误触。组合回归 170 passed, 1 skipped。

**D-199（2026-09-01）当前门禁**：企微/个人微信/飞书/钉钉/Telegram/Slack 等 Channel 聊天气泡不得出现 ` ```chart` / Mermaid 原始 JSON；流式只发可读正文，终态与 `send_message` 经 `rich_output` cook 为精装 HTML 并以 COS 链接或 `.html` 附件交付，失败时只发清理文字与中文降级说明。桌面 assistant message 不改写。D-199 定向 + D-195/D-196/D-198/连接器组合回归：**171 passed, 1 skipped**。**须重启 sidecar** 后企微复验含 chart 回答。

**D-199b（2026-09-01）当前门禁**：Channel 含 chart 时 best-effort 发送 PNG 预览图 + **单一** HTML 链接（预览与链接同源）；`report.md` 优先于正文 inline chart 作为 cook 来源；四平台统一 `compose_channel_rich_reply`。精装 HTML 移动端默认 zoom 最新 24 根。D-199b 定向 + 组合回归：**174 passed, 1 skipped**。**须重启 sidecar** 后企微复验预览图与链接。

**D-199c（2026-09-01）当前门禁**：精装 HTML 不得裸显 GFM pipe 表格（`| 列 |`）；`normalize_gfm_tables` 隔离表格块后保留 nl2br。定向 `test_report_html_cook` 含助手标题直下表格 + chart 混排用例。**须重启 sidecar** 后重新生成 COS 链接验收。

**D-200（2026-09-01）当前门禁**：个人微信在工具轮次最终回答前发送「正在调用 {tool}…」过程气泡（≥2s 节流）；正文分段门槛 80；错误中文气泡；仍为 `incremental_messages`。D-200 定向 + D-196/D-198/D-199/企微流/多平台组合回归：**94 passed, 1 skipped**。**须重启 sidecar** 后个人微信复验过程提示。

**D-204（2026-09-02）当前门禁**：无期现歧义的化工查价/走势（如柠檬酸）默认投影 chem-data-hub `get_price_trend`，不再因未写「现货」落到 non_market 只剩网页；甲醇/原油等仍 ask_user。Channel 查价禁止「请贴数据」问卷；今天/现价小 limit 快答。定向 market_intent + channel_fast + projection/scenario/planner/guidance：**78 passed**。**须重启 sidecar**。

**D-202（2026-09-02）当前门禁**：Channel（企微/个人微信/飞书/钉钉/Telegram/Slack）用户轮窄工具面——禁 shell/load_skill/subagent；周报/日报/月报 Channel 单轮 `REPORT_CHANNEL` 写 `report.md` + 终态 HTML/PNG，不启 D-201 后台子任务、不向 IM 刷进度气泡；chem-data-hub 价格回包引擎预聚合；液化气/LPG→液化石油气别名映射。桌面 GUI 仍可选 D-201 后台补全。定向 `test_channel_fast_surface_d202` + planner/market_series/wecom_stream：**27 passed**。**须重启 sidecar** 后企微/个微复验液化气周报。

**D-165 按需上下文已实现并 live PASS**：真实会话每轮 `TurnPlan`；FAST/KNOWLEDGE 的 tools/skills=0；prompt policy v1；reasoning 有则实时展示；强意图用能力包，旧会话与未知 MCP/connector 保守 legacy；`prompt_projection_enabled` 候选 ON。ApiHub Flash GUI WS N=5 + 长答：问候 85 tokens、P50 2.88s/P95 6.88s、direct fallback=0；长答 745 deltas；上游 reasoning=0。

产品设计与阶段 1 实施计划已获批准。销售主线首包（D-091—D-122）与内容重构 M1+M2+M3（D-104/D-107/**D-128**）已落地。**D-127 HubSpot 字段更新/任务创建 CTA 已落地**。**D-131 默认智能体自称 ChemClaw**（system prompt/title/UI，id 仍 `cowork`）。当前：公开查询必显销售 Provider；VAT/汇率/维基已接线；**化工社只读 + 写反应 + SVG 落盘**（D-118/D-119/D-120）；**压缩硬裁提示中性化**（D-121）；**压缩默认 70%/100k**（D-129）；**四销售龙虾专属空态三卡**（D-122）。**性能 Router v5：HARD STOP A–G + §65 46–55 已完成；Step 56–59 已授权落地**（routing + projection + structured-tools true streaming known-safe + Emergency Finalization built-in = 候选 ON；unknown/custom 仍 buffered；FAST/KNOWLEDGE EF 强制 OFF；NEW FAIL = none）。**四开关独立 rollout 已全部完成**。**D-133 Inline Chart 第一轮已落地**（```chart` + Chart.js；`chart-image` 仅静态导出；解析兼容 `x.labels`）。**D-134 行情默认附趋势图已落地**（有时间序列则表+要点+```chart`）。**D-135 Yahoo OHLC + 蜡烛图已落地**（`lookup_yahoo_ohlc`；`candlestick`；version 缺省=1；多标的分图）。**D-136 Yahoo K 线短引用已落地**（`from_tool`+`symbol`；工具 `chart_spec`；GUI 回查；手抄长度截齐兜底）。**D-137 K 线国内红涨绿跌已落地**。**D-138 K 线阶段标注已落地**（`stages` 色带；高低价自动；OHLC 左上+驱动右上；十字线；无箭头；short-ref 可附 stages）。**D-139 手抄 OHLC `[o,h,l,c]` 数组兼容已落地**。**D-140 K 线默认最新窗+滚轮缩放/拖动已落地**（90根；X zoom/pan；可见区Y自适应）。**D-141 现货十字线+融文铬层已落地**（line/area/bar 左栏+十字线+固定；默认最新；无图源切换/灰框；全屏图标+芯片提示）。**D-142 全屏不透+现货 stages/focusLabel 已落地**（近不透明 lightbox；挂载默认 pin；短栏居中；guidance 拉长历史）。**D-143 操作芯片悬停才显**（顶部固定占位淡入，不挡标题、图不位移；全屏常显）。**D-144 左栏详情始终左中**。**D-145 去掉 Wind 金融 Skill 路径**（三份金融 Skill + chain-lobster；Yahoo/Web；启动窄刷新）。**D-146 左栏价格不截断**（KV 上下排 + 加宽轨）。**D-147 左栏空白收紧**（fit-content；OHLC 左右排 / 系列上下排；开收随当根涨跌）。**D-148 国内行情层地基**（`coworker/cn_market/` contracts/cache/symbol/calendar/fake；不加 AKShare）。**D-149 A 股公开 adapter**（新浪报价/K线/财报 + 东财龙虎榜/北向历史 + 上证两融）。**D-150 国内期货公开 adapter**（新浪 L1/日线/分钟 + 本地持仓量主力 + 理论保证金；`MA0` 不冒充本地连续）。**D-151 期权公开 adapter**（SSE ETF 新浪纵切 + CFFEX 盘口；Greeks 仅 upstream；exchange_stats unavailable；Core-35 未验证项不扩源）。**D-152 国内行情 Agent 接线**（11 个 `lookup_cn_*` 已挂默认对话；A股/国内期货/期权不走 Yahoo；GUI short-ref 认 CN OHLC；公开查询三张国内行情卡）。**D-153 现货图缩放/拖动对齐 K 线**（line/area 最新窗+滚轮/拖动；密点隐藏圆点；最低/最右价不裁切）。**D-154 极值标签分侧+去重**（高上低下；顶/底留白；近邻同 kind 丢阶段极值）。**D-155 小图不标极值、全屏才标**（可见窗全局高+低；zoom/pan 刷新）。**D-156 阶段方向重算+驱动只写原因**（GUI 按涨跌幅覆盖 tone；reason 去价格）。**D-157 短引用中文品种匹配**（payload `name`/`aliases`；GUI 精确对上橡胶/天然橡胶）。**D-158 阶段色带互斥**（last-wins 裁切；半透明不叠色）。**D-159 短引用直播 sidecar + 全会话回查**（TOOL_FINISHED 带 chart_spec；追问可对上更早的 GC=F）。**D-160 未指定周期默认日线**（股价/期货价未点名周期走日线 OHLC，不默认分钟/周/月）。**D-161 ApiHub CN 带工具真流式单独验证**：精确对表已接；短答 live 无 PASS。**D-163 长答再验**（不放宽 200ms）：`deepseek-v4-pro`/`glm-5.2` PASS 已进对表。**D-164 Flash 单独重跑 PASS**，默认 `deepseek-v4-flash` 带工具可真流式；kimi-k3 未定价；未验 Intl。**D-162 产物 Markdown 短引用回查出图**（报告 md 与对话共用本会话 OHLC 回查）。下一刀须新独立授权（Run 4X Tick/L2 / Fast Router / 放宽 D-161 200ms 门槛 / 其它产品门禁）。按 GATE 点检 D-108+。以 `docs/chemclaw/README.md` 为准。
