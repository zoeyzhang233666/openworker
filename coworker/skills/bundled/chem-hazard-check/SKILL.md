---
name: chem-hazard-check
description: "EHS 与仓储物流的合规工具。输入化学品，AI 自动返回 GHS 符号、信号词、危险说明与防范声明，出海（GHS/CLP）一键校验。 Use when the user asks about this chem-cloud skill scenario (危险品合规速查 / chem-hazard-check). Prefer MCP tools: get_compound_details."
agent_created: true
---

# 危险品合规速查

> 来源：芯化单源 · 开放平台 Skill `chem-hazard-check` · vendor=chem-cloud

## 适用场景

EHS 与仓储物流的合规工具。输入化学品，AI 自动返回 GHS 符号、信号词、危险说明与防范声明，出海（GHS/CLP）一键校验。

## 价值

相对人工核对，约 3 分钟完成半天工作量

## 输入

- 用户自然语言需求（化学品名 / CAS / 企业信用代码 / 询单号等，视场景而定）
- 必须通过已配置的 **chem-data-hub** MCP 调用下列 Tool，禁止编造数据

## 可用 MCP Tool（仅限这些）

- `get_compound_details`

## 工作流

1. 确认用户目标与关键参数（CAS、信用代码、品名等）。缺参先追问。
2. 严格按 Tool 的 JSON Schema 传参调用 MCP（例如 `get_compound` 只要 `cas_no`；
   仅有中文名时先 `search_compound` 再查详情）。
3. 基于 Tool 返回整理答案；失败时说明错误并给出可重试建议。
4. 输出结构清晰的中文结论（要点列表 + 必要原文字段）。

## 示例提示词

查询甲醇的 GHS 分类、信号词与防范说明，用于仓储标签核对。

## 免责声明

结果仅供业务参考，不构成法律/合规/投资建议。正式生产请使用本人 API Key 直连 datahub MCP。
