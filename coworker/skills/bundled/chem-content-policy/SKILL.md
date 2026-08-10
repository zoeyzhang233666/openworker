---
name: chem-content-policy
description: "Use when 需要对化工平台文案做敏感词/广告法绝对化/安全承诺扫描；用确定性脚本 scan_content.py，区分平台经验与监管口径。"
---

# 化工内容表达策略与词表扫描

对改写稿（及可选原文）做确定性敏感表达扫描。不发帖、不登录平台。

## 载入后

用绝对 `resources_path` 执行：

```powershell
python "$resources_path/scripts/scan_content.py" --text-file draft.txt --lexicon "$resources_path/references/lexicon/base.csv" --output scan.json
```

或把文本经 stdin / `--text` 传入。规则见 `references/general-claims.md`、`references/chemical-claims.md`。

## 输出

JSON：`hits[]`（rule_id / term / severity / action）、`blocked` 布尔。`severity=block` 命中时不得直接宣称可发布。

平台经验规则与法律/监管口径必须在说明中区分，不要一律叫「违规」。
