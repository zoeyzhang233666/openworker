---
name: chem-ip-crosscheck
description: "知产合规工具。专利与商标、软著等知识产权交叉比对，补漏查重防侵权。 Use when the user asks about this chem-cloud skill scenario (IP 资产交叉核验 / chem-ip-crosscheck). Prefer MCP tools: get_enterprise_patents, get_patent_info."
agent_created: true
---

# IP 资产交叉核验

> 来源：core+ext · 开放平台 Skill `chem-ip-crosscheck` · vendor=chem-cloud

## 适用场景

知产合规工具。专利与商标、软著等知识产权交叉比对，补漏查重防侵权。

## 价值

上市或合作前交叉核验，提前发现缺口

## 输入

- 用户自然语言需求（化学品名 / CAS / 企业信用代码 / 询单号等，视场景而定）
- 必须通过已配置的 **chem-data-hub** MCP 调用下列 Tool，禁止编造数据

## 可用 MCP Tool（仅限这些）

- `get_enterprise_patents`
- `get_patent_info`

## 工作流

1. 确认用户目标与关键参数（CAS、信用代码、品名等）。缺参先追问。
2. 严格按 Tool 的 JSON Schema 传参调用 MCP（例如 `get_compound` 只要 `cas_no`；
   仅有中文名时先 `search_compound` 再查详情）。
3. 基于 Tool 返回整理答案；失败时说明错误并给出可重试建议。
4. 输出结构清晰的中文结论（要点列表 + 必要原文字段）。

## 示例提示词

对目标企业做 IP 交叉核验。

## 免责声明

结果仅供业务参考，不构成法律/合规/投资建议。正式生产请使用本人 API Key 直连 datahub MCP。
