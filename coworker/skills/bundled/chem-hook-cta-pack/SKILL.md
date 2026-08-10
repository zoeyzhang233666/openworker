---
name: chem-hook-cta-pack
description: "Use when 用户明确要求标题、封面字、开篇钩子或 CTA 候选；在已有 RewriteBrief 与成稿基础上生成变体，不新增事实，不替代正文重构与最终门禁。"
---

# 化工内容钩子与 CTA 包

仅在用户要**标题 / 封面字 / 开篇钩子 / CTA**时 `load_skill`。日常四核心流水线**不要**每次加载本 Skill。

## 输入

- 已有 `RewriteBrief`（事实合同）
- 已有平台成稿（或至少正文骨架）
- 目标平台：`xiaohongshu` / `douyin` / `x`

## 输出

按 `schemas/hook-cta-pack.schema.json` 给出候选，并声明 `facts_unchanged=true`。平台细则见 `references/`。

- 小红书：标题、封面字、开篇钩子、评论区/私信式 CTA（不得编造联系方式）
- 抖音：前 3 秒钩子、口播开场、话题向 CTA
- X：首帖钩子、线程引导、简短 CTA

## 硬约束

- **不得新增** `immutable_facts` / `unknown_fields` 之外的 CAS、纯度、认证、检测、案例、价格、交期、疗效、「包过 / 绝对安全」类表述。
- 未知联系方式或商务信息：写「请用户补充」或留在 unknown，**禁止编造**手机/微信/邮箱。
- 本 Skill **不替代** `chem-platform-rewrite` 正文重构，也**不做**最终合规判定；钩子写入成稿后仍须走 `chem-content-policy` → `chem-content-quality-check`。
- 详见 `references/anti-patterns.md` 与 `references/cta-patterns.md`。
