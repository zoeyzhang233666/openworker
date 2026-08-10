# ChemClaw SAM.gov TenderProvider（D-106）

**Goal:** 美国联邦公开采购检索 → 规范化 `OpportunitySignal`，挂商机雷达；口述无来源仍 `NeedsReview`。

**Architecture:**
- 平台 `coworker/tender/sam.py`：`SamProvider` + Tool `search_sam_opportunities`
- SAM Opportunities API v2 GET；SecretStore `sam:default`（`api_key`）
- Fixture 契约测试；Skill/龙虾仅文档接线；不伪造 noticeId

**Status (2026-08-10):** 已完成（D-106）。

## Tasks
- [x] SamProvider + OpportunitySignal 映射 + tests
- [x] `search_sam_opportunities` 注册到 `agent.py`
- [x] chem-opportunity-radar / opportunity-radar-lobster 接线
- [x] D-106 / README / 规格

## Out of Scope
- TED 重做、海关、SEC、USAspending、自动外发
