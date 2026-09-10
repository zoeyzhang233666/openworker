"""Markdown → HTML for report cook (D-195 / D-195b).

Uses PyPI ``markdown`` with tables; chart/mermaid fences are extracted first and
re-injected via an optional fence_renderer.
"""

from __future__ import annotations

import re
from typing import Callable

_FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
_PLACEHOLDER = "@@CHEMCLAW_FENCE_{idx}@@"
# Placeholders that survive markdown paragraph wrapping.
_PLACEHOLDER_BLOCK = "\n\n<!--CHEMCLAW_FENCE_{idx}-->\n\n"
_PLACEHOLDER_FIND = re.compile(r"<!--CHEMCLAW_FENCE_(\d+)-->")
_TABLE_SEP_CELL = re.compile(r"^:?-{3,}:?$")


def _line_is_table_separator(line: str) -> bool:
    stripped = (line or "").strip()
    if not stripped or "---" not in stripped:
        return False
    if "|" in stripped:
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    else:
        cells = [cell.strip() for cell in re.split(r"\s*\|\s*", stripped) if cell.strip()]
    if len(cells) < 2:
        return False
    return all(_TABLE_SEP_CELL.fullmatch(cell or "") for cell in cells)


def _line_is_table_row(line: str) -> bool:
    stripped = (line or "").strip()
    if not stripped:
        return False
    if _line_is_table_separator(line):
        return True
    if "|" in stripped:
        cells = [cell for cell in stripped.strip("|").split("|")]
        return len(cells) >= 2 and any(cell.strip() for cell in cells)
    parts = [part.strip() for part in stripped.split("|")]
    return len(parts) >= 2 and all(parts)


def _is_table_block(lines: list[str], start: int) -> bool:
    if start >= len(lines) or not _line_is_table_row(lines[start]):
        return False
    end = start
    while end < len(lines) and _line_is_table_row(lines[end]):
        end += 1
    block = lines[start:end]
    if len(block) < 2:
        return False
    return any(_line_is_table_separator(row) for row in block)


_LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+\S")


def _line_is_list_item(line: str) -> bool:
    return bool(_LIST_ITEM_RE.match(line or ""))


def normalize_gfm_lists(markdown: str) -> str:
    """Ensure list blocks are isolated before nl2br markdown runs.

    Assistant replies often place ``- item`` immediately after a heading or bold
    line without the blank line GFM needs. Without isolation, nl2br wraps list rows
    in ``<p>`` and the leading hyphens show up literally in Channel HTML pages.
    """
    lines = (markdown or "").splitlines()
    if not lines:
        return markdown or ""

    out: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if _line_is_list_item(line):
            if out and out[-1].strip() and not _line_is_list_item(out[-1]):
                out.append("")
            block_end = index
            while block_end < len(lines) and _line_is_list_item(lines[block_end]):
                block_end += 1
            out.extend(lines[index:block_end])
            index = block_end
            if index < len(lines) and lines[index].strip():
                out.append("")
            continue
        out.append(line)
        index += 1
    return "\n".join(out)


def normalize_gfm_tables(markdown: str) -> str:
    """Ensure pipe tables are isolated block elements before nl2br markdown runs.

    Assistant replies often place a table immediately after a heading or prose line
    without the blank line GFM needs. Without isolation, nl2br wraps table rows in
    ``<p>`` and the pipes show up literally in Channel HTML pages.
    """
    lines = (markdown or "").splitlines()
    if not lines:
        return markdown or ""

    out: list[str] = []
    index = 0
    while index < len(lines):
        if _is_table_block(lines, index):
            if out and out[-1].strip():
                out.append("")
            block_end = index
            while block_end < len(lines) and _line_is_table_row(lines[block_end]):
                block_end += 1
            out.extend(lines[index:block_end])
            index = block_end
            if index < len(lines) and lines[index].strip():
                out.append("")
            continue
        out.append(lines[index])
        index += 1
    return "\n".join(out)


def extract_fenced_blocks(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """Replace fenced blocks with HTML comments; return (text, [(lang, body), ...])."""
    blocks: list[tuple[str, str]] = []

    def repl(match: re.Match[str]) -> str:
        lang = (match.group(1) or "").strip().lower()
        body = match.group(2) or ""
        idx = len(blocks)
        blocks.append((lang, body))
        return _PLACEHOLDER_BLOCK.format(idx=idx)

    return _FENCE_RE.sub(repl, markdown or ""), blocks


def _default_fence_html(lang: str, body: str, index: int) -> str:
    from html import escape

    if lang == "chart":
        return '<p class="chart-missing">（图表占位）</p>'
    return (
        f'<pre><code class="language-{escape(lang)}">'
        f"{escape(body.rstrip())}</code></pre>"
    )


def markdown_to_html_fragments(
    markdown: str,
    *,
    fence_renderer: Callable[[str, str, int], str] | None = None,
) -> str:
    """Convert Markdown (incl. GFM tables) to HTML; reinject special fences."""
    import markdown as md_lib

    text, blocks = extract_fenced_blocks(markdown or "")
    text = normalize_gfm_lists(normalize_gfm_tables(text))
    html_body = md_lib.markdown(
        text,
        extensions=[
            "markdown.extensions.tables",
            "markdown.extensions.fenced_code",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
        ],
        output_format="html5",
    )

    renderer = fence_renderer or _default_fence_html

    def reinject(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        if idx < 0 or idx >= len(blocks):
            return match.group(0)
        lang, body = blocks[idx]
        return renderer(lang, body, idx)

    # Comments may sit inside <p>…</p> after markdown; strip wrapping p if sole content.
    html_body = re.sub(
        r"<p>\s*(<!--CHEMCLAW_FENCE_\d+-->)\s*</p>",
        r"\1",
        html_body,
    )
    return _PLACEHOLDER_FIND.sub(reinject, html_body)


# Back-compat alias used by older call sites / tests.
def markdown_tables_to_html(markdown: str) -> str:
    return markdown_to_html_fragments(markdown)
