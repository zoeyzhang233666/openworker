# ChemClaw SMTP 发送审批闭环 Implementation Plan（D-099）

> **For agentic workers:** 复用 Email 连接器；勿新建 `coworker/mail/`。

**Goal:** 在 D-094/D-097 草稿与报价之后，提供**人工触发**的邮件发送：走现有审批；无自动外发、无静默 SMTP。

**Architecture（定案）：**
- 复用连接器 [`coworker/connectors/email_tools.py`](../../../../coworker/connectors/email_tools.py) 的 `email_send` + SecretStore `email:default`
- `requires_approval=True` → 现有 ApprovalCard；不新建 SMTP 客户端
- GUI：助手文本含 `ready_for_human_send` 时显示「提交发送审批」，注入意图后由 Agent 调 `email_send`
- 发送相关错误中文化；不买联系人、不绕过审批、客户清单页不加发送按钮

**Status (2026-08-09):** 已实现并收口（D-099）。

## Tasks
- [x] `email_send` 路径中文错误 + `tests/test_email_tools.py`
- [x] 外贸转化龙虾 / `chem-sales-engagement` 发送纪律；测试改用 `email_send`
- [x] Transcript CTA + `requestSendApproval.ts` + i18n
- [x] D-099 / README / 销售规格 / DOMAIN

## 验收
- 无密钥时清晰中文错误；有密钥时审批后才发送；自动发送路径测试必须失败（`needs_user`）
- 门禁未 `ready_for_human_send` 不显示 CTA

## Out of Scope
- CRM、TED、客户清单发送、Gmail OAuth 专属重写、新建 `coworker/mail/`
