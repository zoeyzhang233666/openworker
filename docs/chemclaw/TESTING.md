# ChemClaw 测试、开发环境与源码预览

## 1. 本次基线结论

- 基线日期：2026-07-29
- 被测提交：`ba58832c98cabab3f357edf50631782a5f773288`
- 分支：`design/chemclaw-foundation`
- Worktree：`D:\OpenWorker\openworker\.worktrees\chemclaw-design`
- 本次没有修改产品界面或 ChemClaw 业务功能。
- 已修复刚克隆源码无法启动的依赖断裂：项目仍使用 MCP 1.x API，因此依赖约束由无上限的 `mcp>=1.1` 改为 `mcp>=1.27,<2`。实际解析版本为 `mcp 1.29.0`。
- 浏览器源码预览已做真实页面验证：后端 `/v1/health` 返回 `{"status":"ok"}`，页面不再停留在 `Starting OpenWorker…`。
- GUI 单元测试、生产构建、Playwright E2E 和 Tauri `cargo check` 已通过。
- 后端全量测试在 Windows 上仍有已定位的上游基线失败，详见“已知后端基线缺陷”。在处理或明确接受这些失败前，不得声称后端全量基线为绿色。

## 2. 固定开发环境

### 工具版本

| 工具 | 本次版本 |
| --- | --- |
| Python | 3.11.15 |
| pytest | 9.1.1 |
| uv | 0.11.11 |
| Node.js | 24.15.0 |
| npm | 11.12.1 |
| Playwright | 1.61.1 |
| Rust | rustc 1.97.1 |
| Cargo | 1.97.1 |
| Visual Studio Build Tools | 2022 / 17.14.37 |
| LLVM/Clang | 22.1.8 |
| MCP Python SDK | 1.29.0 |
| slack-bolt | 1.30.0 |

### 目录分工

| 目录 | 用途 | 是否每个 Worktree 重装 |
| --- | --- | --- |
| `D:\OpenWorker\.chemclaw-dev\uv-cache` | Python 包下载缓存 | 否 |
| `D:\OpenWorker\.chemclaw-dev\uv-python` | uv 管理的 Python 3.11 | 否 |
| `D:\OpenWorker\.chemclaw-dev\state` | 当前 ChemClaw 开发状态 | 否，多个源码启动会复用 |
| `D:\OpenWorker\.chemclaw-dev\pytest-tmp` | pytest 专用临时目录 | 否 |
| Worktree 根目录的 `.venv` | 当前源码的 Python 可执行入口 | 每个活跃 Worktree 一个，但包下载缓存复用 |
| `surfaces\gui\node_modules` | 当前 GUI 依赖 | 每个活跃 Worktree 一个，npm 下载缓存复用 |
| `%USERPROFILE%\.cargo` | Rust 工具链和 crate 缓存 | 否，全机用户级复用 |
| `%LOCALAPPDATA%\ms-playwright` | Chromium 测试浏览器 | 否，全机用户级复用 |

Visual Studio Build Tools、LLVM、Rust 和 Playwright 浏览器是一次性机器环境。以后新开 Codex 对话不会重装；只有新建需要独立运行的 Worktree 时，才可能需要为那个 Worktree 建立 `.venv` 和 `node_modules`。

### Python 与前端依赖

后端全量测试会使用 Slack/Telegram 测试，因此安装方式必须与仓库 CI 一致，包含 `messaging`：

```powershell
cd D:\OpenWorker\openworker\.worktrees\chemclaw-design
$env:UV_CACHE_DIR='D:\OpenWorker\.chemclaw-dev\uv-cache'
$env:UV_PYTHON_INSTALL_DIR='D:\OpenWorker\.chemclaw-dev\uv-python'
uv pip install --python '.venv\Scripts\python.exe' -e '.[dev,messaging]'

cd surfaces\gui
npm.cmd install
npx.cmd playwright install chromium
```

`npm install` 本次报告 7 个依赖漏洞（3 moderate、3 high、1 critical）。Task 1 没有运行 `npm audit fix --force`，因为它可能引入破坏性升级；后续应单独审计，而不是混入品牌或中文化任务。

## 3. 每天查看源码界面

### 推荐：浏览器热更新

浏览器方式最适合高频修改 React 界面，不需要构建 EXE。必须先启动后端，再启动前端；Vite 启动时会从同一个状态目录读取本地认证 token。

终端 1：

```powershell
cd D:\OpenWorker\openworker\.worktrees\chemclaw-design
$env:COWORKER_STATE_DIR='D:\OpenWorker\.chemclaw-dev\state'
.\.venv\Scripts\openworker-server.exe --host 127.0.0.1 --port 8765
```

看到 `Uvicorn running on http://127.0.0.1:8765` 后，可验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8765/v1/health
```

终端 2：

```powershell
cd D:\OpenWorker\openworker\.worktrees\chemclaw-design\surfaces\gui
$env:COWORKER_STATE_DIR='D:\OpenWorker\.chemclaw-dev\state'
npm.cmd run dev
```

浏览器打开：

```text
http://localhost:1420
```

注意：

- 必须使用 `localhost`；当前 Vite 在 Windows 上监听 `::1`，`http://127.0.0.1:1420` 可能打不开。
- React/样式修改会自动热更新。
- Python 后端修改后通常要在终端 1 按 `Ctrl+C`，再重新启动后端。
- 正常停止两个服务的方法是分别在对应终端按 `Ctrl+C`。
- 如果一直显示 `Starting OpenWorker…`，先确认 8765 健康，再重启 Vite。后端启动失败或 Vite 在 token 生成前启动都会造成这个现象。
- Task 1 没有改界面，所以现在看到的仍是原 OpenWorker 英文界面。ChemClaw 品牌和默认中文属于 Task 2。

### 桌面程序源码模式

这个模式直接打开 Tauri 桌面窗口，也不构建安装包。它适合验证托盘、原生文件夹选择器、语音输入等原生能力；普通界面修改优先使用浏览器。

第一次运行会下载并编译数百个 Rust crate，属于一次性机器工作和本地磁盘缓存，不是反复消耗 Codex token。后续运行会复用 `src-tauri\target` 和 `%USERPROFILE%\.cargo`。

从 Windows 开始菜单打开 **Developer PowerShell for VS 2022**，再运行：

```powershell
$env:COWORKER_STATE_DIR='D:\OpenWorker\.chemclaw-dev\state'
$env:LIBCLANG_PATH='C:\Program Files\LLVM\bin'
cd D:\OpenWorker\openworker\.worktrees\chemclaw-design
New-Item -ItemType Directory -Force -Path 'surfaces\gui\src-tauri\binaries\sidecar' | Out-Null
cd surfaces\gui
npm.cmd run tauri -- dev
```

说明：

- `Developer PowerShell for VS 2022` 会设置 MSVC 的 `link.exe`、头文件和库路径；普通 PowerShell 不会自动获得这些变量。
- `LIBCLANG_PATH` 用于 `whisper-rs` 的 Rust 绑定生成。
- `binaries\sidecar` 被仓库 `.gitignore` 排除；生产构建脚本会把 PyInstaller 后端放入这里，源码开发只需要空占位目录，Tauri 会回退到 Worktree 根目录的 `.venv\Scripts\openworker-server.exe`。
- `npm.cmd run tauri -- dev` 只运行源码桌面窗口；`npm.cmd run tauri -- build` 才会进入安装包构建，本阶段不需要。

## 4. 测试命令与实测结果

### 后端

Windows 上不要使用 pytest 默认的 `%TEMP%\pytest-of-EDY`。这个目录曾由不同执行身份创建并产生 ACL 冲突，导致 889 个用例同时报 `PermissionError`。每次使用一个新的专用子目录：

```powershell
cd D:\OpenWorker\openworker\.worktrees\chemclaw-design
$env:COWORKER_STATE_DIR='D:\OpenWorker\.chemclaw-dev\state'
$env:NO_PROXY='127.0.0.1,localhost'
$env:no_proxy='127.0.0.1,localhost'
$env:Path=(($env:Path -split ';' | Where-Object { $_ -notmatch 'OpenAI\.Codex' }) -join ';')
$baseTemp='D:\OpenWorker\.chemclaw-dev\pytest-tmp\manual-YYYYMMDD-HHMM'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=$baseTemp -p no:cacheprovider
```

环境处理的原因：

- `NO_PROXY` 防止 Windows 系统代理把 FakeSlack 的 `127.0.0.1` 请求转成空的 502 响应。
- Codex 桌面进程会把一个普通用户无权执行的内置 `rg.exe` 放入子进程 PATH。测试时移除这一项后，OpenWorker 会正确使用 Python 搜索后备实现；单测实测 `1 passed`。
- `--basetemp` 绕开系统 pytest 临时目录的 ACL 污染。

最终原始全量运行（已安装 `dev,messaging`，使用专用 basetemp，但尚未加 NO_PROXY/PATH 清理）结果：

```text
879 passed, 10 failed, 1 skipped in 165.75s
```

补充根因验证：

```text
MCP 1.29.0 + coworker.server.manager 导入：PASS
FakeSlack 两条 502 失败加 NO_PROXY 后：2 passed
grep 移除 Codex 私有 rg 路径后：1 passed
```

使用上面的 `NO_PROXY`、干净 PATH 和专用 basetemp 后，受控全量结果为：

```text
880 passed, 9 failed, 1 skipped in 173.75s
```

这 9 条是当前 Windows/Codex 受控基线的已知失败；当前仍不得写成“后端全部通过”。

### GUI 单元测试

```powershell
cd D:\OpenWorker\openworker\.worktrees\chemclaw-design\surfaces\gui
npm.cmd test
```

结果：

```text
12 test files passed
68 tests passed
Duration 21.71s
```

### TypeScript/Vite 构建

```powershell
npm.cmd run build
```

结果：退出码 0，约 40.22 秒。存在两类非阻断警告：`api.ts` 同时被静态和动态导入，以及部分 chunk 超过 500 kB。

### Playwright E2E

```powershell
npm.cmd run e2e
```

结果：

```text
154 passed in 2.6m
```

这些用例使用网络层 mock，不需要真实模型、MCP 凭据或外网服务。

### Tauri/Rust

在 **Developer PowerShell for VS 2022** 中：

```powershell
$env:LIBCLANG_PATH='C:\Program Files\LLVM\bin'
cd D:\OpenWorker\openworker\.worktrees\chemclaw-design
New-Item -ItemType Directory -Force -Path 'surfaces\gui\src-tauri\binaries\sidecar' | Out-Null
cargo check --manifest-path 'surfaces\gui\src-tauri\Cargo.toml'
```

结果：退出码 0，最终缓存后完整检查约 1 分 45 秒。剩余一条原仓库警告：`src-tauri\src\lib.rs:691` 的变量不需要 `mut`。

## 5. 已知后端基线缺陷

下面是 OpenWorker 刚克隆基线在 Windows/Codex 环境中暴露的问题，不是 ChemClaw 界面改造造成的：

1. `test_workspace_trust_is_canonical_and_user_owned`
   - 普通 Windows 用户未启用“开发人员模式”时，无权创建符号链接（WinError 1314）。
   - 同一测试还假设 POSIX `0600` 权限位，Windows ACL 不能用该断言验证。
2. `test_standalone_server_token_file_is_user_only`
   - 断言 POSIX `0600` 权限位；Windows 应改为 ACL 验证。
3. `test_workspace_command_trust_controls_live_engine`
   - 活跃会话的持久 shell 占用工作目录，Windows 不允许此时重命名目录（WinError 32）；Linux 允许。
4. Relay 的若干测试把 `SLACK_API_URL` 指向 `127.0.0.1:9`，并要求 2 秒内完成消息分发。
   - 在本机 Windows 网络/防火墙环境中，连接不会足够快地失败，名称查询阻塞分发，造成 timeout。
   - 正确的测试修复方向是直接 stub 名称查询，不应把“无网络”模拟为一个真实 TCP 死端口。
5. FakeSlack 和跨层 UI 后端测试曾被 Windows 系统代理转成空 502；临时 `NO_PROXY=127.0.0.1,localhost` 已验证可解决。
6. Codex 内置但不可执行的 `rg.exe` 会使搜索测试返回 `WinError 5`；清理该 PATH 项后 Python fallback 已验证通过。
7. 受控全量中仍有 `test_one_hub_fans_out_to_both_adapters` 和 `test_ui_refresh_cross_cutting_e2e` 失败。
   - 两者都经过共享 relay/FakeSlack 异步链路；前者未及时 fan-out，后者在静音后仍多触发了一次 provider。
   - 这是当前上游异步测试/Windows 时序基线，不能靠增大固定 sleep 来掩盖，需要在单独检查点做事件边界诊断。

后续规则：

- 新任务必须确保没有新增失败。
- 不得静默删除或放宽产品断言来制造“全绿”。
- 建议在 Task 2 前增加一个小型 Windows 基线清理检查点：让 Unix 权限测试使用平台条件、让 Relay 测试真正无网络化，并决定活跃 workspace 目录锁的产品行为。

## 6. 凭据与开发数据规则

- `D:\OpenWorker\.chemclaw-dev\state` 只用于源码开发，不等同于未来正式安装程序的用户数据目录。
- 自动化测试不得写入真实 MCP、公司接口、OpenAI、Slack、GitHub、企查查或其他生产凭据。
- 测试 MCP 必须使用假凭据、mock 或本地测试服务。
- 真实 MCP 配置将来只在人工集成测试中使用，并应从测试数据库和日志中隔离。
- 当前浏览器预览显示 `No model` 属正常状态；Task 1 没有配置或复制任何真实模型密钥。
