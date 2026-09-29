"""User-selected execution depth, independent of business routing and permissions."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchPolicy:
    size: int
    reserve: int
    reasoning: str


POLICIES = {
    "fast": ResearchPolicy(6, 1, "low"),
    "deep": ResearchPolicy(300, 15, "high"),
}


def validate_depth(value: str) -> str:
    if not isinstance(value, str) or value not in POLICIES:
        raise ValueError("研究深度只能选择快速或深度探索")
    return value


def depth_guidance(depth: str, *, used: int, remaining: int, finalizing: bool) -> str:
    if finalizing:
        return ("快速模式进入最终交付轮，本轮不调用工具。直接交付能满足用户核心问题的完整答案：结论在前，必要依据和来源在后，明确证据范围与重要局限。"
                "不要只复述计划、搜索过程或说额度耗尽；不要因可选细节没查完而放弃已有结论。若必需操作或产物确实未完成，明确指出未完成项，不得声称已执行或已生成；不编造缺失事实。")
    if depth == "fast":
        strategy = (
            "从第一轮就设计快速完成路径，在内部先确定：①用户最需要的结论/产物和最小完整交付；"
            "②已有材料能覆盖什么，哪些事实必须核验；③最短的取证/执行路径及何时停止。不要额外调用模型来写计划，不必向用户展示内部规划。"
            "简单问题直接流式回答。需要检索时优先一个覆盖核心问题的可靠直接来源，合并独立查询/读取；只有关键事实缺失、矛盾或过期才补查。"
            "不要先铺开深研目录、全面搜索再等额度截断；不追求来源数量，不做无关背景拓展，不默认委派。"
            "需要文件或操作时从开始就为生成、验证与交付留出步骤；普通概览默认在对话中交付，图表优先现有内联能力，不临时写绘图脚本。"
        )
        if used > 0:
            strategy = "沿用最小完整交付目标，复用已有证据，不扩展深研目录。生成/验证/交付优先于补可选资料；不以来源数量为目标，不编造缺失事实。"
        phase = "已进入综合阶段：核心问题有依据就立即交付，仅补会改变结论的缺口；可选细节留作后续扩展。" if used >= 2 else ""
        return (f"当前为快速模式，目标是尽早给出有依据的最小完整答案。{strategy}{phase}"
                f"主/子助手共享本段额度，含当前剩余 {remaining} 轮，最后 1 轮只整理。额度是兜底，不是用满目标。必要联网/MCP及权限审批仍可使用。")
    return "当前为深度探索。围绕关键问题收集证据、核对矛盾并及时综合；已有直接证据足够时结束，不为凑来源数扩展。无需强制委派。"
