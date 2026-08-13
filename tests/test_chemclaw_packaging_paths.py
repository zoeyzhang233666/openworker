"""ChemClaw packaging / runtime path contracts."""

from __future__ import annotations

import os
from pathlib import Path

from coworker.runtime_paths import bundled_skills_dir, builtin_personas_dir
from coworker.secrets import state_dir
from coworker.skills.base import SkillLoader
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


def test_content_policy_packaging_assets_and_load_skill():
    """M3: package-data tree must ship managed lexicon + scripts; SkillLoader resolves."""
    d = bundled_skills_dir()
    skill = d / "chem-content-policy"
    assert (skill / "SKILL.md").is_file()
    assert (skill / "scripts" / "scan_content.py").is_file()
    assert (skill / "references" / "lexicon" / "managed" / "base.csv").is_file()
    assert (skill / "references" / "lexicon" / "managed" / "rule_version.txt").is_file()
    assert (skill / "references" / "lexicon" / "user.csv").is_file()
    assert (skill / "schemas" / "content-scan-output.schema.json").is_file()

    loader = SkillLoader([d])
    loaded = loader.get("chem-content-policy")
    assert loaded is not None
    assert loaded.name == "chem-content-policy"
    assert loaded.path
    skill_dir = Path(loaded.path)
    assert (skill_dir / "scripts" / "scan_content.py").is_file()
    assert (skill_dir / "references" / "lexicon" / "managed" / "base.csv").is_file()


def test_staged_sidecar_internal_content_policy_if_present():
    """If a local packaging dist exists, assert lexicon + scripts are inside _internal."""
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root
        / "packaging"
        / "dist"
        / "openworker-server"
        / "_internal"
        / "coworker"
        / "skills"
        / "bundled"
        / "chem-content-policy",
        root
        / "surfaces"
        / "gui"
        / "src-tauri"
        / "target"
        / "release"
        / "openworker-server"
        / "_internal"
        / "coworker"
        / "skills"
        / "bundled"
        / "chem-content-policy",
    ]
    present = [p for p in candidates if p.is_dir()]
    if not present:
        return
    for skill in present:
        assert (skill / "SKILL.md").is_file()
        # Older staged builds may still have pre-M3 base.csv; accept either until rebuild.
        managed = skill / "references" / "lexicon" / "managed" / "base.csv"
        legacy = skill / "references" / "lexicon" / "base.csv"
        assert managed.is_file() or legacy.is_file()
        assert (skill / "scripts" / "scan_content.py").is_file()
