# ChemClaw GLEIF 法定主体 Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or subagent-driven-development.

**Goal:** 交付只读、免密钥的 `lookup_legal_entity` Tool（GLEIF API），供企业核验辅助主体解析；失败不伪造 LEI。

**Architecture:** 平台层 `coworker/entity/`（ABC + `GleifProvider` + Tool），镜像 `coworker/chem/`；不复用 LLM `coworker/providers/`；Skill 用 evidence locator 承载 LEI。

**Status (2026-08-09):** 已完成并收口（D-096）。

## Tasks

### Task 1: Provider + Tool + Fixture 契约
- [x] `coworker/entity/` + `lookup_legal_entity` + agent 注册

### Task 2: Skill 接线
- [x] `chem-company-qualification` 说明调用 Tool；接线测试

### Task 3: 治理
- [x] D-096、README、规格/DOMAIN、回归

## Out of Scope
- 国家登记 / 关系树 / TED / Comtrade / SMTP / 报价 / 数据源 GUI
