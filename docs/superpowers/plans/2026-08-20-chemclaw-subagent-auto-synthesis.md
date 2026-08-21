# ChemClaw Subagent 自动汇合实施计划（D-175）

> **For agentic workers:** 按任务顺序实现；每步有验证。规格：[`2026-08-20-chemclaw-subagent-auto-synthesis-design.md`](../specs/2026-08-20-chemclaw-subagent-auto-synthesis-design.md)。

## Task 1：DelegationCohort 模块 + 单测

- 新增 `coworker/subagents/cohort.py`
- 新增 `tests/test_delegation_cohort.py`
- 覆盖：全齐一次、含失败、不重复 fire、新批、持久化可选

## Task 2：SessionManager 接线

- `_on_background_task_change`：register / complete_job / on_terminal / deliver_to_session
- 测试：`tests/test_subagent_cohort_wake.py` mock deliver

## Task 3：短 gather + 委派文案

- `background_task_gather` 默认 60
- `_SUBAGENT_DELEGATION_CONTEXT` 更新

## Task 4：文档

- DECISIONS D-175、README、DOMAIN、TESTING
