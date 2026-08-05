---
name: chem-supplier-match
description: "撮合场景工具。输入询单化学品，AI 从平台 B2B 档案智能推荐合格供应商与历史报价。 Use when the user asks about this chem-cloud skill scenario (供应商反向匹配 / chem-supplier-match). Prefer MCP tools: get_enterprise_b2b, get_enterprise_commercial."
agent_created: true
---

# 供应商反向匹配

> 来源：芯化单源 · 开放平台 Skill `chem-supplier-match` · vendor=chem-cloud

## 适用场景

撮合场景工具。输入询单化学品，AI 从平台 B2B 档案智能推荐合格供应商与历史报价。

## 价值

相对人工寻源，约 3 分钟完成半小时工作

## 输入

- 用户自然语言需求（化学品名 / CAS / 企业信用代码 / 询单号等，视场景而定）
- 必须通过已配置的 **chem-data-hub** MCP 调用下列 Tool，禁止编造数据

## 可用 MCP Tool（仅限这些）

- `get_enterprise_b2b`
- `get_enterprise_commercial`

## 工作流

1. 确认用户目标与关键参数（CAS、信用代码、品名等）。缺参先追问。
2. 严格按 Tool 的 JSON Schema 传参调用 MCP（例如 `get_compound` 只要 `cas_no`；
   仅有中文名时先 `search_compound` 再查详情）。
3. 基于 Tool 返回整理答案；失败时说明错误并给出可重试建议。
4. 输出结构清晰的中文结论（要点列表 + 必要原文字段）。

## 示例提示词

按丙酮询单推荐合适供应商与可参考报价。

## 免责声明

结果仅供业务参考，不构成法律/合规/投资建议。正式生产请使用本人 API Key 直连 datahub MCP。
