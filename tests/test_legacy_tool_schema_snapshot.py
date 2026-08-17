"""HARD STOP D — capture legacy provider-visible tool schema parity snapshot.

Records representative agent/persona/session tool names + schema fingerprints
BEFORE Step 34 tool projection, so HARD STOP E can compare.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from coworker.agent import build_engine
from coworker.agents import chat_agent, get_agent
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient


class _Stub(ProviderClient):
    def complete(self, *, model, messages, tools=None, **settings):
        return AssistantTurn(text="ok")

    def capabilities(self, model):
        return ModelCapabilities()

    def stream(self, *, model, messages, tools=None, **settings):
        yield from ()


def _fingerprint(schema: dict) -> str:
    blob = json.dumps(schema, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _snapshot_engine(label: str, engine) -> dict:
    names = sorted(engine.registry.names())
    schemas = engine.registry.schemas()
    by_name = {}
    for sch in schemas:
        fn = (sch.get("function") or {}) if isinstance(sch, dict) else {}
        name = fn.get("name") or sch.get("name")
        if not name:
            continue
        by_name[name] = {
            "fingerprint": _fingerprint(sch),
            "param_keys": sorted(
                ((fn.get("parameters") or {}).get("properties") or {}).keys()
            ),
        }
    return {
        "label": label,
        "agent_name": getattr(engine, "agent_name", None),
        "tool_count": len(names),
        "tool_names": names,
        "schemas": by_name,
    }


def test_legacy_provider_visible_schema_parity_snapshot(tmp_path):
    """Write snapshot under docs for HARD STOP E comparison; assert non-empty."""
    out_dir = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "superpowers"
        / "plans"
        / "fixtures"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "hard-stop-d-legacy-tool-schema-snapshot.json"

    snapshots = []
    # Default ChemClaw / cowork (knowledge family with workspace tools).
    cowork = build_engine(
        agent=get_agent("cowork"),
        workspace=tmp_path,
        provider=_Stub(),
        question_asker=lambda *a, **k: {"answers": []},
    )
    snapshots.append(_snapshot_engine("cowork_default_session", cowork))

    # Chat surface — typically fewer tools.
    chat = build_engine(agent=chat_agent(), provider=_Stub())
    snapshots.append(_snapshot_engine("chat_agent_session", chat))

    # Built-in persona: chain-lobster if present, else cowork again tagged.
    try:
        persona = get_agent("chain-lobster")
    except Exception:  # noqa: BLE001
        persona = get_agent("cowork")
    persona_engine = build_engine(
        agent=persona,
        workspace=tmp_path,
        provider=_Stub(),
        question_asker=lambda *a, **k: {"answers": []},
    )
    snapshots.append(
        _snapshot_engine(f"persona_{getattr(persona, 'name', 'unknown')}", persona_engine)
    )

    payload = {
        "phase": "HARD_STOP_D",
        "purpose": "legacy provider-visible tool-name/schema parity before Step 34",
        "note": "tool_projection_enabled not introduced; no aggressive filtering applied",
        "snapshots": snapshots,
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    assert out_path.is_file()
    for snap in snapshots:
        assert snap["tool_count"] > 0
        assert snap["tool_names"]
        # Parity baseline: projection must not silently drop unknown tools later.
        assert "ask_user" in snap["tool_names"] or snap["label"].startswith("chat")
