"""D-167 builtin MCP seed + API guards."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coworker.mcp import builtin as mcp_builtin
from coworker.mcp.builtin import (
    encode_secrets_file,
    obfuscate_payload,
    deobfuscate_payload,
    seed_builtin_mcp,
)
from coworker.mcp.config import put_global_server, read_global
from coworker.server.manager import SessionManager, _redact


@pytest.fixture
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "state"
    root.mkdir()
    monkeypatch.setenv("COWORKER_STATE_DIR", str(root))
    return root


def test_obfuscate_roundtrip():
    payload = {"tokens": {"chem-data-hub": "tok_test"}, "urls": {}}
    blob = obfuscate_payload(payload)
    assert blob.startswith("CCBM1.")
    assert "tok_test" not in blob
    assert deobfuscate_payload(blob) == payload


def test_seed_writes_mcp_json_with_var_and_dotenv(
    state: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    bundle = tmp_path / "builtin_mcp.bundle"
    bundle.write_text(
        encode_secrets_file(
            {
                "tokens": {"chem-data-hub": "secret_token_abc"},
                "urls": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CHEMCLAW_BUILTIN_MCP_BUNDLE", str(bundle))

    seeded = seed_builtin_mcp(state_dir=state)
    assert "chem-data-hub" in seeded
    raw = read_global()["chem-data-hub"]
    assert raw.get("chemclaw_builtin") is True
    assert raw["url"] == "https://datahub.chem-cloud.cn/mcp"
    assert "${CHEMCLAW_BUILTIN_MCP_CHEM_DATA_HUB}" in raw["headers"]["Authorization"]
    assert "secret_token_abc" not in json.dumps(raw)

    dotenv = (state / ".env").read_text(encoding="utf-8")
    assert "CHEMCLAW_BUILTIN_MCP_CHEM_DATA_HUB=secret_token_abc" in dotenv
    assert "secret_token_abc" not in raw["headers"]["Authorization"]


def test_seed_skips_user_owned_server(
    state: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    put_global_server(
        "chem-data-hub",
        {
            "type": "http",
            "url": "https://example.com/mcp",
            "headers": {"Authorization": "Bearer user_plain"},
            "enabled": True,
        },
    )
    bundle = tmp_path / "b.bundle"
    bundle.write_text(
        encode_secrets_file({"tokens": {"chem-data-hub": "bundled"}, "urls": {}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("CHEMCLAW_BUILTIN_MCP_BUNDLE", str(bundle))
    assert seed_builtin_mcp(state_dir=state) == []
    assert read_global()["chem-data-hub"]["url"] == "https://example.com/mcp"
    assert "user_plain" in read_global()["chem-data-hub"]["headers"]["Authorization"]


def test_seed_skips_server_without_token(
    state: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    bundle = tmp_path / "b.bundle"
    bundle.write_text(
        encode_secrets_file(
            {
                "tokens": {"chem-data-hub": "t1"},
                "urls": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CHEMCLAW_BUILTIN_MCP_BUNDLE", str(bundle))
    seeded = seed_builtin_mcp(state_dir=state)
    assert "chem-data-hub" in seeded
    assert "chem-biz-scope" not in seeded
    assert "chem-biz-scope" not in read_global()


def test_seed_chem_biz_scope_from_template_url(
    state: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    bundle = tmp_path / "b.bundle"
    bundle.write_text(
        encode_secrets_file(
            {
                "tokens": {"chem-biz-scope": "scope_tok"},
                "urls": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CHEMCLAW_BUILTIN_MCP_BUNDLE", str(bundle))
    seeded = seed_builtin_mcp(state_dir=state)
    assert seeded == ["chem-biz-scope"]
    assert read_global()["chem-biz-scope"]["url"] == "http://121.37.133.47:8900/mcp"


def test_seed_chem_biz_scope_url_override(
    state: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    bundle = tmp_path / "b.bundle"
    bundle.write_text(
        encode_secrets_file(
            {
                "tokens": {"chem-biz-scope": "scope_tok"},
                "urls": {"chem-biz-scope": "https://scope.example/mcp"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CHEMCLAW_BUILTIN_MCP_BUNDLE", str(bundle))
    seeded = seed_builtin_mcp(state_dir=state)
    assert seeded == ["chem-biz-scope"]
    assert read_global()["chem-biz-scope"]["url"] == "https://scope.example/mcp"


def test_api_guards_builtin(state: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "coworker.server.manager.seed_builtin_mcp", lambda *a, **k: []
    )
    put_global_server(
        "chem-data-hub",
        {
            "type": "http",
            "url": "https://datahub.chem-cloud.cn/mcp",
            "headers": {"Authorization": "Bearer ${CHEMCLAW_BUILTIN_MCP_CHEM_DATA_HUB}"},
            "enabled": True,
            "chemclaw_builtin": True,
            "chemclaw_builtin_version": 1,
        },
    )
    mgr = SessionManager(workspace=state / "ws")
    listed = {s["name"]: s for s in mgr.list_mcp()}
    assert listed["chem-data-hub"]["builtin"] is True
    assert listed["chem-data-hub"]["config"]["headers"]["Authorization"] == "***"

    assert mgr.delete_mcp("chem-data-hub")["ok"] is False
    assert mgr.add_mcp("chem-data-hub", {"url": "https://evil"})["ok"] is False
    assert mgr.patch_mcp("chem-data-hub", {"url": "https://evil"})["ok"] is False
    assert mgr.patch_mcp("chem-data-hub", {"enabled": False})["ok"] is True
    assert read_global()["chem-data-hub"]["enabled"] is False


def test_redact_masks_headers():
    out = _redact(
        {
            "url": "https://datahub.chem-cloud.cn/mcp",
            "headers": {"Authorization": "Bearer ${CHEMCLAW_BUILTIN_MCP_CHEM_DATA_HUB}"},
            "chemclaw_builtin": True,
        }
    )
    assert out["headers"]["Authorization"] == "***"
    assert out["url"] == "https://datahub.chem-cloud.cn/mcp"


def test_no_bundle_seeds_nothing(state: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CHEMCLAW_BUILTIN_MCP_BUNDLE", raising=False)
    monkeypatch.delenv("COWORKER_BUILTIN_MCP_BUNDLE", raising=False)
    monkeypatch.delenv("CHEMCLAW_BUILTIN_MCP_CHEM_DATA_HUB", raising=False)
    # Point candidates at empty dirs only
    monkeypatch.setattr(mcp_builtin, "candidate_bundle_paths", lambda: [])
    assert seed_builtin_mcp(state_dir=state) == []
    assert read_global() == {}
