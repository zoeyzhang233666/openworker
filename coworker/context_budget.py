"""Budget the complete next provider request, including schemas and new tool results."""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any


def estimate(value: Any) -> int:
    text = json.dumps(value, ensure_ascii=False, default=str)
    # CJK and structured payloads need a conservative fallback, not escaped JSON chars/4.
    return math.ceil(sum(1 if ord(c) < 128 else 6 for c in text) / 4)


@dataclass(frozen=True)
class ContextBudget:
    window: int
    output_reserve: int
    safety: int
    input_limit: int
    trigger: int
    target: int
    messages_tokens: int
    schema_tokens: int
    fixed_tokens: int
    estimated_input: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


def budget_request(messages: list[dict], tools: list[dict] | None, *, window: int,
                   max_output: int, threshold: float, cap: int,
                   last_actual: int | None = None, last_estimate: int | None = None) -> ContextBudget:
    output = min(max(1, max_output), max(1, window // 2))
    safety = min(2_048, max(1, window // 50))
    limit = max(1, window - output - safety)
    trigger = max(1, min(int(window * threshold), cap, limit))
    schema = estimate(tools) if tools else 0
    history = estimate(messages)
    current = history + schema
    if last_actual is not None and last_estimate is not None:
        current = max(current, last_actual + current - last_estimate)
    fixed = schema + estimate([m for m in messages if m.get("role") == "system"])
    return ContextBudget(window, output, safety, limit, trigger,
                         max(1, min(limit // 2, trigger // 2)), history, schema, fixed, current)
