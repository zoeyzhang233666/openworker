"""Versioned built-in Subagent profile registry."""

from __future__ import annotations

from .models import SubagentProfile


EXPLORER_INSTRUCTIONS = """你是只读代码探索子智能体，工作在用户工作区内。
默认用简体中文思考与回复；仅当用户或父任务明确要求其他语言时再切换。
通过搜索与阅读代码完成研究任务。不能写文件或运行 shell。最终消息是给父智能体的自包含报告：
直接作答，用 path:line 引用代码，只摘关键片段；找不到时说明搜过什么。"""

RESEARCHER_INSTRUCTIONS = """你是 ChemClaw 只读研究小助手。默认使用简体中文。
只查询资料和阅读授权文件，不写文件、不执行命令、不发消息、不修改外部数据、不创建小助手。
返回自包含的研究结果：结论、证据与来源、尚未解决的问题、需要主助手执行的操作。
没有确认只读性质的工具交回主助手；不要声称已经完成未执行的写入。程序会保存你的完整结果，
主助手可以分段回读；不必写 report.md。遵守父任务的目录、联网和搜索限制。
无需申请执行计划或额外权限，遇到限制说明缺口并返回已有结果。"""

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
        return tuple(p for p in self._profiles.values() if p.enabled)


def builtin_subagent_profiles() -> SubagentProfileRegistry:
    return SubagentProfileRegistry(
        [
            SubagentProfile(
                id="explore",
                title="代码探索",
                description="只读搜索和理解多文件代码。",
                agent_id="code",
                mode="plan",
                max_turns=300,
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
                description="只读资料研究，返回证据和结论，由主助手交付报告。",
                agent_id="cowork",
                mode="plan",
                max_turns=300,
                tool_allowlist=None,
                disallowed_tools=(
                    "start_subagent",
                    "explore",
                    "background_task_send",
                ),
                mcp_servers=(),
                isolation="read_only",
                background=True,
                instructions=RESEARCHER_INSTRUCTIONS,
            ),
            SubagentProfile(
                id="market_report",
                enabled=False,
                title="化工市场报告",
                description="有界地补全市场报告并写入 report.md。",
                agent_id="cowork",
                mode="plan",
                max_turns=300,
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
                isolation="read_only",
                background=True,
                instructions=MARKET_REPORTER_INSTRUCTIONS,
            ),
            SubagentProfile(
                id="worker",
                enabled=False,
                title="工作执行",
                description="在共享工作区执行需要审批的读写任务。",
                agent_id="code",
                mode="plan",
                max_turns=300,
                tool_allowlist=None,
                disallowed_tools=(
                    "start_subagent",
                    "explore",
                    "background_task_send",
                ),
                isolation="read_only",
                background=True,
                instructions=WORKER_INSTRUCTIONS,
            ),
        ]
    )
