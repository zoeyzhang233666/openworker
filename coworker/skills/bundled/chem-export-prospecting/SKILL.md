---
name: chem-export-prospecting
description: "Use when 用户要围绕具体化工 SKU 和目标市场执行可核验、可恢复的外贸拓客任务。"
---

# 外贸拓客编排

把一次任务组织为可恢复的 `ProspectingRun`，而不是一次性搜索或市场报告。仅在产品身份、目标市场、客户类型、排除条件和目标数量足够明确后启动；缺项必须追问。

## 输入与边界

- 输入：`CommercialSKU` 草稿、`TargetMarket`、目标 Lead 数与检索预算。
- 依次加载 `chem-product-intelligence`、`chem-buyer-discovery`、`chem-company-qualification`；评分由后续 `chem-lead-ranking` 负责。
- 外部搜索和读取仅用已配置 Tool/Provider；不得把搜索摘要当作页面证据。
- 评估目标市场吸引力时可用平台 Tool `lookup_trade_flow`（Comtrade）；结果仅为国家/HS 汇总，**不得**当作买家企业证据，也**不**在本 Skill 内嵌客户端。
- 用户已提供海关/提单 CSV 或 XLSX 时，可用平台 Tool `filter_customs_importers` 筛货代噪声并排名候选进口商；**收货方≠终端买家**，须与官网/主体交叉核验后再写入 Lead；**不**在本 Skill 内嵌解析客户端；支持 `.csv`/`.xlsx`（无外部海关 API；旧版 `.xls` 请另存）。
- 默认只读。发送邮件、购买联系人、写 CRM、上传客户资料或付费调用均须走现有审批。

## 状态机与断点

维护 `ProspectingRun` 的 `input → product_ready → discovery → qualification → ranking → complete|blocked` 状态。按 `schemas/prospecting-run.schema.json` 从开始就写入版本号、创建/更新时间、输入与目标市场、Provider/Skill/规则版本、预算和阶段记录。每一阶段保存输入/输出/查询/证据 ID、失败对象、断点和时间；任何阶段失败都返回已验证的部分结果及缺口，不能伪造补全。

在 `product_ready` 前，CAS、名称、规格或用途冲突必须标为 `blocked`；不要继续生成客户名单。发现阶段产出 `CompanyCandidate`，核验后才可能成为 Lead。结束时分别列出 `Qualified`、`NeedsReview`、`Rejected`，并给每项给出可执行的下一步。

## 输出纪律

用 `schemas/prospecting-run.schema.json` 组织结构化交付，并在对话中给出简洁摘要。状态为 `complete` 时必须至少有一个已记录阶段；始终保留候选/Lead ID、预算消耗、警告、未决问题与下一步。每个强结论链接到 `EvidenceItem`；不知道联系人时只建议岗位角色，绝不猜姓名、邮箱、采购量或成交概率。
