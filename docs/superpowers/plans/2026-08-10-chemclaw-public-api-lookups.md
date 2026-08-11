# ChemClaw「连接 → API 公开查询」（D-113 / D-114）

**Status (2026-08-10):** 已完成（含 D-114 用途说明与密钥申请指引）。

## Goal

在「连接」页增加第三栏 **API 公开查询**，展示 Skill/Agent 用到的平台 Provider（免密钥 + 需密钥），并为 SAM / Comtrade / 国内登记 / 网页搜索提供 GUI 配置；每张卡片写清做什么、谁在用、如何配置，以及官方说明/申请外链。

## Delivered

- `coworker/public_lookups.py` + `GET/POST /v1/public-api-lookups`
- GUI：`IntegrationsView` 第三栏 + `PublicApiLookupsSection`（purpose / used_by / setup / docs_url / signup_url）
- 决策 D-113、D-114；DOMAIN / README / GATE 已同步

## Out of Scope

- 通用 `/v1/secrets`
- 连接器 / MCP / 模型密钥混入本栏
- 代申请密钥、内嵌第三方登录
- 海关外部 API、CRM 字段 CTA、M3
