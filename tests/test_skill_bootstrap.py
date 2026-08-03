import uuid
from pathlib import Path

from coworker.skills.bootstrap import seed_bundled_skills
from coworker.skills.store import SkillStore


def test_seed_bundled_skills_installs_serenity_once() -> None:
    base = Path("D:/OpenWorker/.chemclaw-dev/test-bootstrap") / uuid.uuid4().hex
    base.mkdir(parents=True, exist_ok=True)
    try:
        store = SkillStore(global_dir=base / "skills")
        installed = seed_bundled_skills(store)
        assert "serenity.industry-chain-mapping" in installed
        skill_md = base / "skills" / "serenity.industry-chain-mapping" / "SKILL.md"
        assert skill_md.is_file()
        text = skill_md.read_text(encoding="utf-8")
        assert "name: serenity.industry-chain-mapping" in text
        assert seed_bundled_skills(store) == []
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)
