# ChemClaw 客户清单工作台首包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** 把拓客评分结果收成可经营客户清单（Markdown + CSV），含分桶与销售状态；不发送、不写 CRM。

**Architecture:** 平台 `coworker/leads/` Tool `format_lead_list` + Skill `chem-lead-list`；挂外贸/内贸拓客龙虾；GUI「客户清单」页（D-098）。

**Status (2026-08-09):** 已完成并收口（D-098）。

## Tasks
- [x] format_lead_list + tests
- [x] chem-lead-list + 拓客龙虾接线
- [x] GUI LeadsWorkbench + nav
- [x] D-098 / README；SMTP 与 Provider 仅队列计划落盘

## Out of Scope
- SMTP / 发送按钮 / 真实 CRM / TED 实现
