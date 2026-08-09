# ChemClaw TED TenderProvider Implementation Plan（D-101）

**Goal:** 欧盟公开招标检索 → 规范化 `OpportunitySignal`，挂商机雷达；口述无来源仍 `NeedsReview`。

**Architecture:**
- 平台 [`coworker/tender/`](../../../../coworker/tender/)：`TedProvider` + Tool `search_tenders`
- TED Search API：`POST https://api.ted.europa.eu/v3/notices/search`（免密钥）
- Fixture 契约测试；Skill/龙虾仅文档接线；不伪造 publication-number

**Status (2026-08-09):** 已完成（D-101）。

## Tasks
- [x] TedProvider + OpportunitySignal 映射 + tests
- [x] `search_tenders` 注册到 `agent.py`
- [x] chem-opportunity-radar / opportunity-radar-lobster 接线
- [x] D-101 / README / 规格

## Out of Scope
- Comtrade、CRM、SMTP、国内登记重做
