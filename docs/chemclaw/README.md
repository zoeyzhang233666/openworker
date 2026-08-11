# ChemClaw 项目控制台

## 当前状态

- 产品设计：书面规格已于 2026-07-29 获得用户批准。
- 实施计划：阶段 1“首条真实纵向链路”已获用户批准。
- 销售增长智能：外贸/内贸/商机/转化设计已于 2026-08-07 获批。**已授权并实现（D-091—D-103、D-105—D-122）**：四龙虾包；PubChem/GLEIF/国内登记；TED；SAM；Comtrade；海关；询盘转报价；清单；SMTP；HubSpot；化工社合集试点+Triage；API 公开查询；SAM/Comtrade 境外可选；VAT/汇率/维基；**化工社只读检索**（D-118）+ **写反应首包**（D-119）+ **公开 SVG 落盘 Tool**（D-120）+ **压缩硬裁提示中性化/二次收紧摘要**（D-121）+ **四销售龙虾专属空态三卡**（D-122）。默认仍为 ChemClaw/`cowork`，销售 Agent 默认禁用。**本机销售环点检（2026-08-09）用户确认通过**。
- **化工多平台内容重构（2026-08-10，D-104 / D-107）**：选用 Plan B；**M1+M2 已落地并收口**：`platform-rewrite-lobster` + 四核心 Skill + **`chem-hook-cta-pack`（按需）**、确定性扫描、合成夹具、**12 条回归语料**、空态三卡；knowledge 会话只读挂载 `skills`；默认仍为 `cowork`，新 Agent 默认禁用；不自动发帖。同日核对工作区假 dirty 已清；定向 pytest **26 passed**。**M3**（词表热升级 / 安装包验收）须点名且确认打安装包。见 [platform-rewrite/README.md](platform-rewrite/README.md)、[HANDOFF_PLATFORM_REWRITE.md](HANDOFF_PLATFORM_REWRITE.md)、[计划](../superpowers/plans/2026-08-10-chemclaw-platform-rewrite-builtin-pack.md)。
- **本机 NSIS 安装包（2026-08-11）**：用户点名打包；已产出未签名 `ChemClaw_0.1.7_x64-setup.exe`（约 48.5 MB）于 `surfaces/gui/src-tauri/target/release/bundle/nsis/`。无 updater 签名密钥，不含自动更新制品。打包前修通 GUI `tsc` 门禁（含 `message_updated`、RightRail 残留进度调用等）。
- **安装包纠偏（2026-08-11，D-123）**：旧包未打入 `skills/bundled`/`personas/builtin`，运行时又读 `%APPDATA%\\coworker`，表现为「带旧聊天、缺新龙虾」。已重打：sidecar 含本 worktree **108** 个 `SKILL.md` + **7** 个 builtin persona；默认状态目录改为 `%APPDATA%\\ChemClaw` / macOS `~/.config/chemclaw`（不迁移旧 coworker 数据）。**请装到空目录，不要覆盖 `D:\\ChemClaw` 旧工程树**；勿把桌面快捷方式指到旧目录里的 exe。
- **macOS DMG（2026-08-11）**：`packaging/build_dmg.sh` 的 APP 名改为读 `tauri.conf.json` `productName`（ChemClaw）；Release workflow 稳定产物名为 `ChemClaw-macos-arm64.dmg` / `ChemClaw-macos-x64.dmg`。须在 **macOS runner**（GitHub Actions `workflow_dispatch` 或标签 `app-v*`）或本机 Mac 构建，Windows 不能交叉编译。已推送 `chemclaw-clean` @ `9b0ac4c` 与标签 `app-v0.1.7-chemclaw-macos`。若 Actions 页仍为 0 runs：到仓库 Settings → Actions → General 允许 Actions 后再 **Re-run** / `workflow_dispatch`。无 Apple 证书时为未签名包：Mac 上右键打开或 `xattr -cr ChemClaw.app`。
- **架构调整（2026-08-03）**：采用方案 A，从 OpenWorker 最新 `main`（含 2026-08-01 Skills PR #391）重建 ChemClaw 层，丢弃自研 `capabilities` 模块。
- 当前阶段：阶段 1，上游 Skill + ChemClaw 品牌/汉化/导航（进行中，待用户界面验收）。
- 当前分支：`chemclaw-clean`（与本机 worktree 目录同名；GitHub 上选此分支即可，无需并入 `main`）
- **唯一开发基线 Worktree**：`D:\OpenWorker\openworker\.worktrees\chemclaw-clean`（后续只在此继续开发）
- 旧 Worktree（只读备份，待确认后删除，本次不删）：`D:\OpenWorker\openworker\.worktrees\chemclaw-design`（分支 `design/chemclaw-foundation` / 标签式备份 `backup/broken-2026-08-03` 已在 `backup` 远程）
- 业务代码（本 Worktree）：
  - ✅ 基于 upstream/main（OpenWorker Skills 官方实现）
  - ✅ ChemClaw 品牌 + 全界面汉化（cherry-pick 自旧分支）
  - ✅ D-006 主导航：对话 / 技能 / 智能体 / 客户清单 / 定时任务 / 连接 / 设置（D-098 增「客户清单」）
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
  - ✅ 设置页 Context compaction 已汉化；默认触发阈值/上限拉到允许最大值（95% / 2,000,000 tokens）
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

1. 用户在 `chemclaw-clean` 打开界面验收：品牌 ChemClaw、默认中文、主导航「智能体」、技能页、Mermaid neo、新建对话 ▾ 中文选择器、空会话主标题「与 xxx 畅谈」随 ▾ 变化、智能体页 Sliders 详情、zip 联装（先重启服务）。
2. 验收满意后删除旧 `chemclaw-design` worktree（`git worktree remove`）；在此之前勿在旧树继续开发。
3. 二期：智能体非内置编辑 / 内置另存为 / 本会话切换+按条 agent_id；对话挂载条；依赖型 Skill 安装器（D-019）。
4. 销售主线含 D-105/D-109 HubSpot、D-106 SAM、D-108/D-110 海关、**D-113—D-120**（公开查询 + VAT/汇率/维基 + **化工社只读/写反应/SVG 落盘**）。**用户侧**补勾 D-108/109/110。**下一刀须点名**：① CRM 字段/任务 CTA → ② 合集 P0 → ③ M3。

## 文档索引

- [完整产品设计](../superpowers/specs/2026-07-29-chemclaw-product-design.md)
- [销售增长智能设计（D-086—D-112）](../superpowers/specs/2026-08-07-chemclaw-sales-growth-intelligence-design.md)
- [外贸拓客内置能力包计划](../superpowers/plans/2026-08-07-chemclaw-export-sales-builtin-pack.md)
- [内贸拓客内置能力包计划](../superpowers/plans/2026-08-07-chemclaw-domestic-sales-builtin-pack.md)
- [商机雷达内置能力包计划](../superpowers/plans/2026-08-07-chemclaw-opportunity-radar-builtin-pack.md)
- [外贸转化内置能力包计划](../superpowers/plans/2026-08-07-chemclaw-export-engagement-builtin-pack.md)
- [PubChem 化学身份 Provider 计划](../superpowers/plans/2026-08-07-chemclaw-pubchem-identity-provider.md)
- [GLEIF 法定主体 Provider 计划](../superpowers/plans/2026-08-09-chemclaw-gleif-legal-entity-provider.md)
- [询盘转报价内置首包计划](../superpowers/plans/2026-08-09-chemclaw-inquiry-to-quote-builtin-pack.md)
- [客户清单工作台计划（D-098）](../superpowers/plans/2026-08-09-chemclaw-lead-list-workbench.md)
- [SMTP 发送审批计划（D-099）](../superpowers/plans/2026-08-09-chemclaw-smtp-send-approval.md)
- [HubSpot CRM 审批写入（D-105）](../superpowers/plans/2026-08-10-chemclaw-hubspot-crm-write-approval.md)
- [HubSpot 创建联系人审批（D-109）](../superpowers/plans/2026-08-10-chemclaw-hubspot-create-contact-approval.md)
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

- 日常开发请使用 **`chemclaw-clean` Worktree**（唯一开发基线；不要再在旧的 `chemclaw-design` 上改代码）。
- Python 下载缓存、开发状态和 pytest 临时目录统一放在 `D:\OpenWorker\.chemclaw-dev`。
- 拉 upstream：`git fetch upstream main`（remote：`https://github.com/andrewyng/openworker`）。
- 完整版本、命令、测试数字、启动顺序和已知缺陷以 [TESTING.md](TESTING.md) 为准。

## 新任务推荐开场

> 继续 ChemClaw 阶段 1（分支与 worktree 均为 `chemclaw-clean`）。请先阅读 AGENTS.md、项目控制台、已批准规格、TESTING.md 和实施计划。Skill 功能以 OpenWorker 上游实现为准；ChemClaw 只做品牌、汉化、导航与 bundled Skill 薄层。一次只执行指定 Task。
