# D-165 执行日志

- 日期：2026-08-19
- Worktree：`D:\OpenWorker\openworker\.worktrees\chemclaw-clean`
- 状态：IMPLEMENTED / LIVE PASS
- 起始分支：`chemclaw-clean`
- 用户已有 dirty：D-161—D-164、CN 行情/Chart/安装包记录等；本任务不重置、不吸收无关改动。
- 提交策略：重叠 dirty 文件不自动整文件提交；每个 Gate 记录测试、diff 与 rollback switch。

## Gate 1

- 状态：PASS
- Rollback：`request_routing_enabled=false`
- 实现：`coworker/turn_planner.py`；`build_engine` 为真实 SessionManager 入口注入 planner；`run/retry/resume` 共用不可变计划。
- Reasoning：Provider 请求 `reasoning_mode` 与界面 `show_reasoning` 解耦；FAST 只在能力矩阵明确支持时发送关闭参数，上游有 reasoning 即广播。
- PASS：路由矩阵、retry 复用、durable resume/附件/source/Persona/Skill/Plan/后台守卫；本地 GUI WebSocket reasoning/text delta 在最终消息前到达。
- NEW FAIL：none。

## Gate 2

- 状态：PASS / CANDIDATE ON
- Rollback：`prompt_projection_enabled=false` / `tool_projection_enabled=false`
- 实现：FAST/KNOWLEDGE direct prompt；VERIFIED/行情、定向 Agent、工作区与可视化 prompt profiles；新会话 `_prompt_policy_version=1`，旧会话 legacy；能力包投影；`search_skills` 元数据发现。
- 离线门禁：FAST system prompt <4k 字符、token estimate <=4k、tools=None、skill count=0；canonical 完整 prompt 不被改写，重载后仍投影。
- Legacy schema fixture：新增 `search_skills` 后已重采，projection OFF parity 通过。
- NEW FAIL：none。

## Gate 3

- 状态：PASS
- 核心新增：`30 passed`（TurnPlanner、prompt profiles、新旧会话、retry、pending guard、reasoning、权限、WS、instrumentation、skills）。
- Router/Profile/Projection 聚焦复跑：`96 passed`；另 1 项仅因 Windows 未授予 symlink 权限（WinError 1314）失败。
- 能力保留/自动化/Stop/durable 聚焦复跑：`37 passed`；1 项因沙箱不可写 `C:\Users\EDY\OpenWorker\__task__*`，1 项为已记录的 AUTO 模式 approval 既有失败。
- Memory + Skill：`135 passed, 1 skipped`。
- Compaction：`43 passed`。
- Provider/Router/Profile/Projection：`172 passed`；另 7 项均因 Windows 沙箱临时 `secrets.json.tmp` ACL 不可写失败。
- MCP：`21 passed`；另 8 项均为相同临时 secrets ACL 环境失败。
- 控制/自动化/Stop/权限：`139 passed`；2 项因沙箱不可写 `C:\Users\EDY\OpenWorker\__task__*`；symlink 用例因 WinError 1314 单独 deselect。
- GUI Chart：`58 passed`；`npm run build` PASS，仅既有 dynamic-import/chunk-size warnings。
- 本地 GUI WebSocket：PASS，FAST `tools=None`，reasoning/text delta 在 complete 前到达。
- Live：用户明确授权后完成 GUI WebSocket → SessionManager → ApiHub CN `deepseek-v4-flash`。5 次全新问候全部 `FAST_CHAT`，实际 prompt 均为 85 tokens，tools=0、skills=0；TTFT P50=2.88s、P95=6.88s。长答 prompt=103 tokens、正文 delta=745、首包=2.76s。6 个主回答调用全部 `direct`，complete fallback=0；另有 6 次非流式调用均为每个新会话的自动标题生成。上游 reasoning delta=0，不伪造思考。夹具：`docs/chemclaw/fixtures/apihub_cn_d165_gui_probe.json`。
- NEW FAIL：none identified。
