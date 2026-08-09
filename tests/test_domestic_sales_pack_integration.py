"""End-to-end discovery contract for the built-in domestic-sales capability pack."""

from __future__ import annotations

from pathlib import Path

from coworker.personas.registry import PersonaRegistry
from coworker.secrets import state_dir
from coworker.server.manager import SessionManager
from coworker.skills import SkillLoader
from coworker.skills.bootstrap import BUNDLED_DIR, seed_bundled_skills
from coworker.skills.store import SkillStore


EXPECTED_SKILLS = (
    "chem-domestic-prospecting",
    "chem-product-intelligence",
    "chem-buyer-discovery",
    "chem-company-qualification",
    "chem-lead-ranking",
    "chem-lead-list",
)


def test_domestic_sales_pack_seeds_with_assets_and_matches_persona(tmp_path: Path) -> None:
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))

    registry = PersonaRegistry(state_path=tmp_path / "personas.json")
    assert registry.skill_ids("domestic-sales-lobster") == list(EXPECTED_SKILLS)
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


def test_domestic_sales_pack_does_not_replace_default_agent(tmp_path: Path) -> None:
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")

    assert "domestic-sales-lobster" in registry.ids()
    assert registry.default_id() == "cowork"
    assert registry.is_enabled("domestic-sales-lobster") is False


def test_domestic_sales_bundle_excludes_generated_python_bytecode() -> None:
    source = BUNDLED_DIR / "chem-domestic-prospecting"
    generated = [
        path
        for path in source.rglob("*")
        if path.name == "__pycache__" or path.suffix == ".pyc"
    ]
    assert generated == [], f"generated files would be seeded: {generated}"


def test_session_manager_loads_seeded_domestic_persona_skills_from_custom_data_dir(
    tmp_path: Path,
) -> None:
    manager_data = tmp_path / "manager-data"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    assert manager_data.resolve() != state_dir().resolve()

    manager = SessionManager(data_dir=manager_data)
    manager.set_persona_enabled("domestic-sales-lobster", True)
    engine = manager.get_engine(
        "domestic-sales-runtime",
        agent="domestic-sales-lobster",
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


def test_oral_jiangsu_park_scenario_scores_needs_review_without_placeholders():
    """江苏园区 + 苯甲酸钠 + 下游厂，无企业标识 → NeedsReview / research_first."""
    import importlib.util
    import json

    script = (
        BUNDLED_DIR / "chem-lead-ranking" / "scripts" / "score_lead.py"
    )
    spec = importlib.util.spec_from_file_location("domestic_forward_score", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = {
        "schema_version": "chemclaw.lead-ranking.input.v1",
        "as_of": "2026-08-07",
        "rule_set": {
            "id": "chem-lead-fit",
            "version": "1.0.0",
            "weights": {
                "sku_application": 30,
                "role_icp": 20,
                "business_signal": 20,
                "market_fit": 10,
                "contactability": 10,
                "signal_recency": 10,
            },
        },
        "lead": {
            "id": "oral-jiangsu-benzoate",
            "qualification_status": "NeedsReview",
            "entity_resolution": "unresolved",
            "features": {
                key: {"evidence_ids": []}
                for key in (
                    "sku_application",
                    "role_icp",
                    "business_signal",
                    "market_fit",
                    "contactability",
                    "signal_recency",
                )
            },
        },
        "evidence": [],
    }
    result = module.score_lead(payload)
    assert result["recommended_action"] == "research_first"
    assert result["lead_fit"]["score"] == 0.0
    assert result["evidence_confidence"]["score"] == 0.0

    bad = json.loads(json.dumps(payload))
    bad["lead"]["qualification_status"] = "Qualified"
    bad["lead"]["entity_resolution"] = "resolved"
    bad["evidence"] = [
        {
            "id": "e1",
            "source": {
                "type": "official_website",
                "url": "task-provided:jiangsu-oral",
                "file": None,
                "record_id": None,
            },
            "title": "Oral claim",
            "raw_fact": "user said so",
            "supports_claim": "entity",
            "supports": ["entity", "sku_application", "role_icp"],
            "polarity": "supports",
            "tier": "A",
            "independence_group": "oral",
            "event_date": "2026-07-01",
            "collected_at": "2026-07-02T12:00:00Z",
            "conflict": "none",
        }
    ]
    for key in bad["lead"]["features"]:
        bad["lead"]["features"][key] = {"evidence_ids": ["e1"]}
    try:
        module.score_lead(bad)
        raise AssertionError("placeholder locator must be rejected")
    except ValueError as exc:
        assert "placeholder locator" in str(exc)
