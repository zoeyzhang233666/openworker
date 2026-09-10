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

_CHANNEL_PLATFORM_LABELS = {
    "wecom": "企业微信",
    "weixin": "个人微信",
    "feishu": "飞书",
    "dingtalk": "钉钉",
    "telegram": "Telegram",
    "slack": "Slack",
}

_IMAGE_ONLY_HINTS = (
    "不要html",
    "不要 html",
    "不要网页",
    "不要链接",
    "只要图片",
    "只要图",
    "要图片",
    "给我图片",
    "发图片",
    "png图片",
    "png 图片",
    "要png",
    "要 png",
)


def _channel_guidance_body(platform: str) -> str:
    return (
        f"\n\n[{platform}交付约定 — 务必遵守]\n"
        "0. 查价要快：已投影 chem-data-hub / 行情工具时立刻调用，禁止连环 ask_user"
        "（时间范围/产品形态/「请你贴生意社数据」等）；用户只要今天/现价/多少钱时用小 limit 取最新点后短答；"
        "要走势图再拉序列并写 ```chart。禁止声称「无法调用 MCP」。\n"
        "1. 行情/价格走势图：必须在回复中包含 ```chart JSON 块（ChartSpec version 1）。"
        "系统会自动生成图表预览 PNG，并按需附精装 HTML 链接——"
        "你不需要 send_file、chart-image 或 shell；禁止声称「无法发送图片/附件/文件」。"
        "聊天气泡只写短摘要，图表由系统自动交付。\n"
        "2. Markdown 报告：若写入 report.md 或 artifact 链接，系统会自动 cook 为精装 HTML；"
        "你只需给短总结，勿用 send_file 发送 .md/.markdown。\n"
        "3. 纯文字问答（无图表、无报告）：只发文字，不要 send_file。\n"
        "4. 用户明确「气泡全文/不要链接」时，才把完整正文写进气泡；"
        "明确索要 md 文件时才可 send_file 发送 .md。"
    )


_WECOM_GUIDANCE = _channel_guidance_body("企微")


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


def wants_image_only(user_text: str) -> bool:
    """User asked for PNG/image delivery without an HTML link or attachment."""
    compact = (user_text or "").strip().replace(" ", "").lower()
    if not compact:
        return False
    return any(h.replace(" ", "") in compact for h in _IMAGE_ONLY_HINTS)


def channel_turn_guidance_suffix(connector: str = "") -> str:
    label = _CHANNEL_PLATFORM_LABELS.get((connector or "").strip().lower(), "消息平台")
    if label == "企业微信":
        return _WECOM_GUIDANCE
    return _channel_guidance_body(label)


def wecom_turn_guidance_suffix() -> str:
    return channel_turn_guidance_suffix("wecom")


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
