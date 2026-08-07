# ChemClaw 外贸销售转化内置能力包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** 交付「外贸转化龙虾」：联系策略、草稿、跟进计划与质量门禁；永不自动发送。

**Architecture:** `export-engagement-lobster` + `chem-sales-engagement` + `chem-sales-quality-check`；复用 `chem-product-intelligence`。

**Status (2026-08-07):** 已完成并收口（D-094）。GUI 需重启 sidecar 后可见；新 Agent 默认禁用。

## Tasks

### Task 1: chem-sales-quality-check
- [x] check_outreach.py + schemas + tests

### Task 2: chem-sales-engagement
- [x] EngagementRun / OutreachDraft / FollowupPlan + tests

### Task 3: Agent + 收口
- [x] Persona、i18n、集成、D-094

## Out of Scope
- 报价数学、SMTP Provider、发送按钮、客户清单工作台
