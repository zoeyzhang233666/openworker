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

产品设计与阶段 1 实施计划已获批准。销售主线首包（D-091—D-122）与内容重构 M1+M2+M3（D-104/D-107/**D-128**）已落地。**D-127 HubSpot 字段更新/任务创建 CTA 已落地**。**D-131 默认智能体自称 ChemClaw**（system prompt/title/UI，id 仍 `cowork`）。当前：公开查询必显销售 Provider；VAT/汇率/维基已接线；**化工社只读 + 写反应 + SVG 落盘**（D-118/D-119/D-120）；**压缩硬裁提示中性化**（D-121）；**压缩默认 70%/100k**（D-129）；**四销售龙虾专属空态三卡**（D-122）。**性能 Router v5：HARD STOP A–G + §65 46–55 已完成；Step 56–59 已授权落地**（routing + projection + structured-tools true streaming known-safe + Emergency Finalization built-in = 候选 ON；unknown/custom 仍 buffered；FAST/KNOWLEDGE EF 强制 OFF；NEW FAIL = none）。**四开关独立 rollout 已全部完成**。**D-133 Inline Chart 第一轮已落地**（```chart` + Chart.js；`chart-image` 仅静态导出；解析兼容 `x.labels`）。**D-134 行情默认附趋势图已落地**（有时间序列则表+要点+```chart`）。**D-135 Yahoo OHLC + 蜡烛图已落地**（`lookup_yahoo_ohlc`；`candlestick`；version 缺省=1；多标的分图）。**D-136 Yahoo K 线短引用已落地**（`from_tool`+`symbol`；工具 `chart_spec`；GUI 回查；手抄长度截齐兜底）。**D-137 K 线国内红涨绿跌已落地**。**D-138 K 线阶段标注已落地**（`stages` 色带；高低价自动；OHLC 左上+驱动右上；十字线；无箭头；short-ref 可附 stages）。**D-139 手抄 OHLC `[o,h,l,c]` 数组兼容已落地**。**D-140 K 线默认最新窗+滚轮缩放/拖动已落地**（90根；X zoom/pan；可见区Y自适应）。**D-141 现货十字线+融文铬层已落地**（line/area/bar 左栏+十字线+固定；默认最新；无图源切换/灰框；全屏图标+芯片提示）。**D-142 全屏不透+现货 stages/focusLabel 已落地**（近不透明 lightbox；挂载默认 pin；短栏居中；guidance 拉长历史）。**D-143 操作芯片悬停才显**（顶部固定占位淡入，不挡标题、图不位移；全屏常显）。**D-144 左栏详情始终左中**。**D-145 去掉 Wind 金融 Skill 路径**（三份金融 Skill + chain-lobster；Yahoo/Web；启动窄刷新）。**D-146 左栏价格不截断**（KV 上下排 + 加宽轨）。**D-147 左栏空白收紧**（fit-content；OHLC 左右排 / 系列上下排；开收随当根涨跌）。**D-148 国内行情层地基**（`coworker/cn_market/` contracts/cache/symbol/calendar/fake；不加 AKShare）。**D-149 A 股公开 adapter**（新浪报价/K线/财报 + 东财龙虎榜/北向历史 + 上证两融）。**D-150 国内期货公开 adapter**（新浪 L1/日线/分钟 + 本地持仓量主力 + 理论保证金；`MA0` 不冒充本地连续）。**D-151 期权公开 adapter**（SSE ETF 新浪纵切 + CFFEX 盘口；Greeks 仅 upstream；exchange_stats unavailable；Core-35 未验证项不扩源）。**D-152 国内行情 Agent 接线**（11 个 `lookup_cn_*` 已挂默认对话；A股/国内期货/期权不走 Yahoo；GUI short-ref 认 CN OHLC；公开查询三张国内行情卡）。**D-153 现货图缩放/拖动对齐 K 线**（line/area 最新窗+滚轮/拖动；密点隐藏圆点；最低/最右价不裁切）。**D-154 极值标签分侧+去重**（高上低下；顶/底留白；近邻同 kind 丢阶段极值）。**D-155 小图不标极值、全屏才标**（可见窗全局高+低；zoom/pan 刷新）。**D-156 阶段方向重算+驱动只写原因**（GUI 按涨跌幅覆盖 tone；reason 去价格）。**D-157 短引用中文品种匹配**（payload `name`/`aliases`；GUI 精确对上橡胶/天然橡胶）。**D-158 阶段色带互斥**（last-wins 裁切；半透明不叠色）。**D-159 短引用直播 sidecar + 全会话回查**（TOOL_FINISHED 带 chart_spec；追问可对上更早的 GC=F）。**D-160 未指定周期默认日线**（股价/期货价未点名周期走日线 OHLC，不默认分钟/周/月）。下一刀须新独立授权（Run 4X Tick/L2 / Fast Router / 其它产品门禁）。按 GATE 点检 D-108+。以 `docs/chemclaw/README.md` 为准。
