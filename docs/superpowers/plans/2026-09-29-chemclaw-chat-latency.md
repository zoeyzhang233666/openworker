# 对话速度优化实施记录

规格：[通用提示与渐进展示](../specs/2026-09-29-chemclaw-chat-latency-design.md)。用户已授权源码修复及开发后端重启；不构建安装版，不新增真实模型调用。

- [x] 确认 MCP 隔离版后端启动：2026-09-29 健康 ok，源码 0129c2c，208 个会话仍可列出。
- [x] 静态拆分：仓库当前 111 个 bundled Skill 元数据 14,785 字符；图表详细说明 2,811 字符。与上一轮真实输入 10,420 tokens 不混为同一计量。
- [x] 有界技能发现与图表协议按需读取；离线前后请求对照。
- [x] 兼容流正文逐步展示，工具片段完整性及恢复回归。
- [x] 中文短答 GUI 立即展示，定向回归。
- [ ] 文档、独立提交与开发后端生效检查。

原有两个 tracked 修改及未跟踪产物保留。现有全仓失败继续按加固台账处理，不宣称全仓通过。

## 验收结果

1. **原问题**：全 Skill 目录附到每轮用户消息、完整图表手册常驻；未知端点带工具时必须收到整段终态才输出；前端按空格数等 40 个词，中文短答几乎等于隐藏到结束。
2. **现在行为**：保持通用引擎与默认联网，通过 search_skills 分页检索已授权技能、load_skill 即时刷新更新/删除；图表细则通过第一方只读工具获取。兼容流逐段输出，JSON/XML/工具名分片完整后才恢复调用；Markdown/普通 JSON/图表在确认非工具后释放，不丢文字。断流已显示部分不重放。中文一个字也可显示，工具调用到达后仍沿用现有事件归档。
3. **离线测量**：相同 bundled 111 技能、相同隔离工作目录、真实引擎的假 Provider，基线 0129c2c 与候选版比较：保守估算 15,216 → 5,031 tokens（约 -67%）；system 5,884 → 3,740，动态用户上下文 8,421 → 277，工具 schema 911 → 1,014。新增图表说明入口稍增 schema，避免常驻详细手册。[脱敏计数](../../chemclaw/fixtures/chat-prompt-budget-2026-09-29.json)。这是估算，不等于下面真实 usage。
4. **真实验收**：用户另外批准两次请求，全部用于 deepseek-v4.1-flash 的新会话“你好”，每次输出最多 256。沿用现有 OpenCode Go 会话 header；仅内存读取提供商配置，独立状态/工作目录，不启动 gateway/scheduler，禁止工具执行，模拟 MCP 永不就绪。两次均 HTTP 200 / completed；输入均 4,017，输出 132/113，缓存读取 0。对比上一轮实际 10,420 输入，减少约 61%。首段 7.031/11.906 秒，整轮 8.312/13.171 秒，正文 55/47 次增量。MCP 准备仅 0.281/0.265 秒，结束时仍 pending。[脱敏证据](../../chemclaw/fixtures/chat-latency-live-2026-09-29.json)。两次新额度已用完，不再发请求。
5. **剩余速度问题**：两次响应头分别在 HTTP 发出后 4.25/9.297 秒到达。该事实不能细分为网关排队、服务端推理、网络链路或其他原因；首段 7–12 秒仍偏长。此次与旧基线日期、输出长度不同，样本小，不能声称整轮稳定提速；真实测量是引擎事件，并非屏幕实际绘制时间。后续需同时间同协议的最小请求/完整引擎对照，或服务端请求追踪，账号调用须新增授权。

## 实际测试

- 最终组合 14 文件 **193 passed**：chat_prompt_budget、compat_incremental_stream、providers、skills、skills_sessions、web_availability、subagent_readonly、runtime_resume、runtime_acceptance、mcp_startup_isolation、webpage_optional_prompts、turn_instrumentation、provider_router、deliver_mcp。
- 最后补充多段 JSON 非递归处理、工具名称共享前缀后，compat_incremental_stream + providers **81 passed**（含上述组合已有测试，不相加为总数）。含真实 WebSocket＋阻塞模拟流：收到正文事件后才放行后续网络块。
- GUI streamGate / BackgroundTasksSection / ChartBlock **65 passed**，`npx tsc --noEmit` 通过。
- 扩展两个组分别 **53 passed / 1 failed** 与 **87 passed / 1 failed**：`test_d182_subagent_profile_instructions_are_chinese` 固定旧措辞断言；`test_provider_extras_persist_on_message_and_survive_outbound` 误把尾部 checkpoint notice 当 assistant。两项在 `.tmp-stability-offline/results.json` 的已保存 9 月 27 日基线中同名同类失败，未算通过，也未顺手修改无关模块。
- 未构建、安装、合并 main；不宣称全仓通过或所有性能问题解决。发布门禁继续遵守主加固计划。
