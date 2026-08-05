---
name: chem-newbiz-lead
description: "招商场景工具。用事件/企业检索捕捉化工相关新设与变更线索；已知信用代码时再查单企时间线。 Use when the user asks about this chem-cloud skill scenario (新设企业招商线索 / chem-newbiz-lead). Prefer MCP tools: search_sag_events, search_enterprise, search_sag_entities, get_enterprise_timeline."
agent_created: true
---

# 新设企业招商线索

> 来源：芯化单源 · 开放平台 Skill `chem-newbiz-lead` · vendor=chem-cloud

## 适用场景

招商场景工具。用事件/企业检索捕捉化工相关新设与变更线索；已知信用代码时再查单企时间线。

## 价值

每日自动捕捉新设/变更招商线索

## 输入

- 用户自然语言需求（化学品名 / CAS / 企业信用代码 / 询单号等，视场景而定）
- 必须通过已配置的 **chem-data-hub** MCP 调用下列 Tool，禁止编造数据

## 可用 MCP Tool（仅限这些）

- `search_sag_events`
- `search_enterprise`
- `search_sag_entities`
- `get_enterprise_timeline`

## 工作流

1. 确认用户目标与关键参数（CAS、信用代码、品名等）。缺参先追问。
2. 严格按 Tool 的 JSON Schema 传参调用 MCP（例如 `get_compound` 只要 `cas_no`；
   仅有中文名时先 `search_compound` 再查详情）。
3. 基于 Tool 返回整理答案；失败时说明错误并给出可重试建议。
4. 输出结构清晰的中文结论（要点列表 + 必要原文字段）。

## 示例提示词

列出近 30 天新设或变更的化工相关企业线索。

## 免责声明

结果仅供业务参考，不构成法律/合规/投资建议。正式生产请使用本人 API Key 直连 datahub MCP。
