# ChemClaw 海关企业级文件 Provider（D-108）

**Goal:** 用户工作区海关/提单 CSV → 筛货代噪声并排名候选进口商；与 Comtrade（国家/HS）严格区分；收货方≠终端买家。

**Architecture:**
- 平台 `coworker/customs/`：`CustomsFileProvider` + Tool `filter_customs_importers`
- 标准库 CSV；列名别名归一；关键词 + 角色/HS 集中度启发式评分
- Fixture 契约测试；挂外贸拓客 / 买家发现文档接线（不嵌客户端）

**Status (2026-08-10):** 已完成（D-108）。首包仅 CSV；XLSX / 外部海关 API 属后续。

## Tasks

- [x] `CustomsFileProvider` + 合成 CSV Fixture 契约测试
- [x] Tool `filter_customs_importers` + `build_engine` 注册
- [x] 缺文件/缺公司列中文错误；结果含非终端买家警告
- [x] Skill/龙虾文档接线 + wire 单测
- [x] D-108 / README / DOMAIN / GATE / 规格

## Out of Scope

- XLSX、外部海关/提单 API、买联系人、自动 CRM、化工社批量
- 将候选直接标为 Actionable Opportunity / Qualified Lead
