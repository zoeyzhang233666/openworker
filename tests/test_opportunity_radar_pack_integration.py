"""Integration contract for opportunity-radar builtin pack."""

from __future__ import annotations

from pathlib import Path

from coworker.personas.registry import PersonaRegistry
from coworker.secrets import state_dir
from coworker.server.manager import SessionManager
from coworker.skills import SkillLoader
from coworker.skills.bootstrap import BUNDLED_DIR, seed_bundled_skills
from coworker.skills.store import SkillStore


EXPECTED_SKILLS = (
    "chem-opportunity-radar",
    "chem-product-intelligence",
    "chem-company-qualification",
    "chem-opportunity-scoring",
)


def test_opportunity_radar_pack_seeds_and_matches_persona(tmp_path: Path) -> None:
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")
    assert registry.skill_ids("opportunity-radar-lobster") == list(EXPECTED_SKILLS)
    assert set(EXPECTED_SKILLS) <= installed
    loader = SkillLoader([store.global_dir])
    for name in EXPECTED_SKILLS:
        assert loader.get(name) is not None
        source = BUNDLED_DIR / name
        target = store.global_dir / name
        assert list((source / "references").glob("*.md"))
        assert list((source / "schemas").glob("*.json"))
        source_files = {
            p.relative_to(source): p.read_bytes()
            for p in source.rglob("*")
            if p.is_file()
        }
        target_files = {
            p.relative_to(target): p.read_bytes()
            for p in target.rglob("*")
            if p.is_file()
        }
        assert target_files == source_files


def test_opportunity_radar_not_default_agent(tmp_path: Path) -> None:
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")
    assert "opportunity-radar-lobster" in registry.ids()
    assert registry.default_id() == "cowork"
    assert registry.is_enabled("opportunity-radar-lobster") is False


def test_opportunity_radar_bundle_excludes_bytecode() -> None:
    for name in ("chem-opportunity-radar", "chem-opportunity-scoring"):
        generated = [
            p
            for p in (BUNDLED_DIR / name).rglob("*")
            if p.name == "__pycache__" or p.suffix == ".pyc"
        ]
        assert generated == []


def test_session_manager_loads_opportunity_radar_skills(tmp_path: Path) -> None:
    manager_data = tmp_path / "manager-data"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    assert manager_data.resolve() != state_dir().resolve()
    manager = SessionManager(data_dir=manager_data)
    manager.set_persona_enabled("opportunity-radar-lobster", True)
    engine = manager.get_engine(
        "opportunity-radar-runtime",
        agent="opportunity-radar-lobster",
        workspace=str(workspace),
    )
    assert engine is not None
    for name in EXPECTED_SKILLS:
        result = engine.registry.execute("load_skill", {"name": name})
        assert "error" not in result, result
        assert Path(result["resources_path"]).resolve() == (
            manager_data / "skills" / name
        ).resolve()


def test_oral_tender_forward_needs_review_not_actionable():
    import importlib.util

    script = BUNDLED_DIR / "chem-opportunity-scoring" / "scripts" / "score_opportunity.py"
    spec = importlib.util.spec_from_file_location("opp_forward", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = {
        "schema_version": "chemclaw.opportunity-scoring.input.v1",
        "as_of": "2026-08-07",
        "rule_set": {
            "id": "chem-opportunity-fit",
            "version": "1.0.0",
            "weights": {
                "signal_recency": 25,
                "entity": 20,
                "sku_relevance": 25,
                "urgency": 15,
                "actionability": 15,
            },
        },
        "opportunity": {
            "id": "oral-benzoate-tender",
            "status": "NeedsReview",
            "entity_resolution": "unresolved",
            "sku_relevance": "unknown",
            "features": {
                key: {"signal_ids": []}
                for key in (
                    "signal_recency",
                    "entity",
                    "sku_relevance",
                    "urgency",
                    "actionability",
                )
            },
        },
        "signals": [],
    }
    result = module.score_opportunity(payload)
    assert result["recommended_action"] == "research_first"
    assert result["opportunity_score"]["score"] == 0.0
