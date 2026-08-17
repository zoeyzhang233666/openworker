"""ChemClaw workspace-relative artifact identity and internal workdir helpers."""

from pathlib import Path

from coworker.chemclaw_paths import (
    chemclaw_charts_workdir,
    chemclaw_internal_dir,
    relativize_markdown_asset_hrefs,
    stable_session_workspace,
    workspace_relpath_or_none,
)


def test_internal_charts_dir_is_under_dot_chemclaw(tmp_path):
    ws = tmp_path / "6ce94f6e-13d"
    ws.mkdir()
    assert chemclaw_internal_dir(ws) == ws / "._chemclaw"
    assert chemclaw_charts_workdir(ws) == ws / "._chemclaw" / "charts"


def test_stable_session_workspace_unit():
    assert str(stable_session_workspace(r"D:\a\b\._chemclaw\charts")).replace(
        "\\", "/"
    ) == "D:/a/b"


def test_relative_posix_and_backslash_paths():
    ws = r"C:\Users\EDY\OpenWorker\6ce94f6e-13d"
    assert workspace_relpath_or_none(ws, "甲醇行情周报_2026W33.md") == "甲醇行情周报_2026W33.md"
    assert workspace_relpath_or_none(ws, r"charts\foo.png") == "charts/foo.png"
    assert workspace_relpath_or_none(ws, "artifact:甲醇行情周报_2026W33.md") == "甲醇行情周报_2026W33.md"


def test_windows_absolute_path_inside_workspace():
    ws = r"C:\Users\EDY\OpenWorker\6ce94f6e-13d"
    got = workspace_relpath_or_none(
        ws,
        r"C:\Users\EDY\OpenWorker\6ce94f6e-13d\甲醇行情周报_2026W33.md",
    )
    assert got == "甲醇行情周报_2026W33.md"

    got = workspace_relpath_or_none(
        ws,
        "C:/Users/EDY/OpenWorker/6ce94f6e-13d/甲醇行情周报_2026W33.md",
    )
    assert got == "甲醇行情周报_2026W33.md"


def test_windows_absolute_path_rejects_escape():
    ws = r"C:\Users\EDY\OpenWorker\session-a"
    assert (
        workspace_relpath_or_none(ws, r"C:\Users\EDY\OpenWorker\session-b\secret.md")
        is None
    )
    assert workspace_relpath_or_none(ws, r"C:\Windows\System32\secret.txt") is None
    assert workspace_relpath_or_none(ws, r"..\session-b\secret.md") is None
    assert workspace_relpath_or_none(ws, "../session-b/secret.md") is None


def test_basename_collision_is_not_enough():
    """Same filename in another session must not resolve to this workspace."""
    ws = r"C:\Users\EDY\OpenWorker\session-a"
    assert workspace_relpath_or_none(ws, r"C:\Users\EDY\OpenWorker\session-b\report.md") is None


def test_relativize_markdown_images_drop_windows_abs_paths():
    ws = r"C:\Users\EDY\OpenWorker\sess"
    md = "见 ![chart](C:\\Users\\EDY\\OpenWorker\\sess\\chart.png)"
    out = relativize_markdown_asset_hrefs(md, ws)
    assert out == "见 ![chart](./chart.png)"
    assert "C:" not in out
    assert "Users" not in out


def test_long_task_guidance_names_internal_charts_dir():
    from coworker.agent import _LONG_TASK_GUIDANCE

    assert "._chemclaw/charts/" in _LONG_TASK_GUIDANCE
    assert "workspace root" in _LONG_TASK_GUIDANCE
