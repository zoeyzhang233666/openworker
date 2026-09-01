"""Text-channel rendering and parsing for ``ask_user`` Inbox items (D-196).

The Inbox remains the source of truth.  This module only translates one pending
question into a plain-text prompt and turns a reply from the bound conversation
back into the exact resolution value expected by ``ask_user``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..tools.ask import option_label

CHANNEL_TARGET_KEY = "channel_target"
CHANNEL_STEP_KEY = "channel_step"
CHANNEL_ANSWERS_KEY = "channel_answers"

_ANSWER_PREFIX = re.compile(r"^/answer(?:\s+|$)", re.I)
_MULTI_SEPARATOR = re.compile(r"\s*[,，、]\s*")


@dataclass(frozen=True)
class ParsedChannelAnswer:
    valid: bool
    answer: str = ""
    error: str = ""


def is_explicit_answer(text: str) -> bool:
    return bool(_ANSWER_PREFIX.match((text or "").strip()))


def strip_answer_prefix(text: str) -> str:
    return _ANSWER_PREFIX.sub("", (text or "").strip(), count=1).strip()


def question_step(item: Any) -> int:
    questions = list(getattr(item, "questions", None) or [])
    if not questions:
        return 0
    raw = (getattr(item, "data", None) or {}).get(CHANNEL_STEP_KEY, 0)
    try:
        step = int(raw)
    except (TypeError, ValueError):
        step = 0
    return min(max(step, 0), len(questions) - 1)


def current_question(item: Any) -> dict[str, Any]:
    questions = list(getattr(item, "questions", None) or [])
    if questions:
        entry = questions[question_step(item)]
        return dict(entry) if isinstance(entry, dict) else {"question": str(entry)}
    return {
        "question": str(getattr(item, "title", "") or ""),
        "header": str(getattr(item, "header", "") or ""),
        "options": list(getattr(item, "options", None) or []),
        "allow_text": bool(getattr(item, "allow_text", True)),
        "multi": bool(getattr(item, "multi", False)),
    }


def question_key(question: dict[str, Any]) -> str:
    return str(question.get("header") or question.get("question") or "answer")


def format_channel_question(item: Any, *, correction: str = "") -> str:
    question = current_question(item)
    questions = list(getattr(item, "questions", None) or [])
    step = question_step(item)
    header = str(question.get("header") or "").strip()
    prompt = str(question.get("question") or "").strip()
    options = list(question.get("options") or [])
    multi = bool(question.get("multi", False))

    lines = ["ChemClaw 需要你选择："]
    if questions:
        lines.append(f"第 {step + 1}/{len(questions)} 题" + (f" · {header}" if header else ""))
    elif header:
        lines.append(header)
    if prompt:
        lines.append(prompt)
    for index, option in enumerate(options, start=1):
        label = option_label(option).strip()
        if not label:
            continue
        recommended = bool(option.get("recommended")) if isinstance(option, dict) else False
        description = str(option.get("description") or "").strip() if isinstance(option, dict) else ""
        lines.append(f"{index}. {label}" + ("（推荐）" if recommended else ""))
        if description:
            lines.append(f"   {description}")
    if correction:
        lines.append(f"未识别该回答：{correction}")
    if options:
        hint = "请直接回复序号或选项文字，也可以发送 /answer 1。"
        if multi:
            hint = "可多选，请用逗号、中文逗号或顿号分隔；也可以发送 /answer 1，2。"
        lines.append(hint)
    else:
        lines.append("请直接回复内容，也可以发送 /answer <内容>。")
    return "\n".join(lines).strip()


def parse_channel_answer(item: Any, text: str) -> ParsedChannelAnswer:
    raw = strip_answer_prefix(text) if is_explicit_answer(text) else (text or "").strip()
    question = current_question(item)
    options = list(question.get("options") or [])
    allow_text = bool(question.get("allow_text", True))
    multi = bool(question.get("multi", False))
    if not raw:
        return ParsedChannelAnswer(False, error="回答不能为空，请重新选择。")

    labels = [option_label(option).strip() for option in options]
    labels = [label for label in labels if label]
    if not labels:
        if allow_text:
            return ParsedChannelAnswer(True, answer=raw)
        return ParsedChannelAnswer(False, error="本题不接受自由文本。")

    tokens = _MULTI_SEPARATOR.split(raw) if multi else [raw]
    if not multi and _MULTI_SEPARATOR.search(raw):
        return ParsedChannelAnswer(False, error="本题只能选择一项。")

    selected: list[str] = []
    for token in tokens:
        value = token.strip()
        if not value:
            continue
        if value.isdigit():
            index = int(value)
            if not 1 <= index <= len(labels):
                return ParsedChannelAnswer(False, error=f"序号 {value} 不在可选范围内。")
            selected.append(labels[index - 1])
            continue
        matched = next((label for label in labels if label.casefold() == value.casefold()), "")
        if matched:
            selected.append(matched)
            continue
        if allow_text:
            selected.append(value)
            continue
        return ParsedChannelAnswer(False, error=f"“{value}”不是可用选项。")
    if not selected:
        return ParsedChannelAnswer(False, error="回答不能为空，请重新选择。")
    return ParsedChannelAnswer(True, answer="、".join(dict.fromkeys(selected)))


def next_group_state(item: Any, answer: str) -> tuple[bool, dict[str, str], int]:
    """Return ``(complete, answers, next_step)`` after accepting one group answer."""
    question = current_question(item)
    data = dict(getattr(item, "data", None) or {})
    answers = {
        str(key): str(value)
        for key, value in dict(data.get(CHANNEL_ANSWERS_KEY) or {}).items()
    }
    answers[question_key(question)] = answer
    step = question_step(item) + 1
    complete = step >= len(list(getattr(item, "questions", None) or []))
    return complete, answers, step
