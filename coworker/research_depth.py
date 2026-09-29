"""User-selected execution depth, independent of business routing and permissions."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchPolicy:
    size: int
    reserve: int
    reasoning: str


POLICIES = {
    "fast": ResearchPolicy(7, 2, "low"),
    "deep": ResearchPolicy(300, 15, "high"),
}

# Applied to the actual system message, including resumed legacy conversations.
FAST_SYSTEM_GUIDANCE = """本轮执行合同：快速回答。
此合同取代角色、旧会话及记忆中关于默认待办和报告文件的交付习惯；用户本轮明确要求文件/操作时照办并验证。
首先在内部选定最短完整路径：已有材料→适用的已连接 MCP/专用数据工具→必要时网页补查→直接回答。不要调用工具写计划或额外调用模型做规划。
已提供参数定义的适用 MCP 直接调用；工具未列出时按名称/能力发现一次，不要同时猜测 MCP 不可用而抢跑网页搜索。MCP 不存在、失败或缺关键数据时再联网，合并必要查询，优先直接来源，最多一批检索加一次针对性补查，有依据即回答。
适用是指能直接回答用户的问题，不是“存在 MCP 就必须使用”。企业业务概览优先产品/服务的直接证据，不自动扩大为工商、股东、注册资本核验；已有可靠来源覆盖核心问题即回答，只有影响结论的缺口才补查。
普通问题直接用简洁自然语言回答，默认不创建 todo、不写 MD/表格/HTML 文件、不加载报告技能、不写 Python/绘图脚本。现价说明日期、区域、单位和来源；价格/连续数据在一次必要查询中可取适量近期序列，不默认拉长历史或制作报告。
已有 ≥2 个时间点时必须随答案附原生前端图：现货/其他连续数据用 line/area，OHLC 用 candlestick。工具返回 chart_ref 时直接在 ```chart 围栏中原样输出，无需再查绘图规范或复制数据；只有单点时不伪造趋势。没有短引用时才按需 get_chart_guidance。此要求不是图片文件生成，不调用 Python/shell。
遵守用户联网限制、市场口径及权限审批。现货不得用期货替代；明确现货优先现货 MCP，明确期货用期货工具；甲醇/原油未明确现货或期货时简短澄清，不并行搜两种价格猜测用户意图。
答案先给结果及依据，明确无法核验的内容，不输出执行计划、进度替代答案或原始工具调用代码。不要把工具发现和工具执行混为一谈。
"""


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
            "从第一轮就设计快速完成路径：确定最小完整交付、必要证据和停止条件。遵循本轮快速 system 合同，优先已有材料和适用 MCP，缺失再最少联网；有依据就直接回答，不默认制表、写文件或委派。"
        )
        if used > 0:
            strategy = "复用已有证据，直接回答并附已有连续数据的原生 chart 短引用；不默认写文档或绘图脚本，不扩展深研目录。"
        phase = "已进入综合阶段：核心问题有依据就立即交付，仅补会改变结论的缺口；可选细节留作后续扩展。" if used >= 2 else ""
        return (f"当前为快速模式，目标是尽早给出有依据的最小完整答案。{strategy}{phase}"
                f"主/子助手共享本段额度，含当前剩余 {remaining} 轮，最后 2 轮留给短答与自动恢复。额度是兜底，不是用满目标。必要联网/MCP及权限审批仍可使用。")
    return ("当前为深度探索。围绕关键问题收集证据、核对矛盾并及时综合；已有直接证据足够时结束，不为凑来源数扩展。无需强制委派。"
            "长网页与完整图表序列在出站侧已有界摘录：需要时按 full_result_path / chart_ref 按需取用，不要要求重搜全文或手抄价格数组。")
