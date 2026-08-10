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

## 用户侧点检（需本机 UI）

### 启动

```powershell
cd D:\OpenWorker\openworker\.worktrees\chemclaw-clean
powershell -File .\scripts\restart-chemclaw-dev.ps1
```

浏览器打开 `http://localhost:1420`。**先 sidecar 后 Vite**（token 会重写）。细节见 [TESTING.md](TESTING.md)。

清单导入示例（D-102）：[`fixtures/smoke-lead-list.json`](fixtures/smoke-lead-list.json)

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

### 点检结果记录

| 日期 | 执行人 | 结论 | 备注 |
|------|--------|------|------|
| 2026-08-09 | 程序侧 | 总复验通过；dev 环境已重启 | `pytest tests/test_sales_loop_preflight.py` 2 passed；`/v1/health` ok |
| 2026-08-09 | 用户 | **点检通过** | 用户口头确认「点检通过」；无失败项回报；销售环 UI 门禁关闭 |
| 2026-08-10 | 程序侧 | D-105 接线验收通过 | HubSpot 中文错误 + CTA + Skill 接线；用户侧 D-105 勾选待填 |

**当前状态：** 销售主线本机点检（D-091—D-103）已关闭。D-105 程序侧通过，用户侧 HubSpot CTA 勾选待填。下一刀须点名（SAM、内容重构 M2、海关等）；不顺手开化工社批量。
