# 销售主线门禁验收记录（2026-08-09）

## 程序侧验收（可自动）

| 检查项 | 结果 |
|--------|------|
| 四龙虾 persona 可发现且默认禁用 | 通过 |
| 默认 Agent 仍为 `cowork` | 通过 |
| `lookup_chemical_identity` / `lookup_legal_entity` / `calculate_quote` 已注册 | 通过 |
| 关键 bundled Skill 目录存在 | 通过 |
| GUI 销售 persona i18n | 7 passed |
| `format_lead_list` 已注册 + `chem-lead-list` | 通过（`tests/test_lead_list.py` 等） |
| 主导航「客户清单」i18n / 无发送按钮 | 接线完成；见 npm 回归 |
| D-099 `email_send` 中文错误 + EXTERNAL 门禁 | `pytest` email/engagement **36 passed** |
| D-099 对话「提交发送审批」CTA | `npm` requestSendApproval + Transcript 等 **47 passed** |

## 程序侧复验（2026-08-09 进度队列）

| 检查项 | 结果 |
|--------|------|
| 四龙虾 persona 可加载 | 通过（export/domestic/opportunity/engagement） |
| `lookup_*` / `calculate_quote` / `format_lead_list` 已注册 | 通过（`build_engine(chat_agent)`） |
| 销售相关改动已小提交 | 含 `404b039` Comtrade 等（未 `git add .`） |
| D-100 国内登记 + 路由 Fixture | `pytest` cn_registry/legal_entity **24 passed** |
| 本机点检前复验（TED 前） | 四龙虾 + 既有 Tool 注册 **通过**（2026-08-09） |
| D-101 `search_tenders` Fixture + 接线 | `pytest` TED **9 passed** |
| D-102 清单进阶 UX | `npm` requestLeadFollowup + LeadsWorkbench + i18n/audit |
| D-103 Comtrade `lookup_trade_flow` | `pytest` comtrade provider + skill wire **11 passed** |
| **点检前总复验（D-091—D-103）** | `pytest tests/test_sales_loop_preflight.py` **2 passed**（2026-08-09） |
| D-105 HubSpot CRM 笔记审批 | `pytest` hubspot portals + skill wire **12 passed**；`npm` requestCrmWriteApproval + Transcript/i18n/audit **49 passed** |
| D-106 SAM.gov `search_sam_opportunities` | `pytest` sam tender provider + skill wire **11 passed**（2026-08-10） |
| D-108 海关 CSV `filter_customs_importers` | `pytest` customs file provider + skill wire **9 passed**（2026-08-10） |
| D-110 海关 XLSX | `pytest` customs file provider（含 xlsx）**8 passed**（2026-08-10） |
| D-109 HubSpot 创建联系人审批 | `pytest` create-contact skill wire **2 passed**；`npm` requestCrmCreateContact + Transcript **32 passed**（相关子集） |

## 用户侧点检（需本机 UI）

### 启动

```powershell
cd D:\OpenWorker\openworker\.worktrees\chemclaw-clean
powershell -File .\scripts\restart-chemclaw-dev.ps1
```

浏览器打开 `http://localhost:1420`。**先 sidecar 后 Vite**（token 会重写）。细节见 [TESTING.md](TESTING.md)。

清单导入示例（D-102）：[`fixtures/smoke-lead-list.json`](fixtures/smoke-lead-list.json)

海关点检样例（D-108 / D-110）：复制到当前对话工作区后使用（勿改仓库内原件也可直接指路径）：

- CSV：`tests/fixtures/customs/sample_shipments.csv`
- XLSX：`tests/fixtures/customs/sample_shipments.xlsx`
- 缺列负例：`tests/fixtures/customs/missing_company.csv`（或 `.xlsx`）

### 操作清单（D-105 / D-106 / D-108 / D-109 / D-110）

> **给非技术用户**：下面按「点哪里、说什么、期望看到什么」写。未连接 HubSpot / 未配 SAM 密钥时，**期望是中文错误提示**，不要硬连真实写入。每做完一项，把上方勾选清单对应行打成 `[x]`，并在「点检结果记录」表加一行。

#### A. 外贸转化 · CRM 笔记审批（D-105）

1. 左侧「智能体」→ 找到「外贸转化龙虾」→ **启用**（默认是关的）。
2. 新建对话，▾ 选中「外贸转化龙虾」。
3. 在输入框粘贴并发送（制造门禁文案，不必真有客户）：

```text
请只输出一段简短中文跟进结论，并在文末单独一行写：recommended_action: ready_for_crm_write
不要调用任何工具。
```

4. 回答结束后应出现按钮 **「提交 CRM 写入审批」**（无此按钮 = 失败）。
5. 点该按钮 → 应注入一段「请提交 CRM 写入审批…」用户消息，Agent 尝试 `hubspot_log_note`。
6. **未连接 HubSpot**：应出现**中文**说明并引导去「连接」配门户（不要英文堆栈）。
7. 若已连接：应出**审批卡**；点拒绝 → 不得宣称已写入 CRM。
8. 打开「客户清单」页：确认**没有**「发送邮件」/ CRM 写入按钮。

#### B. 外贸转化 · 创建联系人审批（D-109）

1. 仍在外贸转化龙虾对话（或新开一会话）。
2. 发送：

```text
请只输出简短中文，并在文末写：recommended_action: ready_for_crm_create_contact
假设已核验邮箱 buyer@example.com。不要调用工具。
```

3. 应出现 **「提交创建联系人审批」**（仅有 `ready_for_crm_write` 时不应单独冒出创建按钮）。
4. 点击后注入创建意图；未连接 → 中文错误；已连接 → 审批卡，拒绝则不创建。
5. 再确认客户清单页仍无 CRM 按钮。

#### C. 商机雷达 · SAM（D-106，可选）

1. 「智能体」启用「商机雷达龙虾」→ 新建对话选它。
2. 发送：

```text
请调用 search_sam_opportunities，关键词用 sodium benzoate，limit 3。
若未配置密钥，用中文说明即可，不要编造 noticeId。
```

3. **未配 `sam:default`**：中文提示缺密钥/未配置。
4. **已配密钥**：结果 id 形如 `sam:<noticeId>`，带来源 URL；不得瞎编编号。

#### D. 外贸拓客 · 海关 CSV（D-108）

1. 「智能体」启用「外贸拓客龙虾」→ 新建对话选它。
2. 把 `tests/fixtures/customs/sample_shipments.csv` 放进**本会话工作区**（或告诉 Agent 绝对路径）。
3. 发送：

```text
请对工作区里的 sample_shipments.csv 调用 filter_customs_importers，limit 10。
说明哪些像货代、哪些更像进口商；不要把候选直接标成 Qualified。
```

4. 期望：能筛出货代噪声；结果含「收货方≠终端买家」类警告；不把候选直接当 Qualified Lead。
5. 再试缺列文件 `missing_company.csv`：应有**中文**缺列/不可用说明。

#### E. 外贸拓客 · 海关 XLSX（D-110）

1. 同上龙虾，对 `sample_shipments.xlsx` 再跑一遍 `filter_customs_importers`。
2. 期望与 CSV 同类（评分行 + 非终端买家警告）。
3. 若只有旧版 `.xls`：应提示另存为 xlsx/csv（中文）。

### 勾选清单

- [x] 智能体页可见：外贸拓客 / 内贸拓客 / 商机雷达 / 外贸转化龙虾（默认关，可启用）
- [x] 默认对话仍为 ChemClaw / `cowork`（未擅自换成销售龙虾）
- [x] 任意 Agent 可调用 `lookup_chemical_identity` / `lookup_legal_entity`（只读）
- [x] 启用转化龙虾后可调用 `calculate_quote`（询盘报价草稿）
- [x] 主导航有「客户清单」；导入 `smoke-lead-list.json` 后见断点条（`smoke-run-001` / ranking / 5）
- [x] 展开行可见匹配原因 / 关键证据 / 下一步 / 排除原因
- [x] 「继续补查」「调整 ICP 并重评」切回会话并注入意图
- [x] 可标记状态、备注、导出 CSV；**无**「发送邮件」/ CRM 按钮
- [x] （可选 D-099）`ready_for_human_send` →「提交发送审批」→ 审批卡；拒绝不外发；Email 未连接时中文错误
- [x] （可选 D-101）商机雷达可调用 `search_tenders`；结果带来源 URL，不伪造 TED 编号
- [x] （可选 D-103）未配置 `comtrade:default` 时 `lookup_trade_flow` 中文提示；有密钥时返回汇总 + 非买家警告
- [ ] （D-105）转化龙虾文案含 `ready_for_crm_write` 时有「提交 CRM 写入审批」；点后注入意图；`hubspot_log_note` 出现审批卡；拒绝不写入；未连接中文错误；清单页仍无 CRM 按钮
- [ ] （可选 D-106）未配置 `sam:default` 时 `search_sam_opportunities` 中文提示；有密钥时返回 `sam:<noticeId>` + 来源 URL，不伪造 noticeId
- [ ] （可选 D-108）工作区放入海关 CSV 后 `filter_customs_importers` 可筛货代；结果含非终端买家警告；缺列/缺文件中文错误；不把候选直接当 Qualified
- [ ] （可选 D-110）工作区放入海关 XLSX 后同样可筛货代；与 CSV 同类结果；`.xls` 中文提示另存
- [ ] （可选 D-109）文案含 `ready_for_crm_create_contact` 时有「提交创建联系人审批」；点后注入意图；`hubspot_create_contact` 出现审批卡；拒绝不创建；仅笔记门禁时不出现创建 CTA（或两门禁可并存）；清单页仍无 CRM 按钮

### 点检结果记录

| 日期 | 执行人 | 结论 | 备注 |
|------|--------|------|------|
| 2026-08-09 | 程序侧 | 总复验通过；dev 环境已重启 | `pytest tests/test_sales_loop_preflight.py` 2 passed；`/v1/health` ok |
| 2026-08-09 | 用户 | **点检通过** | 用户口头确认「点检通过」；无失败项回报；销售环 UI 门禁关闭 |
| 2026-08-10 | 程序侧 | D-105 接线验收通过 | HubSpot 中文错误 + CTA + Skill 接线；用户侧 D-105 勾选待填 |
| 2026-08-10 | 程序侧 | D-106 接线验收通过 | SAM Fixture + 商机雷达接线 11 passed；用户侧 D-106 勾选待填 |
| 2026-08-10 | 程序侧 | D-108 接线验收通过 | 海关 CSV Fixture + 外贸拓客接线 9 passed；用户侧 D-108 勾选待填 |
| 2026-08-10 | 程序侧 | D-109 接线验收通过 | 创建联系人 CTA + Skill 接线；用户侧 D-109 勾选待填 |
| 2026-08-10 | 程序侧 | D-110 接线验收通过 | 海关 XLSX Fixture + provider 8 passed；用户侧 D-110 勾选待填 |
| 2026-08-10 | 程序侧 | D-111 合集单包验收通过 | `uncertainty-and-units` vendor + wire：`tests/test_uncertainty_and_units_skill.py` 4 passed |
| 2026-08-10 | 程序侧 | D-112 合集 Triage 落盘 | `HUAGONGSHE_SKILL_TRIAGE.md` + JSON；P0/P1 待用户确认 |
| 2026-08-10 | 程序侧 | **点检操作清单 A–E 落盘**；工具复验 | `pytest` preflight+customs+sam **19 passed**；`npm` CRM CTA **4 passed**；用户侧勾选仍待按操作清单点完 |

**当前状态：** 销售主线本机点检（D-091—D-103）已关闭。D-105—D-112 程序侧通过（含合集单包与 Triage 表）。**2026-08-10**：已补「操作清单」A–E；程序侧复验含 `search_sam_opportunities` / `filter_customs_importers`（见上表）。**用户侧 D-105/106/108/109/110 勾选仍待你按操作清单点完后打钩。**

点检通过后默认下一刀顺序（须再点名才实现）：**CRM 字段/任务 CTA** → **海关外部 API（确有在线数据需求时）** → **合集 P0 `scientific-critical-thinking`** → **内容重构 M3**。不顺手开化工社批量。
