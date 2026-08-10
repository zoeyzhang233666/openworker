# ChemClaw — 化工社合集 Triage（D-112）

> 状态：**已交付（2026-08-10）** — 分流表落盘；实现须另开小任务  
> 用户确认：「先做 triage 表」

## Goal

对 `D:\化工社skills合集` 全部 158 个 K-Dense zip 做 ChemClaw 销售镜头下的四档分流，避免盲目逐包猜、也禁止一次批量安装。

## Deliverables

- [`docs/chemclaw/HUAGONGSHE_SKILL_TRIAGE.md`](../../chemclaw/HUAGONGSHE_SKILL_TRIAGE.md)
- [`docs/chemclaw/fixtures/huagongshe_skill_triage.json`](../../chemclaw/fixtures/huagongshe_skill_triage.json)
- [`scripts/_gen_huagongshe_triage.py`](../../../scripts/_gen_huagongshe_triage.py)
- 决策 D-112

## Summary counts

| 档 | 数量 |
| --- | ---: |
| DONE | 1（`uncertainty-and-units`） |
| P0 | 1（`scientific-critical-thinking`） |
| P1 | 4 |
| P2 | 17 |
| Skip | 135 |

## Out of scope

- 本刀不 vendor 新 Skill
- 不接官方 reaction-publisher
- 不批准批量 `bundled/` 复制

## Next

用户确认 P0/P1（或捞回 Skip 包名）后，开下一实现刀。
