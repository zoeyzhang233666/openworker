"""Install real skill trees with development bytecode present at the source."""

from pathlib import Path
import io
import zipfile

import pytest

from coworker.personas.package_install import preview_or_install
from coworker.personas.registry import PersonaRegistry
from coworker.skills import bootstrap
from coworker.skills.store import SkillStore


@pytest.mark.parametrize("entry", ["seed", "upload", "overwrite", "zip"])
def test_skill_install_excludes_cache_and_keeps_resources(tmp_path, monkeypatch, entry):
    package = tmp_path / "package"
    source = package / "skills" / "sample"
    resources = {
        "SKILL.md": "---\nname: sample\ndescription: test skill\n---\n研究资料。\n",
        "scripts/run.py": "print('ok')\n",
        "references/guide.md": "参考资料",
        "assets/chart.json": '{"version":1}',
        "requirements.txt": "example==1.0\n",
        "config.example.json": '{"endpoint":""}',
    }
    generated = {
        "scripts/__pycache__/run.cpython-314.pyc": "old cache",
        "scripts/run.pyc": "legacy cache",
        "references/nested/__pycache__/module.pyc": "nested cache",
        "scripts/run.pyo": "old optimized cache",
    }
    for rel, content in {**resources, **generated}.items():
        path = source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    store = SkillStore(global_dir=tmp_path / "installed", settings_path=tmp_path / "settings.json")
    target = store.global_dir / "sample"
    if entry == "seed":
        monkeypatch.setattr(bootstrap, "BUNDLED_DIR", package / "skills")
        assert bootstrap.seed_bundled_skills(store) == ["sample"]
    elif entry == "zip":
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for rel in {**resources, **generated}:
                archive.write(source / rel, "sample/" + rel)
        preview = store.stage_upload(buffer.getvalue(), "sample.zip")
        assert set(preview["files"]) == set(resources) - {"SKILL.md"}
        store.confirm_upload(preview["token"])
    else:
        registry = PersonaRegistry(state_path=tmp_path / "personas.json")
        if entry == "overwrite":
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text(resources["SKILL.md"], encoding="utf-8")
            (target / "obsolete.py").write_text("old", encoding="utf-8")
        result = preview_or_install(registry, store, package, decisions={"skill:sample": "overwrite"})
        assert result["ok"] and result["installed"]["skills"] == ["sample"]
    actual = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
    assert actual == set(resources)
    for rel, content in resources.items():
        if rel != "SKILL.md":  # upload records frontmatter provenance
            assert (target / rel).read_text(encoding="utf-8") == content
    for rel in generated:
        assert (source / rel).is_file()  # no cleanup of caller-owned source
    assert not list(target.rglob("__pycache__"))
