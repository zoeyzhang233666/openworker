# ChemClaw 移除用户侧“活动/执行诊断”页面（D-170）

**状态：实施完成**

## 用户决定

“活动/执行诊断”属于开发排障界面，普通用户难以理解且没有直接业务价值。产品界面不再展示该页面或入口。

## 实施边界

1. 删除左下角账号菜单中的“活动”入口。
2. 删除 App 的 `audit` surface、`AuditView` 页面和执行诊断前端测试。
3. 保留 D-169 的 Scenario/Capability、Tool allowlist guard、ToolOutcome、TurnTrace、REST/WS 与 Preview 后端能力；这些能力继续在聊天执行链路内生效。
4. 不恢复 D-168 已退役的客户清单入口，不改聊天、连接、权限、审批或定时任务界面。

## 验收

- 账号菜单不再出现“活动”。
- 前端不存在可导航到的 Activity/Audit surface。
- TypeScript/Vite build 和 Sidebar/i18n 定向测试通过。
- D-169 Python 聚焦测试继续通过。

## 实施结果

- 用户可见入口、页面和前端执行诊断测试已删除。
- Sidebar/i18n/localization audit：30 passed。
- D-169 Python 聚焦：170 passed。
- TypeScript/Vite production build：通过。
- 本地 `http://localhost:1420` 刷新实查，账号菜单中不再出现“活动”。
