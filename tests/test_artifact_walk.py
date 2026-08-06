"""list_artifacts must never descend into OS application-data directories.

On macOS 14+, merely traversing ~/Library/Application Support (other apps' containers)
trips the App Data TCC protection and the user gets an alarming "OpenWorker would like to
access data from other apps" prompt. The artifacts panel refreshes after every turn, so a
home-directory workspace produced that prompt unprompted. Pruning must happen DURING the
walk (rglob descends first and filters after, which is what caused the bug).
"""

import os

from coworker.server.manager import SessionManager
from coworker.tools.search import OS_DATA_DIRS


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
