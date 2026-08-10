"""Knowledge sessions must read skill resources_path via readonly roots."""

from __future__ import annotations

from pathlib import Path

from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient
from coworker.roots import SYSTEM_SKILLS_LABEL
from coworker.server import SessionManager


class _Provider(ProviderClient):
    def complete(self, *, model, messages, tools=None, **s):
        return AssistantTurn(text="", finish_reason="stop")

    def capabilities(self, model):
        return ModelCapabilities()


def _manager(tmp_path: Path) -> SessionManager:
    data = tmp_path / "data"
    mgr = SessionManager(data_dir=data, provider=_Provider())
    mgr._prefs["scratch_base"] = str(tmp_path / "scratchbase")
    return mgr


def test_knowledge_engine_can_read_skill_references(tmp_path: Path) -> None:
    mgr = _manager(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    mgr.set_persona_enabled("platform-rewrite-lobster", True)
    engine = mgr.get_engine(
        "skill-roots-read",
        agent="platform-rewrite-lobster",
        workspace=str(workspace),
    )
    assert engine is not None

    loaded = engine.registry.execute("load_skill", {"name": "chem-rewrite-brief"})
    assert "error" not in loaded, loaded
    ref = Path(loaded["resources_path"]) / "references" / "fact-boundary-rules.md"
    assert ref.is_file()

    result = engine.registry.execute("read_file", {"path": str(ref)})
    text = result if isinstance(result, str) else str(result)
    assert "error" not in text.lower() or "Path escapes" not in text
    assert "immutable" in text.lower() or "不可变" in text or "事实" in text


def test_skill_root_is_readonly_for_writes(tmp_path: Path) -> None:
    mgr = _manager(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    mgr.set_persona_enabled("platform-rewrite-lobster", True)
    engine = mgr.get_engine(
        "skill-roots-write",
        agent="platform-rewrite-lobster",
        workspace=str(workspace),
    )
    assert engine is not None
    skills_root = (tmp_path / "data" / "skills").resolve()
    target = skills_root / "chem-rewrite-brief" / "references" / "should-not-write.txt"

    # Permission layer blocks writes into readonly roots without approval prompt
    decision = engine.permissions.evaluate(
        "write_file",
        {"path": str(target), "content": "nope"},
        engine.registry.get("write_file").metadata,
    )
    assert decision.allowed is False
    assert decision.needs_user is False


def test_skill_roots_not_persisted_in_extra_roots(tmp_path: Path) -> None:
    mgr = _manager(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    user_folder = tmp_path / "user-docs"
    user_folder.mkdir()
    mgr.set_persona_enabled("platform-rewrite-lobster", True)
    sid = "skill-roots-persist"
    engine = mgr.get_engine(
        sid,
        agent="platform-rewrite-lobster",
        workspace=str(workspace),
    )
    assert engine is not None

    skills_root = (tmp_path / "data" / "skills").resolve()
    root_paths = {r.path for r in engine.roots}
    assert skills_root in root_paths
    skill_entries = [r for r in engine.roots if r.label == SYSTEM_SKILLS_LABEL]
    assert skill_entries
    assert all(not r.writable for r in skill_entries)

    mgr.add_root(sid, str(user_folder), writable=False)
    # Persist session so extra_roots are on disk (same as a completed turn).
    mgr.save(sid, engine)
    record = mgr.session_store.load(sid)
    assert record is not None
    persisted_paths = {Path(r["path"]).resolve() for r in (record.extra_roots or [])}
    assert skills_root not in persisted_paths
    assert user_folder.resolve() in persisted_paths

    # Cold get_roots still exposes skills as non-removable system root
    mgr._engines.pop(sid, None)
    cold = {Path(r["path"]).resolve(): r for r in mgr.get_roots(sid)}
    assert skills_root in cold
    assert cold[skills_root].get("removable") is False
    assert cold[skills_root]["writable"] is False

    # Cannot remove system skills root
    assert mgr.remove_root(sid, str(skills_root))["ok"] is False
