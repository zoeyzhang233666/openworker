# 现有能力加固：问题与验收台账

## 已核实的代码问题（尚未宣称运行修复）

| 编号 | 现象/证据 | 处理 |
| --- | --- | --- |
| S01 | subagents/runtime.py 将非 completed/interrupted 终态全部归 failed | 保留暂停/截断/阻塞状态 |
| S02 | profiles 存在 6/10/32 小轮数，run_foreground 超时强停 | 共享预算；等待超时不停止 |
| S03 | manager 子引擎没有绑定 checkpoint_sink/compaction_settings/恢复压缩状态 | 主/子复用保存恢复配置 |
| S04 | research 强制写报告，shared_workspace 继承父 AUTO；未知工具默认 read | 只读能力执行约束及明确工具分类 |
| S05 | 后台任务只有进程级 8 工作者，没有主任务共享预算 | 任务域预算与五路限制 |
| S06 | Windows grep 把 `D:` 解析为文件名 `D`，单文件输出缺路径 | 已适配上游 NUL 分隔，UTF-8 解码；搜索回归 9 passed |
| S07 | 内置种入和能力包复制整个源目录，开发缓存进入用户技能目录 | 共同过滤缓存并验证 ZIP；9 文件 96 passed / 1 skipped |
| S08 | 能力包覆盖先删除旧目录再复制，复制失败无法保留旧版 | 代码检查发现，尚待失败注入与事务式安装修复 |
| S07 | Skill 初始化及能力包复制源目录中的开发字节码 | 三种入口共用缓存过滤；安装及资源回归 96 passed / 1 skipped |
| S08 | 能力包覆盖安装先删除已有目录再复制，复制失败可能丢失原版本 | 代码检查发现，待补充故障回退验证与修复 |
| S09 | 用户反馈基础联网搜索只能经 multi-search-engine Skill 使用 | 待核实注册、发现及执行链路；基础联网不应以 Skill 加载为前提 |

## 功能验收目录

| 范围 | 入口/测试依据 | 当前状态 |
| --- | --- | --- |
| 对话/恢复/压缩/模型 | engine、manager、providers；runtime/compaction/provider 测试 | 上轮离线通过，本轮待回归 |
| 小助手/后台 | subagents、background_tasks；subagent/runtime/cohort 测试 | 本轮重点 |
| MCP/权限 | mcp、permissions、risk；mcp/permissions 测试 | 待回归与只读新增 |
| Skill/Agent | skills、personas、能力包安装；skills/persona 测试 | 待回归 |
| 渠道/图表 | channels、rich_output、GUI ChartBlock | 待离线与隔离真机 |
| 定时任务 | automation、task 调度 | 待回归 |
| 安装/升级 | packaging、build_info、会话存储 | 静态/离线检查；不正式构建 |

## 上游台账

源仅 https://github.com/andrewyng/openworker 。规划时固定 SHA 5870585321e2cae0b2afbcd8903e14b63c959ac7；实施时再次验证。
需要对照整个相关模块，不以 cc2b921 之后 18 个提交代替完整差异。
沙箱仅评估 Windows/依赖/目录/命令/凭据/渠道/性能/打包，不安装或接入。

| 候选（固定快照 5870585） | 本地影响与处理 | 验收与回退 |
| --- | --- | --- |
| `coworker/sandbox/runner/tools_grep.py` 的 `--null` / `--with-filename` | 同样存在 Windows 盘符误解析；仅适配到本地 `tools/search.py`，保留目录权限与工具接口，另指定 UTF-8 | 9 项搜索回归通过；独立提交可回退，无数据迁移 |

## 测试结果与限制

第一步 34 passed；第二步组合 78 passed、GUI 11 passed、TypeScript 通过；第三步定时任务组合 40 passed、新增恢复 4 passed、GUI 12 passed（包含重叠用例，不相加作为总数）。全仓初轮 205 个 Python 测试文件已补齐：2052 passed、74 failure、1 collection error、4 skipped。审阅过的测试在 Python 网络审计钩子下执行，外部连接阻断、回环服务可用；这不是任意子进程安全沙箱。结果按文件保存在 `.tmp-stability-offline/results.json` 及日志/XML。失败正逐项分类处理，尚未结案；初轮部分文件运行早于定时任务修复，不能作为最终候选版结果。

新增复现与处理：子引擎在新的事件循环中继续时，旧 asyncio.Event 仍绑定前一循环，导致“未返回完整终态”。现为每次运行创建独立停止信号，并让旧流绑定旧信号；真实小助手 follow-up 回归通过。输出分页原实现可能截去长块开头又越过整块，现使用 cursor+offset 无损回读。快结束子任务提前通知问题通过批次封口和持久化去重处理。

2026-09-27 在线克隆 GitHub 上游到忽略目录 `.tmp-upstream-stability`，HEAD=`5870585321e2cae0b2afbcd8903e14b63c959ac7`。完整相关文件差异索引已生成，具体候选适配/暂缓理由仍在审阅；不能称为已经同步整个上游。
