# ChemClaw 询盘转报价内置首包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or subagent-driven-development.

**Goal:** 用户询盘 → 可审计 Inquiry → 确定性 `calculate_quote` → 待审 `QuoteDraft`；不编造单价；草稿 ≠ 发送。

**Architecture:** 平台 `coworker/quote/` + Skill `chem-inquiry-to-quote`；挂到现有 `export-engagement-lobster`；复用 `chem-product-intelligence` 与可选 `chem-sales-quality-check`。

**Status (2026-08-09):** 已完成并收口（D-097）。

## Tasks

### Task 1: calculate_quote Tool
- [x] `coworker/quote/` + Fixture 测试 + agent 注册

### Task 2: chem-inquiry-to-quote
- [x] Inquiry / QuoteDraft / QuoteRun schemas + Skill + tests

### Task 3: Agent + 治理
- [x] 扩展外贸转化龙虾；D-097；README/DOMAIN/规格

## Out of Scope
- SMTP / 发送按钮 / CRM / chem-inquiry-feed MCP / TED / 新龙虾
