"""D-190 retire builtin MCP (+ obfuscation roundtrip still covered)."""

from __future__ import annotations

from pathlib import Path

import pytest

from coworker.mcp.builtin import (
    obfuscate_payload,
    deobfuscate_payload,
    retire_builtin_mcp,
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


def test_retire_builtin_mcp_removes_servers_and_dotenv_keys(
    state: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    put_global_server(
        "chem-data-hub",
        {
            "type": "http",
            "url": "https://datahub.chem-cloud.cn/mcp",
            "headers": {"Authorization": "Bearer ${CHEMCLAW_BUILTIN_MCP_CHEM_DATA_HUB}"},
            "enabled": True,
            "chemclaw_builtin": True,
        },
    )
    put_global_server(
        "my-custom",
        {
            "type": "http",
            "url": "https://example.com/mcp",
            "headers": {"Authorization": "Bearer x"},
            "enabled": True,
        },
    )
    (state / ".env").write_text(
        "CHEMCLAW_BUILTIN_MCP_CHEM_DATA_HUB=tok\n"
        "CHEMCLAW_BUILTIN_MCP_CHEM_BIZ_SCOPE=tok2\n"
        "OTHER_KEY=keep\n",
        encoding="utf-8",
    )
    removed = retire_builtin_mcp(state_dir=state)
    assert removed == ["chem-data-hub"]
    assert "chem-data-hub" not in read_global()
    assert "my-custom" in read_global()
    dotenv = (state / ".env").read_text(encoding="utf-8")
    assert "CHEMCLAW_BUILTIN_MCP_" not in dotenv
    assert "OTHER_KEY=keep" in dotenv


def test_session_manager_boot_calls_retire_not_seed(
    state: Path, monkeypatch: pytest.MonkeyPatch
):
    put_global_server(
        "chem-biz-scope",
        {
            "type": "http",
            "url": "http://121.37.133.47:8900/mcp",
            "chemclaw_builtin": True,
            "enabled": True,
        },
    )
    calls: list[str] = []

    def _retire(*a, **k):
        calls.append("retire")
        return retire_builtin_mcp(state_dir=state)

    monkeypatch.setattr("coworker.server.manager.retire_builtin_mcp", _retire)
    SessionManager(workspace=state / "ws")
    assert calls == ["retire"]
    assert "chem-biz-scope" not in read_global()


def test_mcp_crud_allows_delete_after_retire(state: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "coworker.server.manager.retire_builtin_mcp", lambda *a, **k: []
    )
    put_global_server(
        "chem-data-hub",
        {
            "type": "http",
            "url": "https://datahub.chem-cloud.cn/mcp",
            "headers": {"Authorization": "Bearer tok"},
            "enabled": True,
        },
    )
    mgr = SessionManager(workspace=state / "ws")
    assert mgr.delete_mcp("chem-data-hub")["ok"] is True
    assert "chem-data-hub" not in read_global()


def test_add_mcp_strips_builtin_flags(state: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "coworker.server.manager.retire_builtin_mcp", lambda *a, **k: []
    )
    mgr = SessionManager(workspace=state / "ws")
    mgr.add_mcp(
        "chem-data-hub",
        {
            "type": "http",
            "url": "https://datahub.chem-cloud.cn/mcp",
            "headers": {"Authorization": "Bearer tok"},
            "chemclaw_builtin": True,
            "chemclaw_builtin_version": 99,
        },
    )
    raw = read_global()["chem-data-hub"]
    assert "chemclaw_builtin" not in raw
    assert raw["headers"]["Authorization"] == "Bearer tok"


def test_redact_masks_headers():
    out = _redact(
        {
            "url": "https://datahub.chem-cloud.cn/mcp",
            "headers": {"Authorization": "Bearer secret"},
        }
    )
    assert out["headers"]["Authorization"] == "***"
