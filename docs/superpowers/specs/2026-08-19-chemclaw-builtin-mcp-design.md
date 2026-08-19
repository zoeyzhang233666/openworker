# ChemClaw 内置 MCP（chem-data-hub / chem-biz-scope）设计

- 日期：2026-08-19
- 决策：D-167
- 状态：用户已批准（B1：构建注入 + 连接页只读「内置」），允许实现

## 1. 问题与目标

化工现货依赖 `chem-data-hub` MCP 的 `get_price_trend`（D-166）。测试版 exe 发给同事后，若未手动粘贴 MCP，现货会诚实 unavailable。需要把 `chem-data-hub` 与 `chem-biz-scope` 内置进安装包，同事零配置可用；连接页可见只读「内置」行，**界面与 `mcp.json` 不出现明文 key**。

## 2. 安全边界（必须诚实）

- 本方案只防「打开 APPDATA / 连接页偷看」。
- 桌面端若本地能调 MCP，密钥可被反编译、调试或抓包提取。
- Bundle 使用轻量混淆（XOR + base64），**不是**对外发版级密钥保管。
- 真实 key **永不**进入 Git；仅构建机旁路 `packaging/builtin_mcp.secrets.json`（gitignore）。

## 3. 方案（B1）

1. 仓库只存无密钥模板（`coworker/mcp/builtin_servers.json`）：URL、header 键、`${CHEMCLAW_BUILTIN_MCP_<SERVER>}`。`chem-data-hub` → `https://datahub.chem-cloud.cn/mcp`；`chem-biz-scope` → `http://121.37.133.47:8900/mcp`。
2. 构建时读取 gitignore 的 secrets → 生成 `builtin_mcp.bundle` 打进 sidecar datas。
3. `SessionManager` 启动调用 `seed_builtin_mcp()`：
   - 缺同名 server → 写入 `mcp.json`（仅 `${VAR}`）+ 将 token 写入状态目录 `.env`（现有 `${VAR}` 解析通道）。
   - 已有且 `chemclaw_builtin` → 可按 version 更新非密字段；**不覆盖**已有 `.env` 中同名 VAR。
   - 已有且非 builtin（用户自配）→ **跳过**。
   - 无 bundle / 无 token / 无可用 URL → 不种该 server。
4. REST：`builtin: true`；禁止 delete / 覆盖 / 改 url·headers·env；允许 `enabled`；`_redact` 保持。
5. GUI：徽章「内置」；隐藏删除；启停可用。

## 4. 非目标

- 公司网关代理鉴权
- 防专业逆向
- 改变 D-166 路由语义
- 把「ChemClaw Knowledge」等本机开发 MCP 打进安装包

## 5. 验收

见实施计划 `docs/superpowers/plans/2026-08-19-chemclaw-builtin-mcp.md`。
