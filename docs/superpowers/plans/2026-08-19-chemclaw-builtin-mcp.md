# 内置 chem-data-hub / chem-biz-scope MCP（B1）实施计划

- 日期：2026-08-19
- 决策：D-167
- 规格：`docs/superpowers/specs/2026-08-19-chemclaw-builtin-mcp-design.md`

## 步骤

1. 仓库无密钥模板 + `coworker/mcp/builtin.py`（bundle 编解码、seed、`.env` 写入）
2. `SessionManager` 启动 seed；`list/add/patch/delete_mcp` 护栏
3. GUI `McpTab` 只读「内置」+ i18n
4. `packaging/builtin_mcp.secrets.example.json`、gitignore、`build_windows.ps1` / datas 注入
5. 定向测试 + DECISIONS / README

## 本地打测试包

1. 复制 `packaging/builtin_mcp.secrets.example.json` → `packaging/builtin_mcp.secrets.json`
2. 填入 `tokens`（及如需的 `urls.chem-biz-scope`）
3. 运行 `packaging/build_windows.ps1`（会生成 bundle 并打进 sidecar）
4. 干净 `%APPDATA%\ChemClaw` 首次启动验证连接页两行「内置」且现货可用
