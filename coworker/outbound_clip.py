from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Tuple

# Matches the rollout plan: tool/MCP "outbound view" gets capped so the model cannot
# blow up the prompt window due to a single massive tool response.
DEFAULT_CAP_CHARS = 40_000
DEFAULT_HEAD_CHARS = 2_000
DEFAULT_TAIL_CHARS = 500
# Prefer a structured MCP summary before falling back to head/tail clip.
MCP_SUMMARY_CAP_CHARS = 8_000
MCP_SUMMARY_FIELD_CHARS = 400


def _stable_overflow_key(
    content: str, *, head_chars: int, tail_chars: int
) -> str:
    """
    Create a stable key so repeated outbound-clip calls don't keep creating new files.
    We hash only head/tail+length to avoid extra memory/CPU.
    """
    head = content[:head_chars]
    tail = content[-tail_chars:] if len(content) > tail_chars else ""
    h = hashlib.sha1()
    h.update(str(len(content)).encode("utf-8", errors="replace"))
    h.update(b"|")
    h.update(head.encode("utf-8", errors="replace"))
    h.update(b"|")
    h.update(tail.encode("utf-8", errors="replace"))
    return h.hexdigest()


def _clip_scalar(value: Any, limit: int = MCP_SUMMARY_FIELD_CHARS) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def summarize_mcp_result(content: str, *, tool_name: str | None = None) -> str | None:
    """Build a compact structured summary for large MCP / JSON tool payloads.

    Returns None when the content is not worth specializing (keep default head/tail).
    """
    if not isinstance(content, str) or len(content) < 2_000:
        return None
    name = tool_name or ""
    looks_mcp = name.startswith("mcp__") or content.lstrip().startswith(("{", "["))
    if not looks_mcp:
        return None

    parsed: Any = None
    try:
        parsed = json.loads(content)
    except (ValueError, TypeError):
        # Not JSON — keep a short head with tool label.
        head = content[:MCP_SUMMARY_CAP_CHARS]
        label = name or "tool"
        return (
            f"[MCP 结果摘要 · {label} · 原文 {len(content)} 字符]\n"
            f"{head}"
            + ("…" if len(content) > MCP_SUMMARY_CAP_CHARS else "")
        )

    lines = [f"[MCP 结果摘要 · {name or 'tool'} · 原文 {len(content)} 字符]"]

    if isinstance(parsed, dict):
        if parsed.get("error"):
            lines.append(f"- error: {_clip_scalar(parsed.get('error'))}")
        # Prefer common research keys.
        preferred = (
            "q",
            "query",
            "product_name",
            "name",
            "title",
            "cas",
            "formula",
            "summary",
            "message",
            "status",
            "count",
            "total",
        )
        for key in preferred:
            if key in parsed and parsed[key] not in (None, "", [], {}):
                lines.append(f"- {key}: {_clip_scalar(parsed[key])}")
        # Nested list samples (compounds, results, items, data, prices…).
        for key, value in parsed.items():
            if key in preferred:
                continue
            if isinstance(value, list) and value:
                lines.append(f"- {key}: {len(value)} 条")
                for i, item in enumerate(value[:5]):
                    lines.append(f"  - [{i}] {_clip_scalar(item, 240)}")
                if len(value) > 5:
                    lines.append(f"  - …另有 {len(value) - 5} 条")
            elif isinstance(value, dict) and value and len(lines) < 40:
                sample_keys = list(value.keys())[:8]
                lines.append(
                    f"- {key}: object keys={sample_keys}"
                )
            elif not isinstance(value, (dict, list)) and key not in preferred:
                if len(lines) < 36 and value not in (None, "", [], {}):
                    lines.append(f"- {key}: {_clip_scalar(value, 160)}")
    elif isinstance(parsed, list):
        lines.append(f"- list: {len(parsed)} 条")
        for i, item in enumerate(parsed[:8]):
            lines.append(f"  - [{i}] {_clip_scalar(item, 240)}")
        if len(parsed) > 8:
            lines.append(f"  - …另有 {len(parsed) - 8} 条")
    else:
        lines.append(_clip_scalar(parsed, MCP_SUMMARY_CAP_CHARS))

    text = "\n".join(lines)
    if len(text) > MCP_SUMMARY_CAP_CHARS:
        text = text[: MCP_SUMMARY_CAP_CHARS - 1] + "…"
    return text


_QUERY_ARG_KEYS = ("q", "query", "product_name", "name", "cas", "keyword", "keywords")


def mcp_query_label(arguments: dict[str, Any] | None) -> str:
    """Pick a short human query string from MCP tool arguments."""
    if not arguments:
        return ""
    for key in _QUERY_ARG_KEYS:
        if key in arguments and arguments[key] not in (None, ""):
            return _clip_scalar(arguments[key], 120)
    # Fall back to first short scalar.
    for key, value in arguments.items():
        if isinstance(value, (str, int, float)) and str(value).strip():
            return f"{key}={_clip_scalar(value, 80)}"
    return ""


def clip_tool_result(
    content: str,
    *,
    workspace_root: Path,
    cap_chars: int = DEFAULT_CAP_CHARS,
    head_chars: int = DEFAULT_HEAD_CHARS,
    tail_chars: int = DEFAULT_TAIL_CHARS,
    overflow_rel_dir: str = "._chemclaw/outbound-clip",
    tool_name: str | None = None,
) -> Tuple[str, Optional[str]]:
    """
    Returns (clipped_content, overflow_path_or_None).

    - When clipped: write full content to a stable overflow file under
      `workspace_root/overflow_rel_dir/`, and inject a short pointer into the
      clipped output so the model can re-load the exact text later.
    - MCP / large JSON results prefer a structured summary over raw head/tail.
    - Only affects the *outbound* view; canonical history is untouched.
    """
    if not isinstance(content, str):
        content = str(content)

    if len(content) <= cap_chars:
        return content, None

    overflow_key = _stable_overflow_key(
        content, head_chars=head_chars, tail_chars=tail_chars
    )
    overflow_dir = (workspace_root / overflow_rel_dir).resolve()
    overflow_dir.mkdir(parents=True, exist_ok=True)
    overflow_path = overflow_dir / f"{overflow_key}.txt"

    overflow_rel_path = Path(overflow_rel_dir) / f"{overflow_key}.txt"
    overflow_rel_path_s = str(overflow_rel_path).replace("\\", "/")

    if not overflow_path.exists():
        # Keep the overflow text intact for exact recovery.
        overflow_path.write_text(content, encoding="utf-8")

    summary = summarize_mcp_result(content, tool_name=tool_name)
    if summary:
        clipped = (
            f"{summary}\n\n"
            f"[... 完整内容已保存至产物：{overflow_rel_path_s} ...]"
        )
    else:
        head = content[:head_chars]
        tail = content[-tail_chars:] if len(content) > tail_chars else ""
        clipped = (
            f"{head}\n\n"
            f"[... 完整内容已保存至产物：{overflow_rel_path_s} ...]\n\n"
            f"{tail}"
        )

    if len(clipped) > cap_chars:
        clipped = clipped[: cap_chars - 1] + "…"

    return clipped, overflow_rel_path_s
