"""Versioned built-in Subagent profile registry."""

from __future__ import annotations

from .models import SubagentProfile


EXPLORER_INSTRUCTIONS = """你是只读代码探索子智能体，工作在用户工作区内。
默认用简体中文思考与回复；仅当用户或父任务明确要求其他语言时再切换。
通过搜索与阅读代码完成研究任务。不能写文件或运行 shell。最终消息是给父智能体的自包含报告：
直接作答，用 path:line 引用代码，只摘关键片段；找不到时说明搜过什么。"""

RESEARCHER_INSTRUCTIONS = """你是 ChemClaw 研究子智能体。
默认用简体中文思考与回复；仅当用户或父任务明确要求其他语言时再切换。
用结构化化工/企业/行情工具与网页来源解答分派问题。直接调用可用的行情工具（含国内期货
lookup_cn_futures_* 与已投影的 chem-data-hub 现货工具）。主张可追溯，区分事实与推断；
来源不可用时如实报告，禁止编造替代。UTF-8 工作区文本优先用 grep/read_file——不要发明带中文
模式的 PowerShell 单行。最终对话气泡前，先用 write_file/edit_file 在共享工作区写简明报告文件，
再只回给父智能体一段短摘要并附产物路径（过长最终气泡有上游拒答风险）。不要进入计划模式，
不要调用 propose_plan，不要声称写工具被阻断或必须等待计划审批。不要嵌套启动子智能体。"""

MARKET_REPORTER_INSTRUCTIONS = """你是 ChemClaw 化工市场报告后台工作流。
默认用简体中文。复用父轮已经拿到的价格与资讯证据，只补充会影响结论的缺口；不要调用 shell、
不要写临时解析脚本、不要读取大原始回包、不要启动子智能体。化工现货以 chem-data-hub 为准，
无数据时如实标注，不得用期货或 Yahoo 冒充。将完整报告写到共享工作区的 report.md，包含数据
周期、价格表/趋势、驱动、风险、来源与数据限制；随后只返回一段短摘要和报告路径。"""

WORKER_INSTRUCTIONS = """你是 ChemClaw 工作执行子智能体，拥有独立上下文。
默认用简体中文思考与回复；仅当用户或父任务明确要求其他语言时再切换。
在共享工作区完成有界任务，遵守仓库说明，返回含改动文件与验证的简明自包含报告。
你没有继承的审批豁免：一切有后果的工具仍走 ChemClaw 正常 PermissionEngine 与人工审批。"""


class SubagentProfileRegistry:
    def __init__(self, profiles: tuple[SubagentProfile, ...] | list[SubagentProfile]):
        self._profiles: dict[str, SubagentProfile] = {}
        for profile in profiles:
            if profile.id in self._profiles:
                raise ValueError(f"duplicate subagent profile id: {profile.id}")
            self._profiles[profile.id] = profile

    def get(self, profile_id: str) -> SubagentProfile | None:
        return self._profiles.get(profile_id)

    def require(self, profile_id: str) -> SubagentProfile:
        profile = self.get(profile_id)
        if profile is None:
            raise ValueError(f"unknown subagent profile: {profile_id}")
        return profile

    def list(self) -> tuple[SubagentProfile, ...]:
        return tuple(self._profiles.values())


def builtin_subagent_profiles() -> SubagentProfileRegistry:
    return SubagentProfileRegistry(
        [
            SubagentProfile(
                id="explore",
                title="代码探索",
                description="只读搜索和理解多文件代码。",
                agent_id="code",
                mode="plan",
                max_turns=10,
                tool_allowlist=(
                    "grep",
                    "read_file",
                    "list_files",
                    "git_log",
                    "git_status",
                    "git_diff",
                ),
                isolation="read_only",
                background=True,
                instructions=EXPLORER_INSTRUCTIONS,
            ),
            SubagentProfile(
                id="research",
                title="研究",
                description="联网与结构化化工/行情研究，可写共享工作区报告。",
                agent_id="cowork",
                mode="interactive",
                max_turns=32,
                tool_allowlist=(
                    "grep",
                    "read_file",
                    "list_files",
                    "write_file",
                    "edit_file",
                    "replace_in_file",
                    "web_search",
                    "web_fetch",
                    "lookup_chemical_identity",
                    "lookup_legal_entity",
                    "validate_eu_vat",
                    "lookup_fx_rate",
                    "lookup_wikipedia",
                    "lookup_yahoo_ohlc",
                    "lookup_cn_futures_quote",
                    "lookup_cn_futures_ohlc",
                    "lookup_cn_futures_minute",
                    "lookup_cn_futures_l1",
                    "calculate_cn_futures_margin",
                    "search_huagongshe",
                    "lookup_huagongshe_chemical",
                    "search_tenders",
                    "search_sam_opportunities",
                    "lookup_trade_flow",
                ),
                disallowed_tools=(
                    "start_subagent",
                    "explore",
                    "background_task_send",
                ),
                mcp_servers=("chem-data-hub", "chem-biz-scope"),
                isolation="shared_workspace",
                background=True,
                instructions=RESEARCHER_INSTRUCTIONS,
            ),
            SubagentProfile(
                id="market_report",
                title="化工市场报告",
                description="有界地补全市场报告并写入 report.md。",
                agent_id="cowork",
                mode="interactive",
                max_turns=6,
                tool_allowlist=(
                    "read_file",
                    "list_files",
                    "write_file",
                    "edit_file",
                    "web_search",
                    "web_fetch",
                ),
                disallowed_tools=(
                    "run_shell",
                    "start_subagent",
                    "explore",
                    "background_task_send",
                ),
                mcp_servers=("chem-data-hub",),
                isolation="shared_workspace",
                background=True,
                instructions=MARKET_REPORTER_INSTRUCTIONS,
            ),
            SubagentProfile(
                id="worker",
                title="工作执行",
                description="在共享工作区执行需要审批的读写任务。",
                agent_id="code",
                mode="interactive",
                max_turns=32,
                tool_allowlist=None,
                disallowed_tools=(
                    "start_subagent",
                    "explore",
                    "background_task_send",
                ),
                isolation="shared_workspace",
                background=True,
                instructions=WORKER_INSTRUCTIONS,
            ),
        ]
    )
