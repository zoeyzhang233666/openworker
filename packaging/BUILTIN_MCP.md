# 内置 MCP（已退役 D-190）

**D-190（2026-08-27）**：产品不再自动种入 `chem-data-hub` / `chem-biz-scope`。启动时 `retire_builtin_mcp()` 会删除全局 `mcp.json` 中带 `chemclaw_builtin` 的旧条目，并清理 `.env` 里的 `CHEMCLAW_BUILTIN_MCP_*` 键。

请在 **连接 → MCP 服务器 → + 添加服务器** 中自行粘贴配置（与 Cursor 相同：`type`/`url`/`headers.Authorization`）。

本目录下的 `builtin_mcp.secrets.json` / `pack_builtin_mcp_secrets.py` 仅作历史参考，**不再参与 Windows 打包**。
