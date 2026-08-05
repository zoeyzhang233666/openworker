---
name: chem-arb-analysis
description: "贸易套利工具。按多区域市场价格 min/max/avg 与样本数，自动识别跨市场价差与物流套利窗口。 Use when the user asks about this chem-cloud skill scenario (区域价差套利分析 / chem-arb-analysis). Prefer MCP tools: get_price_trend."
agent_created: true
---

# 区域价差套利分析

> 来源：芯化单源 · 开放平台 Skill `chem-arb-analysis` · vendor=chem-cloud

## 适用场景

贸易套利工具。按多区域市场价格 min/max/avg 与样本数，自动识别跨市场价差与物流套利窗口。

## 价值

相对人工盯价，更快发现跨区价差窗口

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

对比甲醇华东与华北近一周价差，判断是否存在套利窗口。

## 免责声明

结果仅供业务参考，不构成法律/合规/投资建议。正式生产请使用本人 API Key 直连 datahub MCP。
