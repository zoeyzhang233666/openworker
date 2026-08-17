"""list_artifacts must never descend into OS application-data directories.

On macOS 14+, merely traversing ~/Library/Application Support (other apps' containers)
trips the App Data TCC protection and the user gets an alarming "OpenWorker would like to
access data from other apps" prompt. The artifacts panel refreshes after every turn, so a
home-directory workspace produced that prompt unprompted. Pruning must happen DURING the
walk (rglob descends first and filters after, which is what caused the bug).
"""

import os

from coworker.server.manager import SessionManager
from coworker.sessions import SessionRecord
from coworker.tools.search import OS_DATA_DIRS


def _save_session(manager: SessionManager, session_id: str, workspace: str, agent: str) -> None:
    manager.session_store.save(
        SessionRecord(
            session_id=session_id,
            workspace=workspace,
            model="m",
            mode="interactive",
            agent=agent,
        )
    )


def _ws(tmp_path):
    ws = tmp_path / "home"
    (ws / "Library" / "Application Support" / "SomeOtherApp").mkdir(parents=True)
    (ws / "Library" / "Application Support" / "SomeOtherApp" / "secrets.json").write_text("{}")
    (ws / "Library" / "notes.md").write_text("# private")
    (ws / "node_modules" / "pkg").mkdir(parents=True)
    (ws / "node_modules" / "pkg" / "readme.md").write_text("# dep")
    (ws / "report.md").write_text("# real artifact")
    return ws


def test_os_data_dirs_are_not_traversed(tmp_path, monkeypatch):
    ws = _ws(tmp_path)
    walked: list[str] = []
    real_walk = os.walk

    def spy(top, *a, **k):
        for dirpath, dirs, files in real_walk(top, *a, **k):
            walked.append(dirpath)
            yield dirpath, dirs, files

    monkeypatch.setattr("coworker.server.manager.os.walk", spy)
    m = SessionManager(data_dir=tmp_path / "data", workspace=str(ws))
    names = [a["name"] for a in m.list_artifacts("s1")]

    assert "report.md" in names
    # The private file is skipped AND its directory was never entered (the TCC trigger).
    assert "notes.md" not in names
    assert "secrets.json" not in names
    assert not any("Library" in p for p in walked), f"descended into Library: {walked}"
    assert not any("node_modules" in p for p in walked)


def test_os_data_dirs_cover_mac_and_windows():
    assert {"Library", "AppData", "Application Data"} <= OS_DATA_DIRS


def test_list_artifacts_hides_dot_chemclaw_process_files(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "report.md").write_text("# ok", encoding="utf-8")
    progress = ws / "._chemclaw" / "task-progress.md"
    progress.parent.mkdir(parents=True)
    progress.write_text("# leftover\n", encoding="utf-8")

    m = SessionManager(data_dir=tmp_path / "data", workspace=str(ws))
    arts = m.list_artifacts("s1")
    paths = [a["path"].replace("\\", "/") for a in arts]
    assert "report.md" in paths
    assert "._chemclaw/task-progress.md" not in paths


def test_artifact_target_error_keys(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    m = SessionManager(data_dir=tmp_path / "data", workspace=str(ws))

    target, err = m._artifact_target("s1", "missing.md")
    assert target is None and err == "artifact_not_found"

    target, err = m._artifact_target("s1", "._chemclaw/task-progress.md")
    assert target is None and err == "artifact_not_found"

    target, err = m._artifact_target("s1", "../outside.md")
    assert target is None and err == "artifact_path_mismatch"


def test_list_artifacts_root_markdown_is_visible(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "report.md").write_text("# report", encoding="utf-8")
    m = SessionManager(data_dir=tmp_path / "data", workspace=str(ws))
    _save_session(m, "s-root", str(ws), "cowork")
    paths = [a["path"].replace("\\", "/") for a in m.list_artifacts("s-root")]
    assert "report.md" in paths


def test_list_artifacts_hides_chemclaw_charts_workdir(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "report.md").write_text("# report", encoding="utf-8")
    charts = ws / "._chemclaw" / "charts"
    charts.mkdir(parents=True)
    (charts / "plot.py").write_text("print(1)\n", encoding="utf-8")
    (charts / "raw.png").write_bytes(b"\x89PNG")
    (charts / "temp.json").write_text("{}", encoding="utf-8")

    m = SessionManager(data_dir=tmp_path / "data", workspace=str(ws))
    _save_session(m, "s-hide", str(ws), "cowork")
    paths = [a["path"].replace("\\", "/") for a in m.list_artifacts("s-hide")]
    assert "report.md" in paths
    assert "._chemclaw/charts/plot.py" not in paths
    assert "._chemclaw/charts/raw.png" not in paths
    assert "._chemclaw/charts/temp.json" not in paths


def test_list_artifacts_shows_root_images_not_chart_scripts(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "report.md").write_text("# report", encoding="utf-8")
    (ws / "price.png").write_bytes(b"\x89PNG")
    (ws / "inventory.png").write_bytes(b"\x89PNG")
    leftover = ws / "charts"
    leftover.mkdir()
    (leftover / "plot.py").write_text("print(1)\n", encoding="utf-8")
    (leftover / "raw.png").write_bytes(b"\x89PNG")

    m = SessionManager(data_dir=tmp_path / "data", workspace=str(ws))
    _save_session(m, "s-know", str(ws), "cowork")
    paths = [a["path"].replace("\\", "/") for a in m.list_artifacts("s-know")]
    assert "report.md" in paths
    assert "price.png" in paths
    assert "inventory.png" in paths
    assert "charts/plot.py" not in paths
    assert "charts/raw.png" not in paths


def test_list_artifacts_code_session_still_lists_charts_scripts(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    charts = ws / "charts"
    charts.mkdir()
    (charts / "plot.py").write_text("print(1)\n", encoding="utf-8")

    m = SessionManager(data_dir=tmp_path / "data", workspace=str(ws))
    _save_session(m, "s-code", str(ws), "code")
    paths = [a["path"].replace("\\", "/") for a in m.list_artifacts("s-code")]
    assert "charts/plot.py" in paths


def test_artifact_target_reads_relative_and_in_workspace_absolute(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    target_file = ws / "甲醇行情周报_2026W33.md"
    target_file.write_text("# week", encoding="utf-8")
    m = SessionManager(data_dir=tmp_path / "data", workspace=str(ws))
    _save_session(m, "s-read", str(ws), "cowork")

    target, err = m._artifact_target("s-read", "甲醇行情周报_2026W33.md")
    assert err is None and target == target_file.resolve()

    target, err = m._artifact_target("s-read", str(target_file))
    assert err is None and target == target_file.resolve()

    other = tmp_path / "other"
    other.mkdir()
    secret = other / "secret.md"
    secret.write_text("nope", encoding="utf-8")
    target, err = m._artifact_target("s-read", str(secret))
    assert target is None and err == "artifact_path_mismatch"
