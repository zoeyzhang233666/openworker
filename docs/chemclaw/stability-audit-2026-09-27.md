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

本轮尚未运行；上轮数字见 runtime-renewal-validation-2026-09-26.md，不能当本轮结果。
