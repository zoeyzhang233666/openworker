"""End-to-end discovery contract for the built-in export-sales capability pack."""

from __future__ import annotations

from pathlib import Path

from coworker.personas.registry import PersonaRegistry
from coworker.secrets import state_dir
from coworker.server.manager import SessionManager
from coworker.skills import SkillLoader
from coworker.skills.bootstrap import BUNDLED_DIR, seed_bundled_skills
from coworker.skills.store import SkillStore


EXPECTED_SKILLS = (
    "chem-export-prospecting",
    "chem-product-intelligence",
    "chem-buyer-discovery",
    "chem-company-qualification",
    "chem-lead-ranking",
)


def test_export_sales_pack_seeds_with_assets_and_matches_persona(tmp_path: Path) -> None:
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))

    registry = PersonaRegistry(state_path=tmp_path / "personas.json")
    assert registry.skill_ids("export-sales-lobster") == list(EXPECTED_SKILLS)
    assert set(EXPECTED_SKILLS) <= installed

    loader = SkillLoader([store.global_dir])
    for name in EXPECTED_SKILLS:
        source = BUNDLED_DIR / name
        target = store.global_dir / name
        skill = loader.get(name)

        assert skill is not None
        assert skill.description.strip()
        assert skill.path == str(target)
        assert list((source / "references").glob("*.md"))
        assert list((source / "schemas").glob("*.json"))

        source_files = {
            path.relative_to(source): path.read_bytes()
            for path in source.rglob("*")
            if path.is_file()
        }
        target_files = {
            path.relative_to(target): path.read_bytes()
            for path in target.rglob("*")
            if path.is_file()
        }
        assert target_files == source_files

    assert (store.global_dir / "chem-product-intelligence" / "scripts").is_dir()
    assert (store.global_dir / "chem-lead-ranking" / "scripts").is_dir()


def test_export_sales_pack_does_not_replace_default_agent(tmp_path: Path) -> None:
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")

    assert "export-sales-lobster" in registry.ids()
    assert registry.default_id() == "cowork"
    assert registry.is_enabled("export-sales-lobster") is False


def test_export_sales_bundle_excludes_generated_python_bytecode() -> None:
    for name in EXPECTED_SKILLS:
        source = BUNDLED_DIR / name
        generated = [
            path
            for path in source.rglob("*")
            if path.name == "__pycache__" or path.suffix == ".pyc"
        ]
        assert generated == [], f"generated files would be seeded for {name}: {generated}"


def test_session_manager_loads_seeded_persona_skills_from_custom_data_dir(
    tmp_path: Path,
) -> None:
    manager_data = tmp_path / "manager-data"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    assert manager_data.resolve() != state_dir().resolve()

    manager = SessionManager(data_dir=manager_data)
    manager.set_persona_enabled("export-sales-lobster", True)
    engine = manager.get_engine(
        "export-sales-runtime",
        agent="export-sales-lobster",
        workspace=str(workspace),
    )

    assert engine is not None
    for name in EXPECTED_SKILLS:
        result = engine.registry.execute("load_skill", {"name": name})
        assert "error" not in result, result
        assert result["name"] == name
        assert result["instructions"].strip()
        assert Path(result["resources_path"]).resolve() == (
            manager_data / "skills" / name
        ).resolve()
