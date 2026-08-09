---
name: chem-domestic-prospecting
description: "Use when 用户要围绕具体化工 SKU 和国内市场/园区执行可核验、可恢复的内贸拓客任务。"
---

# 内贸拓客编排

把一次国内拓客任务组织为可恢复的 `ProspectingRun`，而不是一次性搜索或市场报告。仅在产品身份、国内目标市场（省/市/园区可选）、客户类型、排除条件和目标数量足够明确后启动；缺项必须追问。

## 输入与边界

- 输入：`CommercialSKU` 草稿、面向中国大陆的 `TargetMarket`、目标 Lead 数与检索预算。
- 依次加载 `chem-product-intelligence`、`chem-buyer-discovery`、`chem-company-qualification`；评分由后续 `chem-lead-ranking` 负责。
- 外部搜索和读取仅用已配置 Tool/Provider；不得把搜索摘要当作页面证据；国内主体可用平台 `lookup_legal_entity`（`uscc`/中文名，Provider `cn_registry`），**不**在本 Skill 内嵌工商/海关 API 客户端。
- 默认只读。发送邮件/短信、购买联系人、写 CRM、上传客户资料或付费调用均须走现有审批。

## 国内规则要点

详见 `references/domestic-prospecting-workflow.md`：中文查询矩阵、统一社会信用代码优先、园区/工商公开证据、物流货代噪声排除、只建议岗位不编造手机/微信。

## 状态机与断点

维护 `ProspectingRun` 的 `input → product_ready → discovery → qualification → ranking → complete|blocked` 状态。按 `schemas/prospecting-run.schema.json` 从开始就写入版本号、创建/更新时间、输入与目标市场、Provider/Skill/规则版本、预算和阶段记录。每一阶段保存输入/输出/查询/证据 ID、失败对象、断点和时间；任何阶段失败都返回已验证的部分结果及缺口，不能伪造补全。

在 `product_ready` 前，CAS、名称、规格或用途冲突必须标为 `blocked`；不要继续生成客户名单。发现阶段产出 `CompanyCandidate`，核验后才可能成为 Lead。结束时分别列出 `Qualified`、`NeedsReview`、`Rejected`，并给每项给出可执行的下一步。

## 输出纪律

用 `schemas/prospecting-run.schema.json` 组织结构化交付，并在对话中给出简洁摘要。状态为 `complete` 时必须至少有一个已记录阶段；始终保留候选/Lead ID、预算消耗、警告、未决问题与下一步。每个强结论链接到 `EvidenceItem`；不知道联系人时只建议岗位角色，绝不猜姓名、手机、微信、采购量或成交概率；不得伪造统一社会信用代码或 `task-provided:*` 占位 locator。
