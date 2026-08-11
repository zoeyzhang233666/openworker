# public-apis 短名单连通探针（2026-08-10）

本机（Windows / 中国大陆网络）对计划短名单公开端点各打 1–2 次请求。列表里的 Auth=`No` **不等于**大陆可用或真免密钥。

## 结果摘要

| 目标 | 可达 | HTTP | 延迟 | 结论 |
|------|------|------|------|------|
| Tenders.guru PL `GET /api/pl/tenders` | 否 | — | ~21s | 无法连接远程服务器；**不接** |
| Tenders.guru ES `GET /api/es/tenders` | 否 | — | ~13s | 同上；**不接** |
| OpenSanctions `GET /search/default?q=BASF` | 部分 | 401 | ~1s | 主机可达但需授权；列表标 No 已过时；**不接（需 key）** |
| VATComply rates `GET /rates?base=EUR` | 是 | 200 | ~1.9s | 真免密钥；可用 |
| VATComply VAT `GET /vat?vat_number=…` | 是 | 200 | ~0.5s | 真免密钥；**本刀接入** |
| Frankfurter `GET /latest?from=EUR&to=USD,CNY` | 是 | 200 | ~4.8s | 真免密钥；报价换算候选，本刀不接（一次只一个） |
| USAspending awards `POST /api/v2/search/spending_by_award/` | 是 | 200 | ~2.2s | 免密钥；偏联邦花钱历史，作 SAM 弱替代候选，本刀不接 |
| World Bank indicator `GET …/NY.GDP.MKTP.CD` | 是 | 200 | ~0.7s | 免密钥；宏观指标，弱替代 Comtrade，本刀不接 |

原始 JSON：[`PUBLIC_API_PROBE_2026-08-10.json`](PUBLIC_API_PROBE_2026-08-10.json)

## 本刀选定

**按业务场景（D-117）已接入并接线 Skill/龙虾：**

| Tool | 业务 | 接线 |
|------|------|------|
| `validate_eu_vat` | 欧盟 VAT 核验 | 企业核验 / 外贸·商机 |
| `lookup_fx_rate` | 报价换汇 | 询盘转报价 / 转化龙虾 |
| `lookup_wikipedia` | 品名百科背景 | 产品情报 / 外贸·内贸·商机 |

**延期：** USAspending、World Bank（探针通但拓客 ROI 低，须另点名）。

## 未接入原因（备忘）

- Tenders.guru：本机不可达，不能当大陆默认商机源（继续用 TED）。
- OpenSanctions：401，不能当免密钥合规筛查。
- Frankfurter / Wikipedia：已在 D-117 按业务接入（见上表）。
- USAspending / World Bank：探针通过，业务延期。
