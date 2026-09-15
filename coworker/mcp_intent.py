"""MCP references with ASCII boundaries, including adjacent Chinese text."""

from __future__ import annotations

import re
from typing import Iterable


def mentions_mcp(text: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9_])mcp(?![a-z0-9_])", text, re.I))


def referenced_mcp_tools(text: str, names: Iterable[str]) -> tuple[str, ...]:
    """Match registered tool namespaces or configured server markers, never invent tools."""
    selected = []
    for name in names:
        if not name.startswith("mcp__"):
            continue
        server = name[5:].split("__", 1)[0]
        if server and re.search(
            rf"(?<![a-z0-9_-]){re.escape(server)}(?![a-z0-9_-])", text, re.I
        ):
            selected.append(name)
    return tuple(dict.fromkeys(selected))
