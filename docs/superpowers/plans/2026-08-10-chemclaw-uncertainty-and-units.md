# ChemClaw — uncertainty-and-units 单包（D-111）

> 状态：**已交付（2026-08-10）**；`pytest tests/test_uncertainty_and_units_skill.py` → 4 passed  
> 来源：`D:\化工社skills合集` 内 K-Dense `uncertainty-and-units.zip`（MIT）

## Goal

把合集中的单位/不确定度 Skill 作为阶段 6 **第一个**试点单包引入 ChemClaw：服务询盘/报价数字可信，不进入 Lead 评分，不批量内置其余 157 包。

## Scope

- Vendor 到 `coworker/skills/bundled/uncertainty-and-units/`
- 中文 ChemClaw 边界 + `references/chemclaw-usage.md`
- `pyproject.toml` optional-deps `uncertainty`（仅 pint + uncertainties）
- `chem-inquiry-to-quote` / `export-engagement-lobster` **可选**接线（非强制 `skills:`）

## Out of scope

- rdkit / datamol / 官方 reaction-publisher / 化工社 HTTP API
- 把 NumPy/SciPy 写入核心或默认 optional
- 强制挂外贸/内贸/商机龙虾

## Tasks

1. TDD：`tests/test_uncertainty_and_units_skill.py`
2. Vendor + 中文化
3. Wire + 治理文档 D-111
4. 定向 pytest

## Acceptance

见测试文件四用例 + README/DECISIONS 更新。
