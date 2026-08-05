---
name: chem-master-data
description: "生产型企业主数据管理场景的核心工具。输入 CAS 号或品名，AI 自动生成化合物主档案（分子式/SMILES/理化性质/关联商品数），支撑一物一码主数据治理。 Use when the user asks about this chem-cloud skill scenario (化学品数字档案 / chem-master-data). Prefer MCP tools: get_compound, get_compound_details."
agent_created: true
---

# 化学品数字档案

> 来源：芯化单源 · 开放平台 Skill `chem-master-data` · vendor=chem-cloud

## 适用场景

生产型企业主数据管理场景的核心工具。输入 CAS 号或品名，AI 自动生成化合物主档案（分子式/SMILES/理化性质/关联商品数），支撑一物一码主数据治理。

## 价值

相对手工建档，约省 2–3 小时整理

## 输入

- 用户自然语言需求（化学品名 / CAS / 企业信用代码 / 询单号等，视场景而定）
- 必须通过已配置的 **chem-data-hub** MCP 调用下列 Tool，禁止编造数据

## 可用 MCP Tool（仅限这些）

- `get_compound`
- `get_compound_details`

## 工作流

1. 确认用户目标与关键参数（CAS、信用代码、品名等）。缺参先追问。
2. 严格按 Tool 的 JSON Schema 传参调用 MCP（例如 `get_compound` 只要 `cas_no`；
   仅有中文名时先 `search_compound` 再查详情）。
3. 基于 Tool 返回整理答案；失败时说明错误并给出可重试建议。
4. 输出结构清晰的中文结论（要点列表 + 必要原文字段）。

## 示例提示词

帮我生成 CAS 67-56-1 甲醇的化合物主档案，含分子式、SMILES、理化性质与关联商品数。

## 免责声明

结果仅供业务参考，不构成法律/合规/投资建议。正式生产请使用本人 API Key 直连 datahub MCP。
