# 退役客户清单侧栏页（方案 A）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** 主导航不再出现「客户清单」；用户改在对话产物中使用 Markdown/CSV 清单。

**Architecture:** 只拆 GUI 壳。后端 `coworker/leads/`、`chem-lead-list`、外贸/内贸拓客龙虾接线不动。删除侧栏入口后，补查/重评改为纯对话。

**Status (2026-08-19):** 已完成并收口（D-168）。

## Tasks
- [x] 从 App/Sidebar 移除 leads surface、导航项与 followup 监听
- [x] 删除 LeadsWorkbench、requestLeadFollowup 及其测试；清理 i18n `nav.leads` / `leads.*`
- [x] D-168、修订 D-006 / DOMAIN / README
- [x] 定向 GUI 测试 + `tsc --noEmit`（`Sidebar`+`i18n`+`localization-audit` **31 passed**；`tsc --noEmit` exit 0）

## Out of Scope
- `format_lead_list` / `chem-lead-list` / 拓客龙虾
- SMTP / HubSpot 对话 CTA
- 删除 `docs/chemclaw/fixtures/smoke-lead-list.json`
