"""WeCom final-reply composition: summary + COS HTML link (D-195 / D-195c)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..filestore.base import FileStorage, FileStorageError, NullFileStorage
from ..report_html.cook import cook_report_html, find_report_markdown

# WeCom markdown content soft cap (bytes); keep headroom under 20480.
_MAX_BUBBLE_CHARS = 3500

_FULL_BUBBLE_HINTS = (
    "完整版贴出来",
    "完整回答直接发",
    "直接发完整回答",
    "不要链接",
    "气泡里全文",
    "气泡全文",
    "全文发在",
    "把完整回答",
    "完整内容发到",
    "不要完整版链接",
    "贴全文",
)

# Explicit ask for a Markdown file on WeCom (rare).
_WANT_MD_FILE_HINTS = (
    "发markdown",
    "发 markdown",
    "发md文件",
    "发 md 文件",
    "给我md",
    "给我 md",
    "要markdown文件",
    "要 markdown 文件",
    "下载md",
    "下载 md",
)

_WECOM_GUIDANCE = (
    "\n\n[企微交付约定 — 务必遵守]\n"
    "1. 企业微信客户端对 Markdown 文件与气泡内复杂 MD 语法支持很差：默认不要用 send_file 发送 "
    ".md/.markdown，也不要把 `[标题](artifact:….md)` 写进企微回复。\n"
    "2. 本轮若写出了 Markdown 报告，系统会自动生成精装 HTML 完整版并附可打开链接；你只需给短总结"
    "（结论与要点），勿再单独发 MD 附件。\n"
    "3. 普通问答（无报告文件）：只发文字回答，不要 send_file，不要发任何附件。\n"
    "4. 仅当用户明确要求「气泡全文/不要链接」时，才把完整正文写进气泡；"
    "仅当用户明确索要「md/markdown 文件」时才可 send_file 发送 .md。"
)


@dataclass
class WecomFinalReply:
    text: str
    mode: str  # summary_link | full_bubble | summary_only
    html_url: Optional[str] = None


def wants_full_bubble(user_text: str) -> bool:
    raw = (user_text or "").strip()
    if not raw:
        return False
    return any(h in raw for h in _FULL_BUBBLE_HINTS)


def wants_md_file(user_text: str) -> bool:
    raw = (user_text or "").strip().lower().replace(" ", "")
    if not raw:
        return False
    compact = (user_text or "").strip().replace(" ", "").lower()
    return any(h.replace(" ", "") in compact for h in _WANT_MD_FILE_HINTS)


def wecom_turn_guidance_suffix() -> str:
    return _WECOM_GUIDANCE


def truncate_summary(text: str, limit: int = _MAX_BUBBLE_CHARS) -> str:
    raw = (text or "").strip()
    if len(raw) <= limit:
        return raw
    return raw[: max(0, limit - 20)].rstrip() + "\n\n…（详见完整版）"


def strip_md_artifacts_for_wecom(text: str) -> str:
    """Remove artifact:.md links and bare .md path teasers from WeCom bubbles."""
    out = text or ""
    # [title](artifact:path.md) → title（完整版见下方链接，由系统附加）
    out = re.sub(
        r"\[([^\]]+)\]\(artifact:[^)]+\.(?:md|markdown)\)",
        r"\1",
        out,
        flags=re.IGNORECASE,
    )
    # leftover artifact:*.md
    out = re.sub(
        r"\(artifact:[^)]+\.(?:md|markdown)\)",
        "",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"artifact:[^\s)]+\.(?:md|markdown)",
        "",
        out,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def compose_wecom_final_reply(
    *,
    assistant_text: str,
    user_text: str,
    workspace: Path | str | None,
    file_storage: FileStorage | None,
    chart_tool_results: list[dict[str, Any]] | None = None,
) -> WecomFinalReply:
    """Build the WeCom finish=true payload.

    - Report MD exists → short summary + polished HTML link (never attach MD).
    - No report → text-only summary (no file).
    - User asks for full bubble → raw text (still strip dead artifact:.md).
    """
    final = strip_md_artifacts_for_wecom(assistant_text or "")
    if wants_full_bubble(user_text):
        return WecomFinalReply(text=final or "（无正文）", mode="full_bubble")

    md_path = find_report_markdown(assistant_text or "", workspace)
    summary = truncate_summary(final) if final else "本轮已完成。"
    storage = file_storage or NullFileStorage()

    if md_path is None:
        # Pure Q&A — text only, no file / no fake HTML.
        return WecomFinalReply(text=summary, mode="summary_only")

    try:
        markdown = md_path.read_text(encoding="utf-8")
    except OSError:
        return WecomFinalReply(
            text=summary + "\n\n（完整版报告文件无法读取）",
            mode="summary_only",
        )

    cooked = cook_report_html(
        markdown,
        title=md_path.stem,
        chart_tool_results=chart_tool_results,
        workspace=workspace,
        write_local=True,
    )

    if not storage.configured():
        note = (
            "\n\n完整版需在 ChemClaw 设置中配置「云文件存储」（腾讯云 COS）后，"
            "才能生成可在企微内打开的精装网页（不发送 MD 文件）。"
        )
        return WecomFinalReply(text=summary + note, mode="summary_only")

    try:
        ref = storage.upload(
            cooked.html.encode("utf-8"),
            filename=f"{cooked.title or md_path.stem}.html",
            content_type="text/html; charset=utf-8",
        )
        url = storage.public_url(ref)
    except FileStorageError as exc:
        return WecomFinalReply(
            text=f"{summary}\n\n完整版上传失败：{exc}",
            mode="summary_only",
        )
    except Exception as exc:
        return WecomFinalReply(
            text=f"{summary}\n\n完整版上传失败（{type(exc).__name__}）",
            mode="summary_only",
        )

    body = f"{summary}\n\n[查看完整版]({url})"
    return WecomFinalReply(text=body, mode="summary_link", html_url=url)


def extract_user_text_from_source(source: Optional[dict[str, Any]]) -> str:
    if not source:
        return ""
    return str(source.get("text") or "").strip()


def strip_artifact_dead_links_for_im(text: str) -> str:
    """Leave artifact links as plain titles for IM readability."""
    return re.sub(
        r"\[([^\]]+)\]\(artifact:[^)]+\)",
        r"\1",
        text or "",
    )
