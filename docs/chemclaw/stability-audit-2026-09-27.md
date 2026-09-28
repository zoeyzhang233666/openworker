# 现有能力加固：问题与验收台账

## 已核实的代码问题（尚未宣称运行修复）

| 编号 | 现象/证据 | 处理 |
| --- | --- | --- |
| S01 | subagents/runtime.py 将非 completed/interrupted 终态全部归 failed | 保留暂停/截断/阻塞状态 |
| S02 | profiles 存在 6/10/32 小轮数，run_foreground 超时强停 | 共享预算；等待超时不停止 |
| S03 | manager 子引擎没有绑定 checkpoint_sink/compaction_settings/恢复压缩状态 | 主/子复用保存恢复配置 |
| S04 | research 强制写报告，shared_workspace 继承父 AUTO；未知工具默认 read | 只读能力执行约束及明确工具分类 |
| S05 | 后台任务只有进程级 8 工作者，没有主任务共享预算 | 任务域预算与五路限制 |

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

## 测试结果与限制

第一步 34 passed；第二步组合 78 passed、GUI 11 passed、TypeScript 通过（包含重叠用例，不相加作为总数）。205 个 Python 测试文件的离线逐文件回归进行中，外部网络阻断，回环服务可用；尚未结案。上一轮进程中断后保留了 164 个文件的结果：1709 passed、63 failure、1 collection error、4 skipped；其余须补跑，失败须逐项分类处理，不能当作通过。

新增复现与处理：子引擎在新的事件循环中继续时，旧 asyncio.Event 仍绑定前一循环，导致“未返回完整终态”。现为每次运行创建独立停止信号，并让旧流绑定旧信号；真实小助手 follow-up 回归通过。输出分页原实现可能截去长块开头又越过整块，现使用 cursor+offset 无损回读。快结束子任务提前通知问题通过批次封口和持久化去重处理。

2026-09-27 在线克隆 GitHub 上游到忽略目录 `.tmp-upstream-stability`，HEAD=`5870585321e2cae0b2afbcd8903e14b63c959ac7`。完整相关文件差异索引已生成，具体候选适配/暂缓理由仍在审阅；不能称为已经同步整个上游。
