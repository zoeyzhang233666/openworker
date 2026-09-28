# 基础联网与会话模型选择实施记录

依据：[用户要求与规格](../specs/2026-09-28-chemclaw-web-model-continuity-design.md)。在 2026-09-27 加固计划中优先处理本次反馈，其他未完成项保留。

- [x] 搜索/网页读取固定可见；清理通用提示的数据源禁令；默认和禁联网回归。
- [ ] 分离全局默认与会话模型；首次绑定持久化；延迟响应/连续提问/重连回归。
- [ ] 更新状态和问题台账，分别记录离线证据与实际服务未验证部分，小提交。

不合并 main、不正式构建安装、不发送真实账号消息。

## 联网修复证据

修复前新回归 4 failed / 3 passed：cowork/chat/code 三种助手第一轮均无联网 schema，通用提示也缺少基础联网合同。修复后同组通过，实际引擎调用模拟搜索成功且没有先执行 load_skill；约 400 个 MCP 仍按需加载。用户明确禁联网、禁搜索、禁工具的三种限制均有效。

`test_web_availability / test_web_search / test_tool_discovery / test_tool_policy / test_runtime_acceptance / test_subagent_readonly / test_channel_fast_surface_d202 / test_cn_market_agent / test_model_selection` 加 `test_server::test_ws_first_message_binds_then_midsession_switch_persists_notice` 合并运行 **47 passed**。其中模型代码是同一专项第二个独立提交，见下续录。原 CN 提示测试更新为中文现行合同，保留国内行情不能被异市场报价冒充和默认日线的有效断言。

测试均使用模拟 Provider 和搜索结果，未调用付费模型、未访问真实搜索服务。中间一次批量命令引用不存在的 `test_channel_runtime_parity.py`，已纠正为真实的 `test_channel_fast_surface_d202.py` 并包含于最终 47 项验证；不是产品失败，也未计为通过。
