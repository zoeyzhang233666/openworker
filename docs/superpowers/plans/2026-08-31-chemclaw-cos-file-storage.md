# ChemClaw COS FileStorage 实施计划（D-194）

规格：[2026-08-31-chemclaw-cos-file-storage-design.md](../specs/2026-08-31-chemclaw-cos-file-storage-design.md)

状态：**已实现（自动验收）**；真机桶与手机端验收仍为人工门禁。

## Task 1：filestore 核心

- 新增 `coworker/filestore/`：`FileRef`、`FileStorage`、`MemoryFileStorage`、`TencentCosStorage`、配置加载。
- `cos-python-sdk-v5` 精确 pin 入 optional/`messaging`；lazy import。
- 验收：Memory 契约测试通过。

## Task 2：send_file 投递矩阵

- `coworker/connectors/file_delivery.py` + 改造 `make_send_file_tool`。
- Telegram / 企微降级 / Slack 原生优先。
- 验收：定向 pytest。

## Task 3：配置入口

- SecretStore `filestore:cos` + prefs 非密字段；设置/连接 UI 最小表单与中文说明。
- 验收：未配置错误文案；配置后可构造 storage。

## Task 4：文档

- 更新 `DECISIONS.md` / `README.md` / `DOMAIN.md` 与实测结果。
