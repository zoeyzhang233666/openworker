# D-166 化工现货与期货路由纠偏执行日志

- 日期：2026-08-19
- 状态：COMPLETE（生产外部数据源实查仍由已配置 chem-data-hub 决定）
- 基线：`chemclaw-clean`；受跟踪文件干净，既有未跟踪测试目录保留。

## Gate 1

- 已复现：`查原油的现货价格` 被投影为 `web_search/web_fetch`。
- 已复现：`查甲醇的现货价格` 被投影为 `lookup_cn_futures_*`。
- 原因：D-165 接通生产投影后，通用价格 Web fallback 与品种名即期货规则开始真实裁剪动态 MCP。
- 实施前 Router/TurnPlanner/Projection 基线：`77 passed`（worktree `--basetemp`）。

## Gate 2

- 新增不可变 `MarketIntent` / `MarketToolSelection`，市场口径判定与工具选择集中在 `coworker/market_intent.py`。
- `coworker.cn_market.symbols.find_futures_mentions` 复用权威品种目录，最长别名优先；`MA2509` 等合约代码确定为国内期货。
- `ToolRegistry.descriptors()` 仅向 Planner 暴露只读 name/category/capabilities；chem-data-hub 同时兼容 `chem-data-hub` / `chem_data_hub`。
- `TurnPlan.market_selection` 已接入生产 `build_engine`；明确现货只投影 `get_price_trend`，明确国内期货投影 quote + OHLC，WTI/Brent 投影 Yahoo OHLC，纯价格不投影 Web。
- 裸甲醇/原油投影 `ask_user` 与候选市场 schema；Engine 在权限审批前阻止未澄清或错误口径调用，回答后仅放行所选口径。重试复用已解析口径。
- 行情 prompt 删除“甲醇名称即期货”的旧示例，写明现货优先、MCP 缺失/空数据 unavailable、禁止 Web/Yahoo/期货补现货价。
- Router 或 tool projection OFF 时 D-166 策略保持 legacy-inert；`TurnEngine.run()`、权限、审批、流式与 ChartSpec 接口未改。

## Gate 3

- 最终聚焦路由/投影/Planner/Engine/CN symbol/Prompt/GUI/durable market resume：`94 passed`。
- 生产 `build_engine` prompt/schema 验证：明确现货有 MCP 时只有 `mcp__chem_data_hub__get_price_trend`；缺 MCP 时 `tools=None` 且 prompt 明确 unavailable。
- GUI WebSocket 矩阵（确定性 Provider + MCP 夹具）：原油现货、甲醇现货、甲醇期货、裸甲醇→国内期货全部通过；实际 `TOOL_PROPOSED/FINISHED` 名称符合口径（包含在最终 94 passed）。
- 广泛回归：Router、Projection、Prompt、CN 行情、Yahoo、MCP、权限审批、Stop、压缩、durable resume 共 `319 passed, 8 deselected`；8 项均为已确认的既有/环境失败：6 个 MCP connector 临时 secrets 写 ACL、1 个 automation scratch 写用户目录 ACL、1 个既有 `Mode.AUTO` durable approval 用例（文件直接执行、未产生待审批项）。与 D-166 路径无新增断言失败。
- 未调用真实外部价格源，避免把环境或账户数据写入验收；真实 chem-data-hub 空结果仍按代码策略返回“暂无现货数据”，不会切换价格源。
