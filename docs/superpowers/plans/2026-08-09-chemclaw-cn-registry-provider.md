# ChemClaw 国内登记 Provider 首包（D-100）

**Goal:** 强化内贸主体核验：统一社会信用代码 / 中文名 → 平台 `lookup_legal_entity` 路由到 `cn_registry`；不进 Skill；不接海关。

**Architecture:**
- `coworker/entity/cn_registry.py`：`CnRegistryProvider` + `RoutingLegalEntityProvider`
- USCC GB 32100 校验位；CJK 名称路由国内；LEI/拉丁名仍走 GLEIF
- SecretStore `cn_registry:default`：`base_url`（必填才联网）、可选 `api_key`
- Fixture 契约测试；CI 不依赖外网

**Status (2026-08-09):** 已完成。

## Tasks
- [x] USCC 校验 + CnRegistryProvider + 路由
- [x] Tool schema `query_type=uscc`；`agent.py` 注入 secrets
- [x] Fixture 测试；Skill 文档接线
- [x] D-100 / README / 规格

## Out of Scope
- TED / Comtrade / 海关全量 / 天眼查爬虫 / CRM
