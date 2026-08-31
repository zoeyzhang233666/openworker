# ChemClaw 统一 FileStorage（腾讯云 COS）（D-194）

状态：**已实现（自动验收）**；真机 COS 桶与 Channel 端到端仍为人工门禁。

## 目标与边界

建立平台无关的 `FileRef` ↔ `FileStorage` 深模块，首版后端为腾讯云 COS。目的不是「只给企微上传」，而是让电脑端、其他电脑、服务器与手机 IM connector 能引用同一云端对象。

- **本机 EXE 对话产物**：只写会话 workspace，**默认不上 COS**（与 D-193 前行为一致）。
- **按需上传**：仅当用户经 `send_file`（或显式跨终端交付）发送到 Channel 时上传。
- **访问**：首版公开读 + `folder` 隔离（默认 `chemclaw`）；预签名/私有桶后续单独立项。
- **密钥**：`secret_id` / `secret_key` 只进 `SecretStore`（`filestore:cos`）；禁止写入仓库或规格正文。
- 不引入第二套 Agent runtime；继续使用现有 Session、权限与 `send_file` 审批面。

## 深模块

`coworker/filestore/`：

- `FileRef`：`storage_id`、`key`、`filename`、`content_type`、`size`、`url`、`created_at`（无 SDK 对象）。
- `FileStorage`：`upload` → `FileRef`、`exists`、`public_url`；可选 `download` 预留。
- `TencentCosStorage`：官方 `cos-python-sdk-v5`（精确 pin）；lazy import。
- `NullFileStorage` / 未配置：本机对话无感；需云交付时返回中文可操作错误。
- `MemoryFileStorage`：测试用。

对象键：`{folder}/{yyyy}/{mm}/{uuid}_{safe_filename}`。URL = `{pub_url.rstrip('/')}/{key}`。

非密配置（prefs / 设置）：`bucket`、`region`、`pub_url`、`folder`。

## 投递矩阵（1b）

`send_file` 读本地安全路径后：

1. 若已配置 COS → 上传得到 `FileRef`。
2. 按平台投递：
   - **Telegram**（无原生 FileSender）：只发 COS 公开 URL（可附标题/说明）。
   - **企微**：尝试原生 `upload_media`；失败或未连接 → **必须** URL 降级。
   - **Slack** 等已验证原生：优先原生附件；失败则 URL。
   - 飞书/钉钉/个人微信：同企微（尝试原生，失败 URL）。
3. 未配置 COS 且平台只能 URL 交付 → 中文错误，不静默失败。
4. 工具返回含 `delivery`（`native` | `cos_url`）与 `file_ref.url`（若有）。

## 验收

- Fake/Memory COS：键路径、`pub_url` 拼接、中文名、非法扩展名/超限拒绝。
- `send_file`：Telegram→URL；Slack→native（mock）；企微 native 失败→URL；未配置+Telegram→可操作错误。
- 本机无 `send_file` 的轮次不上传。
- D-193 回归不因可选 COS 依赖失败。

## 明确不做

预签名、全量产物自动同步、嵌入 CowAgent/LangBot、正式安装包、在仓库提交真实密钥。
