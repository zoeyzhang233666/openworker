"""The `send_message` outbound tool — available to every agent.

Stateless: parses the `target` token, pulls the bot token from the SecretStore at call time
(never in the model's context), and dispatches via a swappable sender registry. Permission-
gated (`requires_approval=True` → asks outside Auto mode).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Optional

import aisuite as ai

from ..secrets import SecretStore
from .base import parse_target
from .context import current_channel_target
from .senders import DEFAULT_FILE_SENDERS, DEFAULT_SENDERS, FileSender, Sender

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_message",
        "description": (
            "Send a message to a connected chat (Slack, Telegram, 企业微信、飞书、钉钉或微信). `target` is the "
            "reply handle from an inbound message (e.g. 'telegram:12345' or 'slack:C0123', "
            "optionally with a ':<thread>' suffix) — or, for Slack, just the channel NAME "
            "('#general' or 'general'; resolved against the connected workspaces). Use this to "
            "actually reach a person — plain assistant text is not delivered anywhere."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Destination handle 'platform:chat_id[:thread]', e.g. 'telegram:12345'.",
                },
                "text": {"type": "string", "description": "The message text to send."},
            },
            "required": ["target", "text"],
        },
    },
}


# Slack channel NAMES are strictly lowercase (letters/digits/[-._]); ids are uppercase
# C…/D…/G…/U… tokens. That asymmetry is the discriminator: anything lowercase (or
# #-prefixed) is a name the user said, everything else keeps the raw-address path.
_SLACK_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _slack_channel_name_like(chat_id: str) -> bool:
    return chat_id.startswith("#") or bool(_SLACK_NAME.match(chat_id))


def _parse_or_coerce(target: str) -> tuple[str, str, Optional[str]]:
    """parse_target, but a BARE channel name ('all-openworker', '#general') coerces to
    Slack — models pass what the user said, and a lowercase/#-name is Slack-shaped (owner
    repro 2026-07-14: the model never invented the 'slack:' prefix on its own). Telegram
    targets are numeric, so the shapes never collide."""
    try:
        return parse_target(target)
    except ValueError:
        raw = (target or "").strip()
        if raw and _slack_channel_name_like(raw.lstrip("#")):
            return "slack", raw, None
        raise


def _resolve_slack_channel(
    secrets: SecretStore, name: str
) -> tuple[Optional[str], Optional[str]]:
    """'#all-openworker' (a NAME the user said) → the team-qualified chat_id, via the
    same cached conversations.list roster the GUI's channel picker uses. (chat_id, error):
    exactly one match wins; none/many return an actionable error instead of a guess
    (§36 — 'post Hi to <channel>' must just work when Slack is connected)."""
    from .config import _slack_team_profiles
    from .slack_directory import list_channels

    query = name.lstrip("#").strip()
    teams = [team_id for team_id, _p in _slack_team_profiles(secrets)]
    if not teams and (secrets.get("slack:default") or {}).get("bot_token"):
        teams = ["default"]
    if not teams:
        return None, "no bot token for slack — connect it first"
    hits: list[tuple[str, dict]] = []
    for team in teams:
        r = list_channels(secrets, team, query, limit=50)
        if not r.get("ok"):
            continue
        for c in r.get("channels") or []:
            if str(c.get("name", "")).lower() == query.lower():
                hits.append((team, c))
    if not hits:
        return None, (
            f"no Slack channel named #{query} in the connected workspace"
            f"{'s' if len(teams) > 1 else ''} — check the name, or pass the full "
            "address (slack:C… / slack:T…/C…)"
        )
    if len(hits) > 1:
        return None, (
            f"#{query} exists in more than one connected workspace — use the full "
            "address (slack:TEAM_ID/CHANNEL_ID) to pick one"
        )
    team, c = hits[0]
    chat_id = str(c["id"]) if team == "default" else f"{team}/{c['id']}"
    if not c.get("is_member"):
        return None, (
            f"found #{query}, but the bot isn't a member — invite @OpenWorker to #{query} "
            "in Slack, then retry"
        )
    return chat_id, None


def _resolve_token(secrets: SecretStore, platform: str, chat_id: str) -> Optional[str]:
    """Pick the outbound token for a reply.

    Managed Slack relay is multi-workspace: a team-qualified chat_id ("T…/C…")
    selects that team's bot token from its `slack:team:<team_id>` profile. Manual
    Socket-Mode (single workspace, bare "C…") uses `slack:default`. Non-Slack
    platforms always use `<platform>:default`.
    """
    if platform == "slack":
        from .slack_addr import split

        team, _channel = split(chat_id)
        if team:
            per_team = secrets.get(f"slack:team:{team}") or {}
            return per_team.get("bot_token")
    if platform == "weixin" and "/" in chat_id:
        from . import accounts

        account_id, _conversation_id = chat_id.split("/", 1)
        resolved_id, _key, profile = accounts.resolve(secrets, platform, account_id)
        if profile:
            # The live registry is always keyed by the stable local account id,
            # including while that account is still waiting for a QR scan.
            return resolved_id
    creds = secrets.get(f"{platform}:default") or {}
    if platform == "wecom":
        # Live WS adapter is keyed by bot_id (see wecom_bot._LIVE / senders._send_wecom).
        return creds.get("bot_id")
    if platform == "feishu":
        return creds.get("app_id")
    if platform == "dingtalk":
        return creds.get("client_id")
    if platform == "weixin":
        from . import accounts

        account_id, _key, profile = accounts.resolve(secrets, platform)
        if profile:
            return account_id
        return creds.get("bot_id") or creds.get("account_id") or None
    return creds.get("bot_token")


def make_send_message_tool(
    secrets: SecretStore,
    *,
    senders: Optional[dict[str, Sender]] = None,
    file_senders: Optional[dict[str, FileSender]] = None,
    workspace: Optional[Path] = None,
    file_storage: Optional[Any] = None,
) -> Callable[..., Any]:
    """Build the `send_message` tool bound to a SecretStore (and optional sender registry)."""
    senders = senders if senders is not None else DEFAULT_SENDERS
    file_senders = file_senders if file_senders is not None else DEFAULT_FILE_SENDERS

    def send_message(target: str, text: str) -> dict[str, Any]:
        try:
            platform, chat_id, thread_id = _parse_or_coerce(target)
        except ValueError as exc:
            return {"error": str(exc)}
        sender = senders.get(platform)
        if sender is None:
            return {"error": f"unknown platform: {platform}"}
        # §36: a channel NAME resolves to its address (the user says "#general", not C0123).
        if platform == "slack" and _slack_channel_name_like(chat_id):
            chat_id, err = _resolve_slack_channel(secrets, chat_id)
            if err:
                return {"error": err}
        token = _resolve_token(secrets, platform, chat_id)
        if not token:
            if platform == "wecom":
                return {"error": "企业微信未连接 — 请先在连接设置中填写 bot_id 与 secret"}
            return {"error": f"no bot token for {platform} — connect it first"}
        from ..channels.rich_output import (
            compose_channel_rich_reply,
            deliver_rich_reply_files,
            needs_channel_html_delivery,
            rich_delivery_failure_text,
        )

        rich = None
        if needs_channel_html_delivery(text, workspace):
            rich = compose_channel_rich_reply(
                assistant_text=text,
                workspace=workspace,
                file_storage=file_storage,
            )
            text = rich.text
        if platform == "slack":
            from .attribution import sender_prefix

            text = sender_prefix(secrets, chat_id) + text
        if rich is not None and (
            rich.preview_image_bytes or (rich.html_url is None and rich.html_bytes)
        ):
            delivered = deliver_rich_reply_files(
                platform=platform,
                chat_id=chat_id,
                thread_id=thread_id,
                token=token,
                reply=rich,
                comment=text,
                file_storage=file_storage,
                file_senders=file_senders,
                text_senders=senders,
            )
            if rich.html_url is None and rich.html_bytes:
                if delivered.get("ok"):
                    return {
                        "ok": True,
                        "message_id": delivered.get("message_id"),
                        "target": target,
                        "delivery": delivered.get("delivery"),
                        "filename": rich.filename,
                        "preview": delivered.get("preview"),
                    }
                text = delivered.get("text") or rich_delivery_failure_text(
                    rich, delivered.get("error") or ""
                )
                if platform == "slack":
                    from .attribution import sender_prefix

                    text = sender_prefix(secrets, chat_id) + text
        result = sender(token, chat_id, text, thread_id)
        if result.ok:
            return {"ok": True, "message_id": result.message_id, "target": target}
        return {"error": result.error or "send failed"}

    send_message.__name__ = "send_message"
    send_message.__doc__ = _SCHEMA["function"]["description"]
    send_message.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="send_message",
        category="messaging",
        risk_level="medium",
        capabilities=["messaging"],
        requires_approval=True,
    )
    send_message.__coworker_schema__ = _SCHEMA
    return send_message


# -- send_file (§34 / UX-016) ----------------------------------------------------------

_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_file",
        "description": (
            "Upload a file from the session's workspace into the current connected chat. "
            "`target` defaults to the Channel conversation that started this turn; set it "
            "only to send to an explicit destination. Platforms show their own previews "
            "for pdf/csv/images — send the actual file, not a screenshot of it. For .html "
            "artifacts (which Slack can't preview) set as_screenshot=true to send a "
            "rendered PNG instead. This is a DISTINCT permission from send_message: it "
            "asks for approval even in threads where text replies are pre-approved."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Optional destination handle 'platform:chat_id[:thread]'. Defaults to the current Channel conversation.",
                },
                "path": {
                    "type": "string",
                    "description": "The file to send — workspace-relative, or absolute within an allowed folder.",
                },
                "title": {
                    "type": "string",
                    "description": "Display title (defaults to the filename).",
                },
                "comment": {
                    "type": "string",
                    "description": "Short message posted with the file.",
                },
                "as_screenshot": {
                    "type": "boolean",
                    "description": "HTML only: render the page headless and send a PNG preview instead of the raw file.",
                },
            },
            "required": ["path"],
        },
    },
}

_MAX_FILE_BYTES = 50 * 1024 * 1024  # sanity cap well under Slack's limit
_ALLOWED_FILE_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".json",
    ".md",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
    ".zip",
}


def _resolve_within(path: str, bases: list[Path]) -> Optional[Path]:
    """Resolve `path` (relative → tried against each base) and require the result to live
    inside one of the allowed bases. None → outside every base or nonexistent."""
    candidates = []
    p = Path(path).expanduser()
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.extend(base / p for base in bases)
    for cand in candidates:
        try:
            resolved = cand.resolve(strict=True)
        except OSError:
            continue
        # Even a link that resolves back inside the workspace is rejected: outbound
        # authorization applies to the named regular file, never an indirect alias.
        try:
            if cand.is_symlink():
                continue
        except OSError:
            continue
        for base in bases:
            try:
                resolved.relative_to(base.resolve())
                return resolved
            except ValueError:
                continue
    return None


def _render_html_png(path: Path) -> bytes:
    """Headless render of a local HTML artifact → viewport PNG (1280×800). Uses the
    Playwright chromium we already ship for the browser connector."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(path.as_uri())
            page.wait_for_timeout(500)  # let embedded JS (charts, tables) paint
            return page.screenshot(full_page=False)
        finally:
            browser.close()


def make_send_file_tool(
    secrets: SecretStore,
    *,
    workspace: Optional[Path] = None,
    roots: Optional[list] = None,
    file_senders: Optional[dict[str, FileSender]] = None,
    text_senders: Optional[dict[str, Sender]] = None,
    file_storage: Optional[Any] = None,
    render_html: Optional[Callable[[Path], bytes]] = None,
) -> Callable[..., Any]:
    """Build the `send_file` tool. Same target grammar and token resolution as
    send_message, but a DIFFERENT tool name — standing send_message grants (e.g. a
    mention-thread's pre-approval) never cover file uploads.

    D-194: optional ``file_storage`` enables COS upload + URL delivery for platforms
    without reliable native file APIs (Telegram / WeCom fallback). Local GUI artifacts
    are never uploaded unless this tool runs.
    """
    from .file_delivery import URL_PRIMARY_PLATFORMS, deliver_file

    file_senders = file_senders if file_senders is not None else DEFAULT_FILE_SENDERS
    text_senders = text_senders if text_senders is not None else DEFAULT_SENDERS
    render_html = render_html or _render_html_png
    bases = [Path(r.path) for r in (roots or []) if getattr(r, "path", None)]
    if workspace is not None:
        bases.append(Path(workspace))

    def send_file(
        target: Optional[str] = None,
        path: str = "",
        title: Optional[str] = None,
        comment: Optional[str] = None,
        as_screenshot: bool = False,
    ) -> dict[str, Any]:
        destination = (target or current_channel_target()).strip()
        if not destination:
            return {
                "error": "当前任务不是由 Channel 会话发起，请明确提供 target 后再发送文件"
            }
        try:
            platform, chat_id, thread_id = _parse_or_coerce(destination)
        except ValueError as exc:
            return {"error": str(exc)}
        can_native = platform in file_senders
        can_url = platform in text_senders and (
            platform in URL_PRIMARY_PLATFORMS or can_native or platform == "telegram"
        )
        if not can_native and not can_url:
            return {"error": f"file sending is not supported on {platform} yet"}
        # §36: channel names resolve here too — same rule as send_message.
        if platform == "slack" and _slack_channel_name_like(chat_id):
            chat_id, err = _resolve_slack_channel(secrets, chat_id)
            if err:
                return {"error": err}
        if not bases:
            return {"error": "no workspace folders available to read from"}
        resolved = _resolve_within(path, bases)
        if resolved is None or not resolved.is_file():
            return {
                "error": "path is outside the folders this session can access (or missing)"
            }
        if resolved.suffix.lower() not in _ALLOWED_FILE_EXTENSIONS:
            return {"error": f"不允许发送此文件类型：{resolved.suffix or '无扩展名'}"}
        token = _resolve_token(secrets, platform, chat_id)
        if not token:
            return {"error": f"no bot token for {platform} — connect it first"}
        # D-195c: WeCom renders Markdown files poorly — convert .md → polished HTML.
        wecom_md_converted = False
        if platform == "wecom" and resolved.suffix.lower() in {".md", ".markdown"}:
            from ..report_html.cook import cook_report_html

            try:
                md_text = resolved.read_text(encoding="utf-8")
            except OSError as exc:
                return {
                    "error": (
                        "企业微信不发送 Markdown 文件；读取报告以生成精装 HTML 失败："
                        f"{exc}"
                    )
                }
            cooked = cook_report_html(
                md_text,
                title=resolved.stem,
                workspace=workspace,
                write_local=True,
            )
            data = cooked.html.encode("utf-8")
            filename = f"{(title or cooked.title or resolved.stem).strip() or resolved.stem}.html"
            if not filename.lower().endswith((".html", ".htm")):
                filename = f"{filename}.html"
            if not (comment or "").strip():
                comment = "完整版已转为精装网页（企业微信不发送 Markdown 文件）"
            if not title:
                title = cooked.title
            wecom_md_converted = True
        elif as_screenshot:
            if resolved.suffix.lower() not in (".html", ".htm"):
                return {"error": "as_screenshot only applies to .html files"}
            try:
                data = render_html(resolved)
            except Exception as exc:
                return {"error": f"could not render the page: {exc}"}
            filename = resolved.stem + ".png"
        else:
            if resolved.stat().st_size > _MAX_FILE_BYTES:
                return {"error": "file is larger than 50 MB"}
            data = resolved.read_bytes()
            filename = resolved.name
        if platform == "slack" and comment:
            from .attribution import sender_prefix

            comment = sender_prefix(secrets, chat_id) + comment
        delivered = deliver_file(
            platform=platform,
            chat_id=chat_id,
            thread_id=thread_id,
            token=token,
            filename=filename,
            data=data,
            title=title,
            comment=comment,
            file_storage=file_storage,
            file_senders=file_senders,
            text_senders=text_senders,
        )
        if delivered.ok:
            out: dict[str, Any] = {
                "ok": True,
                "file_id": delivered.message_id,
                "target": destination,
                "filename": filename,
                "delivery": delivered.delivery,
            }
            if wecom_md_converted:
                out["converted_from"] = "markdown"
                out["warning"] = (
                    "企业微信不适合发送 Markdown 文件，已自动改为精装 HTML 完整版。"
                )
            if delivered.file_ref is not None:
                out["file_ref"] = {
                    "url": delivered.file_ref.url,
                    "key": delivered.file_ref.key,
                    "filename": delivered.file_ref.filename,
                    "sha256": delivered.file_ref.sha256,
                    "size": delivered.file_ref.size,
                }
            if delivered.warning:
                out["warning"] = delivered.warning
            return out
        return {"error": delivered.error or "file send failed"}

    send_file.__name__ = "send_file"
    send_file.__doc__ = _FILE_SCHEMA["function"]["description"]
    send_file.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="send_file",
        category="messaging",
        risk_level="medium",
        capabilities=["messaging", "files"],
        requires_approval=True,
    )
    send_file.__coworker_schema__ = _FILE_SCHEMA
    return send_file
