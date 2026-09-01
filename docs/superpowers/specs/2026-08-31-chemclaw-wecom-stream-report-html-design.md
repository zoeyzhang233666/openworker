# 企微流式 + 精装 COS HTML（D-195）

状态：**已实现（自动验收）**；真机企微 + COS 端到端仍为人工门禁。

**D-195b（2026-08-31）**：表格改用 PyPI `markdown`（GFM tables）；`mermaid` fence CDN 真渲染；模板版式升级（字体/斑马纹表/移动端横滚/图框）。KaTeX 仍后补。

## 目标

1. 企业微信智能机器人同 `stream.id` **过程可见再收束**：回合中多次 `reply_stream(finish=false)` 整段刷新进度/草稿；结束 `finish=true` 定稿。
2. 默认终态：**短总结 + 完整版 COS HTTPS 链接**（非全文进气泡）。
3. 完整版为**确定性精装报告页**（MD→固定模板 HTML），内嵌 Chart.js 直出 ````chart`，含滚轮缩放/平移与全屏；**不**恢复 D-077 模型自动烹饪。

## 合同

| 项 | 决定 |
|----|------|
| 流式 | 同 frame + stream.id；节流刷新；异常/finally 必须 `finish=true` |
| 默认终态 | `summary_link` |
| 覆盖 | 用户原文含「完整版贴出来」「不要链接」「气泡里全文」「直接发完整回答」等 → `full_bubble` |
| 短答无 MD | 不硬造 HTML；仅短文或总结 |
| HTML | cook MD；短引用 chart 用本轮 sidecar 烘焙；无法解析则占位 |
| 图表交互 | 缩放/平移/全屏在模板内；左栏/固定/阶段悬停后补 |
| COS | `text/html` → `ContentDisposition: inline` |
| COS 未配置 | 短总结 + 中文提示配置云存储；仍关流 |
| 范围 | **仅 wecom**；飞书/钉钉/微信/GUI 默认不变 |

## 模块

- `WecomBotAdapter.update_stream`：不 pop，`finish=False`
- `SessionManager.deliver_to_session`：wecom 节流推流 + 终态合成
- `coworker/report_html/`：cook + ChartSpec 最小解析 + 模板脚本
- `coworker/channels/wecom_reply.py`：模式判定、MD 发现、文案合成
- `TencentCosStorage.upload`：HTML inline

## 明确不做

飞书等通道同样默认、预签名桶、ChartBlock 左栏 1:1、D-077 后台烹饪、Mermaid/KaTeX CDN（可 D-195b）。

## 验收

- 单测：流式更新/关流、总结+链接、全文覆盖、cook 含 Chart.js/zoom/fullscreen、inline、COS 缺失降级。
- 真机：长研究过程刷新→终态可打开带图可缩放全屏页；短问候无死链；要求气泡全文则贴全文。
