# 资格、证据与风险规则

证据等级采用确定性来源上限：`official_website`、`government_registry` 最高 A；`trade_record`、`industry_directory`、`public_procurement` 最高 B；`b2b_directory`、`search_result`、`user_file` 最高 C；`other` 只能 D。低等级来源不得由模型抬高；较高等级来源仍可因事实薄弱而降级。A/B 可支持资格，C 仅发现，D 仅排入补查。

同一集团的品牌、法人和工厂不可因相同名称自动合并。冲突来源并列保存；若无法确认主体或产品关联，状态为 `NeedsReview`。Qualified 必须是 resolved 主体、非空规范名、主体与角色有正向无冲突证据，并且产品/应用相关性满足一条 A 或两个独立来源组的 B。公开邮箱也不自动等于可靠联系人。

来源 locator 只能来自实际打开的 URL、真实用户文件或 Provider 返回的记录 ID。禁止用 `task-provided:*`、`unknown:*` 等占位 locator 填合同；只有用户口述且没有可回溯来源时，必须进入 `NeedsReview` 并提出补证问题，不能标成 Qualified。事件型事实缺少 `event_date` 时不得支持 `signal_recency`；`collected_at` 不得冒充事件日期。

法定主体外呼使用平台 Tool `lookup_legal_entity`（GLEIF 与/或国内登记）。LEI/USCC 证据按 `government_registry`（上限 A）记录；`ambiguous`/`not_found`/`error` 不得伪造 LEI/USCC 或抬高为 Qualified 主体。
