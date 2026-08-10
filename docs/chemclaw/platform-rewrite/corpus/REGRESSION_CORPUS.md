# 内容重构回归语料（M2）

合成夹具，用于确定性扫描 / 门禁回归。**不是**真实客户稿；业务样例可后续替换同结构 JSON。

## 目录

- `cases/*.json` — 每条含 `id`、`platform`、`source`、`brief`、`output`（可选）、`expect`
- 运行：`pytest tests/test_platform_rewrite_corpus.py`

## 覆盖矩阵

| id | platform | 类型 | 期望要点 |
|----|----------|------|----------|
| 01-safe-xhs | xiaohongshu | 安全 | scan 不 block；gate pass |
| 02-safe-douyin | douyin | 安全 | gate pass |
| 03-safe-x | x | 安全 | gate pass |
| 04-risky-xhs | xiaohongshu | 禁词 | scan.blocked |
| 05-risky-douyin | douyin | 禁词 | scan.blocked |
| 06-risky-x | x | 禁词 | scan.blocked |
| 07-missing-cas | xiaohongshu | 缺事实 | must_not_contain 伪造 CAS |
| 08-missing-cert | douyin | 缺认证 | must_not_contain 伪造认证 |
| 09-fact-drift | xiaohongshu | 纯度漂移 | gate != pass |
| 10-hook-cta-safe | xiaohongshu | 钩子无新事实 | schema + must_not_contain |
| 11-safe-alt-product | x | 另一品名安全 | gate pass |
| 12-risky-alt-product | douyin | 另一品名禁词 | scan.blocked |

## 约定

- `expect.scan_blocked`: 是否要求 `scan_content` 的 `blocked=true`
- `expect.gate_verdict`: 若提供 `output`，则跑 `check_content` 并断言 verdict
- `expect.must_not_contain`: 输出中禁止出现的子串（防编造）
