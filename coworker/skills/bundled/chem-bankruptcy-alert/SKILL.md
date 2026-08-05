---
name: chem-bankruptcy-alert
description: "债权与供应链风控工具。经营/招聘变化与破产重整信号交叉验证，提前预警断供风险。 Use when the user asks about this chem-cloud skill scenario (破产重整预警 / chem-bankruptcy-alert). Prefer MCP tools: get_enterprise_recruitment, get_bankruptcy_reorganization."
agent_created: true
---

# 破产重整预警

> 来源：core+ext · 开放平台 Skill `chem-bankruptcy-alert` · vendor=chem-cloud

## 适用场景

债权与供应链风控工具。经营/招聘变化与破产重整信号交叉验证，提前预警断供风险。

## 价值

相对事后发现，可提前 1–3 个月预警断供

## 输入

- 用户自然语言需求（化学品名 / CAS / 企业信用代码 / 询单号等，视场景而定）
- 必须通过已配置的 **chem-data-hub** MCP 调用下列 Tool，禁止编造数据

## 可用 MCP Tool（仅限这些）

- `get_enterprise_recruitment`
- `get_bankruptcy_reorganization`

## 工作流

1. 确认用户目标与关键参数（CAS、信用代码、品名等）。缺参先追问。
2. 严格按 Tool 的 JSON Schema 传参调用 MCP（例如 `get_compound` 只要 `cas_no`；
   仅有中文名时先 `search_compound` 再查详情）。
3. 基于 Tool 返回整理答案；失败时说明错误并给出可重试建议。
4. 输出结构清晰的中文结论（要点列表 + 必要原文字段）。

## 示例提示词

扫描重点供应商破产重整风险。

## 免责声明

结果仅供业务参考，不构成法律/合规/投资建议。正式生产请使用本人 API Key 直连 datahub MCP。
