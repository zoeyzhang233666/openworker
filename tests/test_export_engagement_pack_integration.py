"""Integration contract for export-engagement builtin pack."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from coworker.personas.registry import PersonaRegistry
from coworker.secrets import state_dir
from coworker.server.manager import SessionManager
from coworker.skills import SkillLoader
from coworker.skills.bootstrap import BUNDLED_DIR, seed_bundled_skills
from coworker.skills.store import SkillStore


EXPECTED_SKILLS = (
    "chem-sales-engagement",
    "chem-product-intelligence",
    "chem-sales-quality-check",
)


def test_export_engagement_pack_seeds_and_matches_persona(tmp_path: Path) -> None:
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")
    assert registry.skill_ids("export-engagement-lobster") == list(EXPECTED_SKILLS)
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


def test_export_engagement_not_default_agent(tmp_path: Path) -> None:
    registry = PersonaRegistry(state_path=tmp_path / "personas.json")
    assert "export-engagement-lobster" in registry.ids()
    assert registry.default_id() == "cowork"
    assert registry.is_enabled("export-engagement-lobster") is False


def test_export_engagement_bundle_excludes_bytecode() -> None:
    for name in ("chem-sales-engagement", "chem-sales-quality-check"):
        generated = [
            p
            for p in (BUNDLED_DIR / name).rglob("*")
            if p.name == "__pycache__" or p.suffix == ".pyc"
        ]
        assert generated == []


def test_session_manager_loads_export_engagement_skills(tmp_path: Path) -> None:
    manager_data = tmp_path / "manager-data"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    assert manager_data.resolve() != state_dir().resolve()
    manager = SessionManager(data_dir=manager_data)
    manager.set_persona_enabled("export-engagement-lobster", True)
    engine = manager.get_engine(
        "export-engagement-runtime",
        agent="export-engagement-lobster",
        workspace=str(workspace),
    )
    assert engine is not None
    for name in EXPECTED_SKILLS:
        result = engine.registry.execute("load_skill", {"name": name})
        assert "error" not in result, result
        assert Path(result["resources_path"]).resolve() == (
            manager_data / "skills" / name
        ).resolve()


def test_forward_no_email_passes_quality_gate_role_only():
    script = BUNDLED_DIR / "chem-sales-quality-check" / "scripts" / "check_outreach.py"
    spec = importlib.util.spec_from_file_location("check_outreach_fwd", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    draft = {
        "schema_version": "chemclaw.outreach-draft.v1",
        "draft_id": "draft-de-forward",
        "language": "de",
        "channel": "email",
        "recipient_role": "Purchasing Manager",
        "recipient_email": None,
        "recipient_name": None,
        "subject": "Natriumbenzoat Angebot",
        "body": "Guten Tag, wir liefern Natriumbenzoat. Bitte teilen Sie die Einkaufs-E-Mail mit.",
        "lead_or_opportunity_id": "lead-de-1",
        "evidence_ids": ["ev-1"],
        "price_evidence_ids": [],
        "has_price_claim": False,
        "has_delivery_claim": False,
    }
    result = module.check_outreach(draft)
    assert result["verdict"] == "pass"
    assert result["recommended_action"] == "ready_for_human_send"
    assert draft["recipient_email"] is None
