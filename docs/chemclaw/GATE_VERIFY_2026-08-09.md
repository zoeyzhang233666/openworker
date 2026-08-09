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

## 用户侧验收（需本机 UI）

重启 sidecar 后请确认：

1. 智能体页可见：外贸拓客/内贸拓客/商机雷达/外贸转化龙虾（默认关，可启用）
2. 启用转化龙虾后对话可调用 `calculate_quote`（询盘报价）
3. 任意 Agent 可调用化学身份/法定主体 Tool（只读）
4. 主导航有「客户清单」：可导入 LeadList JSON、导出 CSV、标记状态；**无**发送/CRM 按钮
5. （D-099）转化龙虾草稿出现 `ready_for_human_send` 后对话有「提交发送审批」；点后出现 `email_send` 审批卡；拒绝则不外发；Email 未连接时中文错误
6. （D-101 后）商机雷达可调用 `search_tenders`；结果须带来源 URL，不得伪造 TED 编号

## 程序侧复验（2026-08-09 进度队列）

| 检查项 | 结果 |
|--------|------|
| 四龙虾 persona 可加载 | 通过（export/domestic/opportunity/engagement） |
| `lookup_*` / `calculate_quote` / `format_lead_list` 已注册 | 通过（`build_engine(chat_agent)`） |
| 销售相关改动已小提交 | `1f52d31`（未 `git add .`） |
| D-100 国内登记 + 路由 Fixture | `pytest` cn_registry/legal_entity **24 passed** |
| 本机点检前复验（TED 前） | 四龙虾 + 既有 Tool 注册 **通过**（2026-08-09） |
| D-101 `search_tenders` Fixture + 接线 | `pytest` TED **9 passed** |
| D-102 清单进阶 UX | `npm` requestLeadFollowup + LeadsWorkbench + i18n/audit |

未在本机启动 GUI 点击；以上为接线验收，不替代人工点检。请重启 sidecar 后按「用户侧验收」点检。
