# D-195 实施计划：企微流式 + 精装 COS HTML

规格：[`../specs/2026-08-31-chemclaw-wecom-stream-report-html-design.md`](../specs/2026-08-31-chemclaw-wecom-stream-report-html-design.md)

## 文件

| 路径 | 职责 |
|------|------|
| `coworker/connectors/wecom_bot.py` | `update_stream` |
| `coworker/server/manager.py` | wecom 过程推流 + 终态 |
| `coworker/channels/wecom_reply.py` | 终态合成 |
| `coworker/report_html/*` | MD cook + chart |
| `coworker/filestore/tencent_cos.py` | HTML inline |
| `tests/test_wecom_stream_reply.py` / `test_report_html_cook.py` | 定向验收 |

## 步骤

1. Spec + DECISIONS D-195 + README 状态。
2. Adapter `update_stream` + Gateway 可选转发。
3. `report_html` cook（含 zoom/fullscreen CDN）。
4. `wecom_reply` + `deliver_to_session` 接线。
5. 定向 pytest；真机清单人工。
