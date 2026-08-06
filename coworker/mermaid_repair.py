"""Mermaid fence extract/replace helpers for D-074 in-place repair."""

from __future__ import annotations

import re
from typing import Optional

# Fenced mermaid: optional spaces after ```, language mermaid, body until closing fence.
_MERMAID_FENCE_RE = re.compile(
    r"```[ \t]*mermaid[ \t]*\r?\n(.*?)```",
    re.IGNORECASE | re.DOTALL,
)

_REPAIR_SYSTEM = """\
You fix Mermaid diagram source that failed to render.
Return ONLY one fenced mermaid code block (```mermaid ... ```).
Preserve the author's intent and structure; fix syntax so mermaid can parse it.
Do not add commentary, markdown outside the fence, or tools.
Keep edge labels on directed graphs when present; do not invent new domain facts.
"""


def extract_mermaid_sources(content: str) -> list[str]:
    """Return bodies of all mermaid fences in content (without fences)."""
    return [m.group(1).rstrip("\n") for m in _MERMAID_FENCE_RE.finditer(content or "")]


def find_message_index_for_source(
    messages: list[dict],
    source: str,
    *,
    message_ts: Optional[float] = None,
) -> Optional[int]:
    """Locate assistant message containing this mermaid body. Prefer matching ts."""
    needle = (source or "").rstrip("\n")
    if not needle:
        return None
    candidates: list[int] = []
    for i, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content") or ""
        if not isinstance(content, str):
            continue
        if any(b.rstrip("\n") == needle for b in extract_mermaid_sources(content)):
            candidates.append(i)
    if not candidates:
        return None
    if message_ts is not None:
        for i in candidates:
            ts = messages[i].get("ts")
            if isinstance(ts, (int, float)) and abs(float(ts) - float(message_ts)) < 1e-6:
                return i
    return candidates[-1]  # most recent match


def replace_mermaid_source(content: str, old_source: str, new_source: str) -> Optional[str]:
    """Replace the first mermaid fence whose body matches old_source. None if not found."""
    old = (old_source or "").rstrip("\n")
    new_body = (new_source or "").rstrip("\n")
    if not old:
        return None

    replaced = False

    def _sub_once(match: re.Match[str]) -> str:
        nonlocal replaced
        body = match.group(1).rstrip("\n")
        if replaced or body != old:
            return match.group(0)
        replaced = True
        return f"```mermaid\n{new_body}\n```"

    out = _MERMAID_FENCE_RE.sub(_sub_once, content or "")
    return out if replaced else None


def parse_repaired_mermaid(text: str) -> Optional[str]:
    """Extract the first mermaid fence body from a model reply."""
    bodies = extract_mermaid_sources(text or "")
    if bodies:
        return bodies[0].rstrip("\n")
    # Bare source without fence
    stripped = (text or "").strip()
    if stripped and "```" not in stripped and len(stripped) < 50_000:
        # Heuristic: looks like a diagram start
        head = stripped.splitlines()[0].lower() if stripped else ""
        if any(
            head.startswith(p)
            for p in (
                "graph",
                "flowchart",
                "sequencediagram",
                "classdiagram",
                "statediagram",
                "erdiagram",
                "journey",
                "gantt",
                "pie",
                "mindmap",
                "timeline",
                "gitgraph",
                "c4context",
            )
        ):
            return stripped.rstrip("\n")
    return None


def repair_prompt_messages(source: str, error: str) -> list[dict[str, str]]:
    """Build the no-tools chat messages for a repair completion."""
    err = (error or "").strip()[:2000]
    user = (
        "The following Mermaid source failed to render.\n"
        f"Renderer error:\n{err or '(unknown)'}\n\n"
        "Broken source:\n"
        f"```mermaid\n{(source or '').rstrip(chr(10))}\n```\n"
    )
    return [
        {"role": "system", "content": _REPAIR_SYSTEM},
        {"role": "user", "content": user},
    ]
