"""Model tools for SubagentRuntime and unified background task control."""

from __future__ import annotations

from typing import Callable, Optional

import aisuite as ai

from .runtime import SubagentRuntime


def subagent_tools(
    runtime: SubagentRuntime,
    *,
    owner_session_id: str,
    workspace: str,
    parent_trace_id: Callable[[], str | None] | None = None,
    parent_market_snapshot: Callable[[], dict[str, str]] | None = None,
) -> list:
    def _parent_trace_id() -> str | None:
        return parent_trace_id() if parent_trace_id is not None else None

    def _parent_market_meta() -> dict[str, str]:
        if parent_market_snapshot is None:
            return {}
        try:
            return dict(parent_market_snapshot() or {})
        except Exception:
            return {}

    def start_subagent(
        task: str,
        profile: str = "research",
        background: bool = True,
        description: Optional[str] = None,
    ) -> dict:
        """把有界任务委派给已注册的子智能体 Profile。默认 profile 为 research（网页/化工/行情）。
        只读代码探索传 profile=\"explore\"；共享工作区执行传 profile=\"worker\"。
        task 与 description 用简体中文书写。background=true 时继续本侧工作，整批完成后运行时
        会注入汇合通知；其间只用 background_task_gather/status/output 短窥。background=false
        会等待最终报告。Profile 由平台定义，不能额外提权。"""
        try:
            profile_spec = runtime.profiles.require(profile)
        except ValueError as exc:
            return {"error": str(exc)}
        if background and not profile_spec.background:
            return {"error": f"subagent profile '{profile}' does not allow background runs"}
        market_meta = _parent_market_meta()
        if background:
            record = runtime.start(
                task=task,
                profile_id=profile,
                owner_session_id=owner_session_id,
                workspace=workspace,
                description=description,
                parent_trace_id=_parent_trace_id(),
                join_cohort=True,
                metadata=market_meta,
            )
            return record.model_dump()
        return runtime.run_foreground(
            task=task,
            profile_id=profile,
            owner_session_id=owner_session_id,
            workspace=workspace,
            description=description,
            parent_trace_id=_parent_trace_id(),
            metadata=market_meta,
        ).model_dump()

    def background_task_status(task_id: str) -> dict:
        """查询后台任务状态（含子智能体）。只读短窥，不要用长阻塞等待代替汇合通知。"""
        record = runtime.task_manager.get(task_id, owner_session_id=owner_session_id)
        if record is None:
            return {"error": f"unknown task: {task_id}"}
        return record.model_dump()

    def background_task_output(task_id: str, cursor: int = 0) -> dict:
        """读取后台任务自 cursor 起的增量输出。用于短窥进展，不要当作主等待手段。"""
        try:
            return runtime.task_manager.read_output(
                task_id, owner_session_id=owner_session_id, cursor=cursor
            ).model_dump()
        except ValueError as exc:
            return {"error": str(exc)}

    def background_task_send(task_id: str, message: str) -> dict:
        """向仍在运行的后台 Agent 任务续发一条消息。message 用简体中文。"""
        try:
            return runtime.task_manager.send_message(
                task_id, message, owner_session_id=owner_session_id
            ).model_dump()
        except ValueError as exc:
            return {"error": str(exc)}

    def background_task_stop(task_id: str) -> dict:
        """请求后台任务收尾停止（含子智能体）：先催写部分报告，超时后再强制停止。

        用户在界面点「停止」会立刻硬停；本工具属于智能体触发，走收尾模式。
        """
        try:
            return runtime.task_manager.stop(
                task_id, owner_session_id=owner_session_id, mode="wrap_up"
            ).model_dump()
        except ValueError as exc:
            return {"error": str(exc)}

    def background_task_gather(
        task_ids: list[str], timeout_seconds: int = 60
    ) -> dict:
        """短窥 / 读取后台任务终态报告（默认超时 60 秒）。

        并行研究批次的最终汇合由运行时在 cohort 完成时注入——不要把长阻塞 gather 当作主等待。
        超时上限 1800 秒。
        """
        try:
            records = runtime.task_manager.gather(
                task_ids,
                timeout=max(0, min(int(timeout_seconds), 1800)),
                owner_session_id=owner_session_id,
            )
            reports = []
            for record in records:
                page = runtime.task_manager.read_output(
                    record.id,
                    owner_session_id=owner_session_id,
                    max_chars=50_000,
                )
                reports.append(
                    {
                        "task": record.model_dump(),
                        "report": "".join(
                            c.text for c in page.chunks if c.stream == "assistant"
                        ),
                    }
                )
            return {"tasks": reports}
        except ValueError as exc:
            return {"error": str(exc)}

    defs = [
        (start_subagent, "search", "low"),
        (background_task_status, "task", "low"),
        (background_task_output, "task", "low"),
        (background_task_send, "task", "low"),
        (background_task_stop, "task", "low"),
        (background_task_gather, "task", "low"),
    ]
    return [
        ai.tool(
            fn,
            metadata=ai.ToolMetadata(
                category=category,
                risk_level=risk,
                capabilities=["subagent" if fn is start_subagent else "background_task"],
                requires_approval=False,
            ),
        )
        for fn, category, risk in defs
    ]


def explore_tool(
    runtime: SubagentRuntime,
    *,
    owner_session_id: str,
    workspace: str,
    parent_trace_id: Callable[[], str | None] | None = None,
):
    def explore(task: str) -> dict:
        """把宽泛、只读的代码研究任务委派给隔离的 explore 子智能体，并返回其自包含最终报告。
        task 用简体中文书写。"""
        result = runtime.run_foreground(
            task=task,
            profile_id="explore",
            owner_session_id=owner_session_id,
            workspace=workspace,
            parent_trace_id=(parent_trace_id() if parent_trace_id is not None else None),
        )
        if not result.report:
            return {"error": result.error or f"explorer stopped: {result.status}"}
        payload = {"report": result.report}
        if result.status != "completed":
            payload["note"] = f"explorer stopped early ({result.status})"
        return payload

    return ai.tool(
        explore,
        metadata=ai.ToolMetadata(
            category="search",
            risk_level="low",
            capabilities=["search"],
            requires_approval=False,
        ),
    )
