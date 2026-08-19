# 内置 MCP 密钥（测试版打包）

ChemClaw 可将 `chem-data-hub` / `chem-biz-scope` 打进安装包（D-167），同事无需手动粘贴 MCP。

## 步骤

1. 复制本目录 `builtin_mcp.secrets.example.json` 为 `builtin_mcp.secrets.json`（已 gitignore）。
2. 填写 `tokens`（只要 token，不要 `Bearer ` 前缀）。
3. `chem-data-hub` / `chem-biz-scope` 的 URL 已在仓库模板中；`urls` 仅在需要覆盖时填写。
4. 运行 `.\packaging\build_windows.ps1`（会自动调用 `pack_builtin_mcp_secrets.py` 生成混淆 bundle）。
5. 发给同事的机器请用**干净** `%APPDATA%\ChemClaw` 首次启动（若对方已手工配过同名 MCP，内置不会覆盖）。

## 安全

- 真实 key / bundle **不要**提交 Git。
- Bundle 仅为混淆，反编译或抓包仍可能拿到 key；仅适合内部测试版。
