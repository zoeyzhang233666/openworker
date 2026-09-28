"""Canonical execution state derived from durable engine progress, not answer text."""
PAUSED = frozenset({"budget_paused", "truncated", "blocked"})
ACTIVE = frozenset({"queued", "running", "waiting_user", "waiting_children"})


def execution_state(messages, *, waiting_user=False):
    if waiting_user:
        return "waiting_user", "等待人工处理"
    for message in reversed(messages):
        kind = message.get("kind")
        if kind in PAUSED | {"waiting_children"}:
            return kind, message.get("text") or ""
        if kind in {"error", "interrupted"}:
            return ("failed" if kind == "error" else "cancelled"), message.get("text") or ""
        if kind == "checkpoint":
            reason = message.get("reason")
            if reason == "completed":
                return "completed", ""
            if reason in PAUSED:
                return reason, ""
            return "running", ""
        if message.get("role") == "assistant":
            if message.get("finish_reason") == "length":
                return "truncated", "输出达到长度限制"
            if not message.get("tool_calls") and message.get("finish_reason") == "stop":
                return "completed", ""
            return "running", ""
        if message.get("role") in {"tool", "user"}:
            return "running", ""
    return "queued", ""
