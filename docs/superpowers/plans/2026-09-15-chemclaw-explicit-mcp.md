# D-206 实施计划

规格：[显式 MCP 请求与慢查询诊断](../specs/2026-09-15-chemclaw-explicit-mcp-design.md)。用户已授权实现。

- [x] 统一 MCP 文本识别，保护桌面显式 MCP 工具面及 Channel 限制；预览对齐实际工具集合。
- [x] 排除多事件新闻中的泛价格波动误判；补充 MCP 能力与健康诊断提示。
- [x] 慢查询有界等待、取消未完成请求及中文分类错误。
- [x] 运行定向回归并更新 README、DECISIONS 和本计划实际结果。

## 实际验证

- D-206 + turn_planner / tool_projection / request_router / market_intent / channel_fast：**140 passed**，含真实 build_engine 两轮请求的 MCP schema 与中文提示断言。
- test_mcp：**10 passed**。
- mcp_connectors / builtin_mcp / scenario_resolver / scenario_registry / permissions_risk / tools_permissions：**68 passed**。首轮沙箱因隔离夹具 `secrets.json.tmp` 写入 PermissionError 失败；授权测试进程后通过。仅 pytest 缓存目录写入警告，不影响断言。
- prompt_projection / deliver_mcp：**14 passed, 1 deselected**。排除既有 `gui_websocket_market_matrix`，该用例含真实外网行情；最初未排除的组合运行已中止，不计入通过数。
- 合计 **232 passed, 1 deselected**。未连接真实 MCP 重放慢查询，不保证服务端查询耗时；未重启或替换安装版。
- 修改的 Python 文件 `compileall` 与 `git diff --check` 通过。

不合并、不正式打包、不管理员安装；源码验收后运行中安装版仍需另行更新。
