# 基础联网与会话模型选择实施记录

依据：[用户要求与规格](../specs/2026-09-28-chemclaw-web-model-continuity-design.md)。在 2026-09-27 加固计划中优先处理本次反馈，其他未完成项保留。

- [x] 搜索/网页读取固定可见；清理通用提示的数据源禁令；默认和禁联网回归。
- [x] 分离全局默认与会话模型；首次绑定持久化；延迟响应/连续提问/重连回归。
- [x] 更新状态和问题台账，分别记录离线证据与实际服务未验证部分，小提交。

不合并 main、不正式构建安装、不发送真实账号消息。

## 联网修复证据

修复前新回归 4 failed / 3 passed：cowork/chat/code 三种助手第一轮均无联网 schema，通用提示也缺少基础联网合同。修复后同组通过，实际引擎调用模拟搜索成功且没有先执行 load_skill；约 400 个 MCP 仍按需加载。用户明确禁联网、禁搜索、禁工具的三种限制均有效。

`test_web_availability / test_web_search / test_tool_discovery / test_tool_policy / test_runtime_acceptance / test_subagent_readonly / test_channel_fast_surface_d202 / test_cn_market_agent / test_model_selection` 加 `test_server::test_ws_first_message_binds_then_midsession_switch_persists_notice` 合并运行 **47 passed**。其中模型代码是同一专项第二个独立提交，见下续录。原 CN 提示测试更新为中文现行合同，保留国内行情不能被异市场报价冒充和默认日线的有效断言。

测试均使用模拟 Provider 和搜索结果，未调用付费模型、未访问真实搜索服务。中间一次批量命令引用不存在的 `test_channel_runtime_parity.py`，已纠正为真实的 `test_channel_fast_surface_d202.py` 并包含于最终 47 项验证；不是产品失败，也未计为通过。

## 模型保持证据

`useSessionModel` 分离全局默认和按 session id 保存的模型；用户待确认选择优先于旧连接 ready/旧模型确认。收到重连 ready 时重提尚未确认的选择，确认后允许后续服务端模型变化。App 的健康/设置回包只更新默认值，不把既有对话换回默认。

后端 `_apply_model` 不再把“没有切换提示”误当作“没有变化”：空对话的首次选择立即保存，发 `model_selected` 确认且不添加聊天标记；有历史时沿用 `model_changed`。旧客户端可忽略新增事件，旧会话格式不变。

新增后台 2 项：空对话选择后重建 SessionManager 仍保持模型；连续提问、读取设置、WebSocket 重连仍用所选模型。既有服务端模型切换用例保留验证，只让聊天提示断言排除新增的内部 checkpoint。共同包含于上述 **47 passed**。

GUI `useSessionModel/sessionResume/api.auth` **12 passed**：晚到默认设置不会覆盖已选模型，两条实际 Session.userMessage 都携带所选模型；不同对话独立，新对话采用默认；旧 ready/确认不回滚新选择。`npx tsc --noEmit` 通过。另 `channel_fast_surface/model_selection/subagent_runtime` **18 passed**（与主组合有重叠，不相加）。

尚未验证：实际安装版界面、用户网络下 DuckDuckGo/Tavily/Brave 的可用性、真实模型端点切换。源码修复不会自动改变运行中的旧程序。更大范围加固与全仓失败清单未完成，仍按 2026-09-27 主计划推进。
