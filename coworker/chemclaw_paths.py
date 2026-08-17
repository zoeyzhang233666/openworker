"""ChemClaw session workspace layout and artifact path identity.

User-facing deliverables live at the session workspace root.
Internal process files live under ``._chemclaw/`` (already skipped by artifact listing
because it is a dot-directory).
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath, PureWindowsPath

CHEMCLAW_INTERNAL_DIRNAME = "._chemclaw"
CHEMCLAW_CHARTS_DIRNAME = "charts"

_WIN_ABS = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)")
_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_MD_HREF = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")


def chemclaw_internal_dir(workspace: str | Path) -> Path:
    return Path(workspace) / CHEMCLAW_INTERNAL_DIRNAME


def chemclaw_charts_workdir(workspace: str | Path) -> Path:
    return chemclaw_internal_dir(workspace) / CHEMCLAW_CHARTS_DIRNAME


def stable_session_workspace(path: str | Path) -> Path:
    """Snap a path that drifted under ``._chemclaw/`` back to the session root.

    Shell cwd may follow the model into ``._chemclaw/charts/...``; that must never become
    the persisted session workspace used by the artifacts panel.
    """
    raw = str(path)
    part_lists: list[tuple[str, ...]] = []
    if is_windows_absolute_path(raw) or "\\" in raw:
        part_lists.append(PureWindowsPath(raw).parts)
    part_lists.append(Path(raw).parts)
    part_lists.append(PurePosixPath(raw.replace("\\", "/")).parts)

    for parts in part_lists:
        for i, part in enumerate(parts):
            if part != CHEMCLAW_INTERNAL_DIRNAME:
                continue
            if i == 0:
                break
            head = parts[:i]
            # Drive paths (C:\, \\server\share) must stay Windows-shaped even on Linux CI.
            if head and (
                is_windows_absolute_path(raw)
                or (len(head[0]) == 2 and head[0][1] == ":")
                or head[0].startswith("\\\\")
            ):
                return Path(str(PureWindowsPath(*head)))
            return Path(*head)
    return Path(path)


def is_windows_absolute_path(path: str) -> bool:
    raw = str(path or "")
    return bool(_WIN_ABS.match(raw))


def _win_parts_casefold(p: PureWindowsPath) -> list[str]:
    parts: list[str] = []
    for i, part in enumerate(p.parts):
        if i == 0:
            parts.append(part.replace("\\", "").replace("/", "").lower())
        else:
            parts.append(part.lower())
    return parts


def _relative_windows(workspace: str, path: str) -> str | None:
    ws = PureWindowsPath(workspace)
    target = PureWindowsPath(path)
    ws_cf = _win_parts_casefold(ws)
    tgt_cf = _win_parts_casefold(target)
    if not ws_cf or len(tgt_cf) < len(ws_cf):
        return None
    if tgt_cf[: len(ws_cf)] != ws_cf:
        return None
    rest = list(target.parts[len(ws.parts) :])
    if any(part == ".." for part in rest):
        return None
    if not rest:
        return ""
    return PureWindowsPath(*rest).as_posix()


def _has_dotdot(rel: str) -> bool:
    parts = PurePosixPath(rel.replace("\\", "/")).parts
    return ".." in parts


def workspace_relpath_or_none(workspace: str | Path, path: str) -> str | None:
    """Return a posix workspace-relative path, or None if the path is outside `workspace`.

    Never falls back to basename matching. Windows-style absolute paths are parsed with
    PureWindowsPath so Linux CI can test them without a ``C:\\`` filesystem.
    """
    raw = str(path or "").strip()
    if not raw:
        return None
    if raw.lower().startswith("artifact:"):
        raw = raw[len("artifact:") :]
    ws = str(workspace)

    if is_windows_absolute_path(raw):
        return _relative_windows(ws, raw)

    candidate = Path(raw)
    if candidate.is_absolute():
        try:
            root = Path(ws).expanduser().resolve()
            target = candidate.expanduser().resolve()
            rel = target.relative_to(root)
        except (ValueError, OSError):
            return None
        posix = rel.as_posix()
        if posix.startswith("..") or _has_dotdot(posix):
            return None
        return posix

    rel = raw.replace("\\", "/").lstrip("/")
    if not rel or _has_dotdot(rel):
        return None
    return str(PurePosixPath(rel))


def relativize_markdown_asset_hrefs(markdown: str, workspace: str | Path) -> str:
    """Rewrite in-workspace absolute image/file hrefs to relative form (``./file.png``)."""

    def repl(match: re.Match[str]) -> str:
        href = match.group(2).strip().strip("<>")
        if _SCHEME.match(href) and not is_windows_absolute_path(href):
            if href.lower().startswith("artifact:"):
                inner = workspace_relpath_or_none(workspace, href)
                if inner is None:
                    return match.group(0)
                return f"{match.group(1)}artifact:{inner}{match.group(3)}"
            return match.group(0)
        rel = workspace_relpath_or_none(workspace, href)
        if rel is None:
            return match.group(0)
        shown = f"./{rel}" if "/" not in rel else rel
        return f"{match.group(1)}{shown}{match.group(3)}"

    return _MD_HREF.sub(repl, markdown)
