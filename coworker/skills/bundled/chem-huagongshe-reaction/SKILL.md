---
name: chem-huagongshe-reaction
description: "Use when 用户要把实验/文献中的反应整理并校验或保存到化工社反应库（须 Token 与确认可见性）。"
---

# 化工社写反应（ChemClaw 边界编排）

把用户提供的明确事实整理成化工社反应草稿，经平台 Tool 校验后，**在用户确认可见性与保存意图后**才创建记录。本 Skill 只编排工作流；API 客户端在平台 Provider/Tool，不在本包内。契约见 https://huagongshe.com/api/agent-guide 。

**禁止**：整包拷贝官方英文 `huagongshe-reaction-publisher`；引入本机 RDKit 渲染；把 SVG 源码搬进模型上下文（结构图用平台 Tool `fetch_huagongshe_svg` 落盘）；把反应结果写入 Lead Fit / 客户评分；编造 SMILES、条件、收率或来源；在未收到 create 成功响应时声称已保存；未获用户明示时把 `visibility` 设为 `public`。

## 工作流

1. 只从用户给出的网页、文档、图片或文本提取**明确事实**；结构歧义或缺必要字段时先提问，不补猜。
2. 形成结构化草稿：至少各有一个 `REACTANT` 与 `PRODUCT`（`role` + `smiles`）；含 `visibility`、`source_type` 与配对单位字段（有值才写）。用户未决定公开时 **`visibility=private`**。
3. 向用户展示参与物、条件、来源与可见范围，取得保存确认；公开必须用户明示。
4. 先调用平台 Tool `validate_huagongshe_reaction`（须已在「连接 → API 公开查询」配置 `huagongshe:default` Token；校验**不写库**、不走审批）。
5. 校验通过且用户确认后，调用 `create_huagongshe_reaction`（须审批；缺 `idempotency_key` 时 Tool 会生成并回显，**同一次保存重试须复用该 key**）。
6. 仅在 create 返回成功时报告 HRID、页面地址、可见范围与 `created_chemical_ids`；编辑/删改/改可见性请用户在化工社网页完成。

## 边界

- 反应数据**不进**客户搜索与 Lead 评分；不得据此编造买家或商机。
- Token 只发给 `huagongshe.com`；无 Token 时披露中文错误并引导配置，不假装成功。
- 网络请求只经平台 Tool；本 Skill 内不直接 HTTP、不装官方整包 Skill、不依赖 RDKit。
- 需要检索已有化合物时可用只读 `search_huagongshe` / `lookup_huagongshe_chemical`；需要 2D 结构图时用 `fetch_huagongshe_svg`（落盘产物，禁止 `web_fetch`）；写路径仍以 validate → create 为准。
