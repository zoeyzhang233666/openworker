---
name: chem-platform-rewrite
description: "Use when 已有 RewriteBrief，需要按小红书/抖音/X 重构化工表达；只改表达不新增事实，不做最终合规判定。"
---

# 化工多平台表达重构

根据 `RewriteBrief` 重构表达：改变句式、结构与信息排序，**保留事实字段**，适配目标平台语气与版式。

## 边界

- 不新增 `immutable_facts` / `unknown_fields` 之外的产品事实。
- 不承担最终合规判定；须交给 `chem-content-policy` 与 `chem-content-quality-check`。
- 不为降重修改 CAS、纯度、规格、数值、包装、已知认证。
- 平台规范见 `references/platforms/`。

## 交付结构

- 小红书：【标题】【封面字】【正文】【标签】【改写说明】
- 抖音：【口播稿】【画面提示】【话题】【改写说明】
- X：【帖文】【线程拆分（可选）】【Hashtags】【改写说明】

结构化摘要可对照 `schemas/rewrite-output.schema.json`。默认不发帖、不登录平台。
