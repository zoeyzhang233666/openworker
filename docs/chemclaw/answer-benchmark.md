# 回答速度与质量评测

## 本轮已经能观测什么

既有 `/v1/turn-traces` 列表与详情返回新增计时，沿用原鉴权与保留策略。没有新增联网、模型请求或消息内容日志。旧记录读取时新增字段为空/零；`usage_reported_calls=0` 表示没有已报告用量，不能宣称零 token 成本。

`model_call_timings` 每项对应引擎的一次主模型流请求，包含准备/失败/中断情况。HTTP 内部重试仍属于这次调用，`http_requests` 内每个请求单列。所有 `*_ms` 为本次模型调用开始后的偏移；仅 `offset_ms` 是相对本轮 trace 开始。

| 字段 | 口径 |
| --- | --- |
| `provider_start_ms` | `_astream` 开始到生产线程开始调用 Provider；包含请求准备和线程排队 |
| `http_requests[].request_ms` | HTTP 客户端请求 hook 时刻，不是网络抓包的首字节发出时刻 |
| `http_requests[].headers_ms` | HTTP 客户端响应 hook 时刻，响应头已到达、流式正文尚未消费 |
| `upstream_first_content_ms` | SDK 解析出首个非空 content；可能是工具 JSON，不能称作有用答案 |
| `upstream_first_reasoning_ms` | SDK 解析出首个非空 reasoning |
| `provider_first_text_ms` | Provider 释放首个正文增量，兼容工具暂存发生在这之前 |
| `engine_first_text_ms` | 引擎接收首个正文增量，包含生产线程到消费协程的调度延迟 |
| `elapsed_ms` | 本次调用退出时间，停止后冻结；不等待迟到的网络线程结束 |
| `status` | 调用完成、失败或中断；调用完成不等于业务任务完成 |

HTTP hook 和上游 content/reasoning 计时首版覆盖 OpenAI Chat Completions 兼容链路（含其重试与 complete 回退的 HTTP 请求）。其他 Provider 仍有通用准备、正文增量和结束时间；未观测的 HTTP/上游时标保持 null。测试注入的非 HTTP 客户端也保持空值。每次调用最多保留 32 个 HTTP 请求明细，`http_request_count` 保存实际数量，可判断是否截断。

`stage_elapsed_ms` 保留 total/router，增加 first_engine_text、model_calls、tools_and_approval、compaction。`tools_and_approval` 从首个工具提议到该批迭代结束，是包含审批/用户等待与执行的墙钟时间，不把并行工具耗时相加。`first_engine_text` 包含直接终态正文，但也可能只是过程叙述。

**限制**：trace 在引擎激活计划后开始，暂不含界面发送前、入口 MCP 准备和实际屏幕绘制；这些不能通过减去后端时标推算。压缩的辅助模型请求尚未纳入逐次模型明细和 token 汇总，仅统计压缩阶段耗时。既有 input_tokens 为含缓存的 prompt 总量；缓存分别列出，不能再次相加当总消耗。缺失或部分 usage 不可当完整账单。

## 固定题库与对照

题库：[answer-benchmark-cases.json](fixtures/answer-benchmark-cases.json)，12 题，包括用户卓创案例及交付恢复。它是评测定义，不是已经跑出的效果数据。

1. 同模型/提供商/推理设置/资料/时间窗比较实现变体，配置使用不同 `configuration_id` 留档。
2. 比较提供商时保持执行策略一致，另列配置，不能混在一起宣称框架改进。
3. 每次运行导出该轮 trace；按题目人工核对 coverage、factuality、citation_support、analysis、uncertainty、readability，0/1/2 分别表示失败/部分/满足。
4. 用户按下发送到屏幕首次正文、首次有用答案的时间，由独立屏幕测试或人工记录；没有观测就省略字段。不能把“正在搜索”计作有用答案。
5. 真实账号调用仍须在用户授权范围内执行。当前只有离线回归，没有真实卓创案例的前后性能结论。

## 离线汇总工具

准备 JSON 数组，每行形式如下，`trace` 放入已有接口导出的完整 trace JSON：

```json
{
  "case_id": "sci99_overview",
  "variant": "baseline",
  "configuration_id": "provider-model-effort-fixtures-v1",
  "measurement_kind": "offline",
  "trace": {},
  "quality": {}
}
```

上面是结构示意，空 trace 不能通过校验。`measurement_kind` 必须明确为 offline 或 live；不得把离线模拟结果标为 live。可选字段 `screen_first_text_ms` 和 `first_useful_answer_ms` 仅填写独立观测值。

```powershell
.venv/Scripts/python.exe scripts/summarize_answer_benchmark.py --input benchmark-records.json --output benchmark-summary.json
```

工具仅读取指定文件，不访问网络或当前会话数据库。按题目/变体/配置/观测类型/模型分别汇总样本数、中位数、状态和质量；有效样本少于 20 不给 P95。缺失、非数值、非有限数和负值不作为零加入统计。HTTP 分布按请求计数，整体指标按轮次计数；离线和真实数据不会合并。失败/暂停数量仍显示，不能仅挑成功且快的样本。
