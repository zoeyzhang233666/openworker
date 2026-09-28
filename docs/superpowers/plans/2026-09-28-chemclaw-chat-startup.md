# 新对话启动修复实施记录

规格：[启动与 MCP 隔离](../specs/2026-09-28-chemclaw-chat-startup-design.md)。基线 2f879bf；不动既有未提交修改。

- [x] 离线复现 MCP 初始化阻塞普通聊天、跨服务排队与取消悬空。
- [x] 共用 MCP 准备入口限时等待/后台补挂，连接独立与生命周期清理。
- [x] 回归聊天、MCP 权限/连接、工具发现、渠道和模型选择，记录旧失败。
- [x] 更新状态、证据及剩余未验证项，小提交。

本次不调用付费模型、不重启正在运行的开发程序、不构建或安装正式版。

## 2026-09-28 实施结果

1. **原问题**：WebSocket 在接收消息前逐个等待 MCP；连接管理器跨服务持锁；取消等待者会取消共享 ready，连接任务取消又可能不结束 ready。初始 7 条行为测试全部失败，包含真实 WebSocket/真实引擎加模拟 Provider 的新对话问候。
2. **现在行为**：共用准备入口最多等 250ms，随后返回；服务器独立连接，同服务器共享尝试，自动连接 15 秒到期结算并取消。迟到连接按最新配置和授权再检查后补挂。任务结束、重载时清理准备任务；重配端点不能复用旧连接，需要现有“重新加载”操作。工具目录读取使用快照，避免边补挂边遍历失败。连接页显示“正在连接”并刷新至终态。
3. **验证**：最终 MCP/启动四文件 **42 passed**（新增启动隔离 13 项）；另渠道投递、会话模型、工具发现、基础联网、工具权限五文件 **28 passed**，两组合计 **70 passed**。GUI MCP/模型/语言 **8 passed**。均为离线/模拟服务，没有调用真实模型或发送真实渠道消息。初轮 7 failed 是修复前的复现，不计入最终失败。
4. **扩展结果**：`test_server` 37 passed / 7 failed，`test_connections` 7 passed / 1 failed；8 项均与已保存全仓基线同名同类，未出现新增失败，不将其标记通过：
   - `test_artifact_read_folder_returns_listing`、`test_artifact_read_rejects_path_escape`：旧英文错误文案断言与当前错误码不同。
   - `test_standalone_server_token_file_is_user_only`：Windows 文件 mode 与 POSIX 权限位断言不同，未以此证明 ACL 正确。
   - `test_ws_error_persists_notice_and_retry_reruns`：尾部检查点 notice 与旧“最后一条必是 assistant”断言冲突。
   - `test_workspace_command_trust_controls_live_engine`、`test_always_allow_grants_survive_restart`：测试假定交互审批，当前默认完全访问，需单独整理。
   - `test_google_one_click_paused_but_manual_alive`：中文错误与旧英文断言不同。
   - `test_muted_connector_not_delivered`：既有渠道投递测试没有得到监听会话结果，仍待独立排查，不能当作已修。
5. **未验证**：现场的 deepseek-v4.1-flash 新会话与此阻塞路径一致，但未在运行进程抓取调用栈，未执行真实模型请求；不宣称模型接口兼容性、网关断流或 MCP 服务端网络已修复。后端需获准重启或在隔离实例真实复测后才能证明用户现场改善。

未修改模型、密钥、现有 MCP 配置、用户聊天记录。正在运行的后端尚未加载本次 Python 修改。真实模型/账号额度、运行环境切换、正式发布仍遵守已批准阶段 6 的单独确认。

最终静态检查：GUI `npx tsc --noEmit`、`git diff --check` 通过。上面所有计数按文件去重；扩展的 8 项失败保留在加固待办，不能用于发布放行。
