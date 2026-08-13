from pathlib import Path

from coworker.skills.bootstrap import (
    list_bundled_skill_names,
    seed_bundled_skills,
    sync_managed_lexicon,
)
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


def test_sync_managed_lexicon_upgrades_without_clobbering_user(tmp_path: Path) -> None:
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    seed_bundled_skills(store)
    skill = store.global_dir / "chem-content-policy"
    managed = skill / "references" / "lexicon" / "managed"
    user = skill / "references" / "lexicon" / "user.csv"
    assert (managed / "base.csv").is_file()
    user.write_text(
        "rule_id,term,platform,locale,category,severity,action,replacement_strategy,notes\n"
        "custom-ban,用户专属词,all,zh-CN,custom,block,rewrite,删除,keep-me\n",
        encoding="utf-8",
    )
    user_before = user.read_text(encoding="utf-8")

    # Simulate older installed managed lexicon.
    (managed / "rule_version.txt").write_text("0.9.0", encoding="utf-8")
    (managed / "base.csv").write_text(
        "rule_id,term,platform,locale,category,severity,action,replacement_strategy,notes\n"
        "old-only,旧词,all,zh-CN,test,block,rewrite,删除,stale\n",
        encoding="utf-8",
    )

    updated = sync_managed_lexicon(store)
    assert "chem-content-policy" in updated
    assert (managed / "rule_version.txt").read_text(encoding="utf-8").strip() == "1.0.0"
    new_csv = (managed / "base.csv").read_text(encoding="utf-8")
    assert "绝对安全" in new_csv
    assert "旧词" not in new_csv
    assert user.read_text(encoding="utf-8") == user_before

    # Second sync with matching version is a no-op for managed content.
    assert sync_managed_lexicon(store) == []
    assert user.read_text(encoding="utf-8") == user_before


def test_sync_managed_lexicon_migrates_legacy_base_csv(tmp_path: Path) -> None:
    import shutil

    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    seed_bundled_skills(store)
    skill = store.global_dir / "chem-content-policy"
    lexicon = skill / "references" / "lexicon"
    managed = lexicon / "managed"
    legacy_body = (managed / "base.csv").read_text(encoding="utf-8")
    # Downgrade layout to pre-M3.
    shutil.rmtree(managed)
    (lexicon / "base.csv").write_text(legacy_body, encoding="utf-8")
    user = lexicon / "user.csv"
    if user.exists():
        user.unlink()

    updated = sync_managed_lexicon(store)
    assert "chem-content-policy" in updated
    assert (managed / "base.csv").is_file()
    assert not (lexicon / "base.csv").exists()
    assert user.is_file()
