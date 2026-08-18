---
name: chem-price-daily
description: "行情服务工具。按品种分区域自动生成价格日报/周报，含涨跌与样本量。 Use when the user asks about this chem-cloud skill scenario (化工品价格日报 / chem-price-daily). Prefer MCP tools: get_price_trend."
agent_created: true
---

# 化工品价格日报

> 来源：芯化单源 · 开放平台 Skill `chem-price-daily` · vendor=chem-cloud

## 适用场景

行情服务工具。按品种分区域自动生成价格日报/周报，含涨跌与样本量。

## 价值

每日自动推送价格日报，零人工整理

## 输入

- 用户自然语言需求（化学品名 / CAS / 企业信用代码 / 询单号等，视场景而定）
- 必须通过已配置的 **chem-data-hub** MCP 调用下列 Tool，禁止编造数据

## 可用 MCP Tool（仅限这些）

- `get_price_trend`

## 工作流

1. 确认用户目标与关键参数（CAS、信用代码、品名等）。缺参先追问。
2. 严格按 Tool 的 JSON Schema 传参调用 MCP（例如 `get_compound` 只要 `cas_no`；
   仅有中文名时先 `search_compound` 再查详情）。查趋势时默认拉够画上下文的历史：
   优先约 ≥60 个交易日（或月线 ≥12 点）。即使用户只问「今天/本周/某一个价」，
   也尽量拉更长序列作图。
3. 基于 Tool 返回整理答案；失败时说明错误并给出可重试建议。
4. 输出结构清晰的中文结论：**价格表 + 简要要点**；若 Tool 返回可用时间序列（≥2 个
   日期点），同一条回复还必须附一条 fenced ```chart`（ChartSpec v1、`type: line`），
   数值与表一致。用户点名某日/某周时设 `focusLabel` 为对应标签；无特定日期则省略
   （UI 默认钉最新）。序列足够长时可附 `stages`（`start`/`end` + grounded `reason` 只写
   主导因素/为什么，禁止复述涨跌横盘、禁止写入具体价格；UI 按区间涨跌幅重算方向）；
   点数不足划多段时可用单段覆盖询问窗只写驱动，或省略色带。禁止编造驱动。
   聊天内出图勿调用 `chart-image` / shell / Node；仅用户明确要 PNG/
   报告附件时才用 chart-image。

## 示例提示词

生成甲醇分区域价格日报。

## 免责声明

结果仅供业务参考，不构成法律/合规/投资建议。正式生产请使用本人 API Key 直连 datahub MCP。
