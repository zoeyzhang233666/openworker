"""ChemClaw packaging / runtime path contracts."""

from __future__ import annotations

import os
from pathlib import Path

from coworker.runtime_paths import bundled_skills_dir, builtin_personas_dir
from coworker.secrets import state_dir
from coworker.skills.bootstrap import BUNDLED_DIR


def test_bundled_skills_dir_points_at_worktree_assets():
    d = bundled_skills_dir()
    assert d.is_dir()
    assert (d / "chem-platform-rewrite" / "SKILL.md").is_file()
    assert BUNDLED_DIR.resolve() == d.resolve()


def test_builtin_personas_dir_includes_sales_lobsters():
    d = builtin_personas_dir()
    assert d.is_dir()
    assert (d / "platform-rewrite-lobster.md").is_file()
    assert (d / "export-sales-lobster.md").is_file()


def test_default_state_dir_is_chemclaw_not_legacy_coworker(monkeypatch, tmp_path):
    monkeypatch.delenv("COWORKER_STATE_DIR", raising=False)
    if os.name == "nt":
        monkeypatch.setenv("APPDATA", str(tmp_path))
        assert state_dir() == Path(tmp_path) / "ChemClaw"
    else:
        monkeypatch.setenv("HOME", str(tmp_path))
        assert state_dir() == Path(tmp_path) / ".config" / "chemclaw"
