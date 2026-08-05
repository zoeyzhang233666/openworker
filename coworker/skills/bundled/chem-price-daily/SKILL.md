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
   仅有中文名时先 `search_compound` 再查详情）。
3. 基于 Tool 返回整理答案；失败时说明错误并给出可重试建议。
4. 输出结构清晰的中文结论（要点列表 + 必要原文字段）。

## 示例提示词

生成甲醇分区域价格日报。

## 免责声明

结果仅供业务参考，不构成法律/合规/投资建议。正式生产请使用本人 API Key 直连 datahub MCP。
