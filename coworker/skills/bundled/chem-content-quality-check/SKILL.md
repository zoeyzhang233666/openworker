---
name: chem-content-quality-check
description: "Use when 需要在发布审阅前对化工平台改写稿做确定性质量门禁；检查事实保持、敏感残留、平台结构与独立表达。"
---

# 化工内容质量门禁

对改写输出做确定性检查。不访问网页、不发帖、不登录平台。

载入后用绝对 `resources_path` 执行：

```powershell
python "$resources_path/scripts/check_content.py" gate-input.json --output gate.json
```

规则集 `chem-content-quality@1.0.0`。仅 `verdict=pass` 才可输出 `ready_for_publish_review`（人工审阅前状态，**不等于**已发布）。详见 `references/quality-rules.md`。

`revise` 时应回到 `chem-platform-rewrite`；`blocked` 须先处理策略命中再改写。
