"""Channel delivery detection helpers (D-202)."""

from __future__ import annotations

from typing import Any

CHANNEL_CONNECTORS = frozenset(
    {"wecom", "weixin", "feishu", "dingtalk", "telegram", "slack"}
)

CHANNEL_DENIED_TOOLS = frozenset(
    {
        "run_shell",
        "run_terminal_cmd",
        "load_skill",
        "search_skills",
        "todo_write",
        "start_subagent",
        "explore",
        "background_task_status",
        "background_task_output",
        "background_task_send",
        "background_task_stop",
        "background_task_gather",
    }
)


def is_channel_delivery_source(source: dict[str, Any] | None) -> bool:
    """True when a turn is tied to an outbound messaging Channel address."""
    if not source:
        return False
    target = str(source.get("target") or "").strip()
    connector = str(source.get("connector") or "").strip().lower()
    return bool(target and connector in CHANNEL_CONNECTORS)


def is_channel_user_source(source: dict[str, Any] | None) -> bool:
    """Inbound user message from a messaging Channel (not background/system)."""
    if not is_channel_delivery_source(source):
        return False
    kind = str(source.get("kind") or "").lower()
    if kind in {"scheduled", "schedule", "self_wake", "wake", "subagent_cohort_complete"}:
        return False
    return True
