"""Session workspace must not follow shell cwd into ._chemclaw/."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from coworker.chemclaw_paths import stable_session_workspace
from coworker.permissions import Mode
from coworker.server.manager import SessionManager
from coworker.sessions import SessionRecord


def test_stable_session_workspace_strips_chemclaw_suffix():
    poisoned = r"C:\Users\EDY\OpenWorker\fca038da-916\._chemclaw\charts\chart-image"
    assert str(stable_session_workspace(poisoned)).replace("\\", "/") == (
        "C:/Users/EDY/OpenWorker/fca038da-916"
    )
    assert stable_session_workspace(Path("/tmp/sess/._chemclaw/charts/x")) == Path(
        "/tmp/sess"
    )
    clean = Path("/tmp/sess")
    assert stable_session_workspace(clean) == clean


def test_save_persists_primary_root_not_shell_cwd(tmp_path):
    scratch = tmp_path / "sess"
    scratch.mkdir()
    charts = scratch / "._chemclaw" / "charts" / "chart-image"
    charts.mkdir(parents=True)

    m = SessionManager(data_dir=tmp_path / "data", workspace=str(scratch))
    engine = SimpleNamespace(
        roots=[SimpleNamespace(path=scratch.resolve(), writable=True, label="scratch")],
        permissions=SimpleNamespace(workspace_root=scratch.resolve(), mode=Mode.AUTO),
        executor=SimpleNamespace(cwd=str(charts)),
        model="m",
        messages=[],
        agent_name="cowork",
        compaction_state=None,
    )
    # Mode.value for PermissionEngine-like object
    engine.permissions.mode = Mode.AUTO

    m.save("s-cwd", engine)
    loaded = m.session_store.load("s-cwd")
    assert loaded is not None
    assert Path(loaded.workspace).resolve() == scratch.resolve()
    assert "._chemclaw" not in loaded.workspace.replace("\\", "/")


def test_list_artifacts_heals_poisoned_workspace(tmp_path):
    scratch = tmp_path / "sess"
    scratch.mkdir()
    (scratch / "report.md").write_text("# ok", encoding="utf-8")
    (scratch / "price.png").write_bytes(b"\x89PNG")
    charts = scratch / "._chemclaw" / "charts" / "chart-image"
    charts.mkdir(parents=True)
    (charts / "package.json").write_text("{}", encoding="utf-8")
    (charts / "package-lock.json").write_text("{}", encoding="utf-8")

    m = SessionManager(data_dir=tmp_path / "data", workspace=str(scratch))
    m.session_store.save(
        SessionRecord(
            session_id="s-poison",
            workspace=str(charts),
            model="m",
            mode="interactive",
            agent="cowork",
        )
    )

    arts = m.list_artifacts("s-poison")
    paths = [a["path"].replace("\\", "/") for a in arts]
    assert "report.md" in paths
    assert "price.png" in paths
    assert "package.json" not in paths
    assert not any(p.endswith("package-lock.json") for p in paths)

    healed = m.session_store.load("s-poison")
    assert Path(healed.workspace).resolve() == scratch.resolve()
