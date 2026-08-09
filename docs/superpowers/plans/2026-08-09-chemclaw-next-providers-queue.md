# ChemClaw 国内登记 / TED·Comtrade Provider 队列计划（待批准后单点实现）

> 本文件落盘后续数据 Provider 选项；**一次只实现其中一个**，需用户点名后再写代码。

## 选项 A：国内工商/登记 Provider（强化内贸 D-092）

- 平台 `LegalEntityProvider` 国内后端（公开登记/可授权 API）
- Tool 可复用或并列 `lookup_legal_entity` 的国内 query_type
- Fixture 契约测试；不进 Skill

## 选项 B：TED TenderProvider（强化商机 D-093）

- 欧盟公开招标检索 → `OpportunitySignal`
- 挂商机雷达；口述无来源仍 NeedsReview

## 选项 C：Comtrade TradeFlowProvider

- 国家/HS 贸易流，辅助选市场，不直接产买家名单

**默认建议：** 先 A（内贸主体）或 B（若业务追欧标）；C 可后置。

**Out of Scope 于任一单点：** SMTP、化工社批量内置、客户清单重做。
