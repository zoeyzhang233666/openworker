# ChemClaw PubChem 化学身份 Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or subagent-driven-development.

**Goal:** 交付只读、免密钥的 `lookup_chemical_identity` Tool（PubChem PUG-REST），供产品情报辅助身份核验；失败不伪造。

**Architecture:** 平台层 `coworker/chem/`（ABC + `PubChemProvider` + Tool），对齐 `coworker/web/`；不复用 LLM `coworker/providers/`；Skill 仍用本地 `cas.py`。

**Status (2026-08-09):** 已完成并收口（D-095）。

## Tasks

### Task 1: Provider + Tool + Fixture 契约
- [x] `coworker/chem/` + `lookup_chemical_identity` + agent 注册

### Task 2: Skill 接线
- [x] `chem-product-intelligence` 说明调用 Tool；集成测试

### Task 3: 治理
- [x] D-095、README、规格/DOMAIN、回归

## Out of Scope
- GLEIF / TED / Comtrade / SMTP / 报价 / 数据源 GUI
