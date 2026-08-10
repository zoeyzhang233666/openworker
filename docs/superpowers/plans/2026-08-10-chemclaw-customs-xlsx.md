# ChemClaw 海关 XLSX 支持（D-110）

**Goal:** 在 D-108 海关文件 Provider 上支持工作区 `.xlsx`；评分与货代过滤不变；不接外部 API。

**Architecture:**
- `CustomsFileProvider._load_rows`：CSV 标准库 + XLSX `openpyxl`（只读首表）
- Tool `filter_customs_importers` 描述与外贸拓客接线同步
- Fixture：同内容 CSV/XLSX 回归

**Status (2026-08-10):** 已完成（D-110）。

## Tasks

- [x] `pyproject.toml` 增加 `openpyxl>=3.1`
- [x] Provider 读 `.xlsx`；`.xls` 中文提示另存
- [x] Fixture + pytest（CSV/XLSX 推荐一致）
- [x] Tool/Skill/龙虾文案；D-110 / README / DOMAIN / GATE / 规格

## Out of Scope

- 外部海关/提单 API、pandas、多 sheet 合并产品化、`.xls` 原生解析
