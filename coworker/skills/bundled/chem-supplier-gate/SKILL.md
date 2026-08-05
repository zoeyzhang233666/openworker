---
name: chem-supplier-gate
description: "采购准入场景工具。结合供应商档案与行政处罚、经营异常、环保处罚等风险信号，一票否决问题主体。 Use when the user asks about this chem-cloud skill scenario (供应商准入合规闸门 / chem-supplier-gate). Prefer MCP tools: get_enterprise_b2b, get_administrative_penalty, get_environmental_penalty, get_business_exception."
agent_created: true
---

# 供应商准入合规闸门

> 来源：core+ext · 开放平台 Skill `chem-supplier-gate` · vendor=chem-cloud

## 适用场景

采购准入场景工具。结合供应商档案与行政处罚、经营异常、环保处罚等风险信号，一票否决问题主体。

## 价值

准入评审前自动排雷，少踩问题主体

## 输入

- 用户自然语言需求（化学品名 / CAS / 企业信用代码 / 询单号等，视场景而定）
- 必须通过已配置的 **chem-data-hub** MCP 调用下列 Tool，禁止编造数据

## 可用 MCP Tool（仅限这些）

- `get_enterprise_b2b`
- `get_administrative_penalty`
- `get_environmental_penalty`
- `get_business_exception`

## 工作流

1. 确认用户目标与关键参数（CAS、信用代码、品名等）。缺参先追问。
2. 严格按 Tool 的 JSON Schema 传参调用 MCP（例如 `get_compound` 只要 `cas_no`；
   仅有中文名时先 `search_compound` 再查详情）。
3. 基于 Tool 返回整理答案；失败时说明错误并给出可重试建议。
4. 输出结构清晰的中文结论（要点列表 + 必要原文字段）。

## 示例提示词

对候选供应商做准入合规闸门检查。

## 免责声明

结果仅供业务参考，不构成法律/合规/投资建议。正式生产请使用本人 API Key 直连 datahub MCP。
