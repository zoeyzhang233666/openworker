import uuid
from pathlib import Path

from coworker.skills.bootstrap import list_bundled_skill_names, seed_bundled_skills
from coworker.skills.store import SkillStore


def test_seed_bundled_skills_installs_full_pack_once(tmp_path) -> None:
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = seed_bundled_skills(store)
    names = set(installed)
    assert "产业链层级测绘" in names
    assert "chem-tech-map" in names
    assert "excel-xlsx" in names
    assert "computer-use" not in names
    assert "serenity.industry-chain-mapping" not in names
    assert (tmp_path / "skills" / "产业链层级测绘" / "SKILL.md").is_file()
    assert (tmp_path / "skills" / "chem-tech-map" / "references").is_dir() or (
        tmp_path / "skills" / "chem-tech-map" / "SKILL.md"
    ).is_file()
    # Second seed is a no-op.
    assert seed_bundled_skills(store) == []


def test_delete_bundled_skill_does_not_reseed(tmp_path) -> None:
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    seed_bundled_skills(store)
    assert "产业链层级测绘" in list_bundled_skill_names()
    store.delete("产业链层级测绘")
    assert "产业链层级测绘" in store.uninstalled_bundled_names()
    assert not (tmp_path / "skills" / "产业链层级测绘").exists()
    # Reseed must not bring it back.
    assert "产业链层级测绘" not in seed_bundled_skills(store)
    assert not (tmp_path / "skills" / "产业链层级测绘").exists()
