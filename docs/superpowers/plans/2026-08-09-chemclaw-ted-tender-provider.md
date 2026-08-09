# ChemClaw TED TenderProvider Implementation Plan（待点名后实现）

> 队列 B；**未获用户「开始实现 TED」前不写业务代码。**

**Goal:** 欧盟公开招标检索 → 规范化 `OpportunitySignal`，挂商机雷达龙虾；口述无来源仍 `NeedsReview`。

**Architecture（拟定）：**
- 平台 `coworker/tender/`（或 `opportunity/`）：`TedProvider` + Tool `search_tenders`（只读）
- Fixture 契约测试；可选 SecretStore 限流密钥
- Skill `chem-opportunity-radar` 文档接线：信号须带来源 URL；不把 API 塞进 Skill
- 不默认挂载询盘 MCP；不自动外发

**验收：** Fixture 覆盖 resolved/empty/error；雷达提示词禁止伪造 TED 编号；CI 无外网。

**Out of Scope：** Comtrade、国内登记重做、SMTP、CRM。
