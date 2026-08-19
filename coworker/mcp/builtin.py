"""ChemClaw managed builtin MCP servers (chem-data-hub / chem-biz-scope).

Templates live in-repo without secrets. Build injects an obfuscated bundle;
``seed_builtin_mcp`` writes ``mcp.json`` with ``${VAR}`` refs and seeds tokens
into the state-dir ``.env`` (the existing SecretStore ``${VAR}`` resolution path).

Obfuscation is intentional mild deterrence for casual APPDATA inspection — not
cryptographic protection against reverse engineering.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

from ..runtime_paths import packaged_coworker_dir
from ..secrets import write_private_text
from .config import put_global_server, read_global

logger = logging.getLogger(__name__)

BUILTIN_FLAG = "chemclaw_builtin"
BUILTIN_VERSION_KEY = "chemclaw_builtin_version"
BUNDLE_PREFIX = "CCBM1."
_XOR_KEY = b"ChemClaw-builtin-mcp-v1"

# Server name → env var used in template headers.
TOKEN_ENV_BY_SERVER: dict[str, str] = {
    "chem-data-hub": "CHEMCLAW_BUILTIN_MCP_CHEM_DATA_HUB",
    "chem-biz-scope": "CHEMCLAW_BUILTIN_MCP_CHEM_BIZ_SCOPE",
}

_ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def builtin_servers_template_path() -> Path:
    return Path(__file__).resolve().parent / "builtin_servers.json"


def load_builtin_templates() -> dict[str, dict[str, Any]]:
    path = builtin_servers_template_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    servers = raw.get("mcpServers") or {}
    return {
        str(name): dict(cfg)
        for name, cfg in servers.items()
        if isinstance(cfg, dict)
    }


def is_builtin_config(raw: dict[str, Any] | None) -> bool:
    return bool(raw) and bool(raw.get(BUILTIN_FLAG))


def token_env_for(server_name: str) -> str:
    return TOKEN_ENV_BY_SERVER.get(
        server_name, f"CHEMCLAW_BUILTIN_MCP_{server_name.upper().replace('-', '_')}"
    )


def obfuscate_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    xored = bytes(b ^ _XOR_KEY[i % len(_XOR_KEY)] for i, b in enumerate(raw))
    return BUNDLE_PREFIX + base64.urlsafe_b64encode(xored).decode("ascii")


def deobfuscate_payload(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text.startswith(BUNDLE_PREFIX):
        raise ValueError("unknown builtin MCP bundle format")
    blob = base64.urlsafe_b64decode(text[len(BUNDLE_PREFIX) :].encode("ascii"))
    raw = bytes(b ^ _XOR_KEY[i % len(_XOR_KEY)] for i, b in enumerate(blob))
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("builtin MCP bundle must be a JSON object")
    return data


def encode_secrets_file(secrets: dict[str, Any]) -> str:
    """Normalize packaging secrets JSON into an obfuscated bundle string."""
    tokens = dict(secrets.get("tokens") or {})
    urls = dict(secrets.get("urls") or {})
    # Allow flat {ENV: value} for convenience.
    if not tokens and any(
        str(k).startswith("CHEMCLAW_BUILTIN_MCP_") for k in secrets.keys()
    ):
        for k, v in secrets.items():
            if str(k).startswith("CHEMCLAW_BUILTIN_MCP_") and isinstance(v, str):
                # Map env → short server key when known.
                for server, env in TOKEN_ENV_BY_SERVER.items():
                    if env == k:
                        tokens[server] = v
                        break
                else:
                    tokens[str(k)] = v
    payload = {"tokens": tokens, "urls": urls}
    return obfuscate_payload(payload)


def candidate_bundle_paths() -> list[Path]:
    paths: list[Path] = []
    env = os.environ.get("COWORKER_BUILTIN_MCP_BUNDLE") or os.environ.get(
        "CHEMCLAW_BUILTIN_MCP_BUNDLE"
    )
    if env:
        paths.append(Path(env).expanduser())
    pkg = packaged_coworker_dir()
    if pkg is not None:
        paths.append(pkg / "mcp" / "builtin_mcp.bundle")
    # Source / editable install next to this module.
    paths.append(Path(__file__).resolve().parent / "builtin_mcp.bundle")
    # Packaging output used by Windows build before datas copy.
    root = Path(__file__).resolve().parents[2]
    paths.append(root / "packaging" / "builtin_mcp.bundle")
    return paths


def load_bundle_payload() -> Optional[dict[str, Any]]:
    """Load tokens/urls from bundle file, or synthesize from process env."""
    for path in candidate_bundle_paths():
        if not path.is_file():
            continue
        try:
            return deobfuscate_payload(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("builtin MCP bundle unreadable at %s: %s", path, exc)
    # Dev fallback: env vars only (no obfuscated file).
    tokens: dict[str, str] = {}
    urls: dict[str, str] = {}
    for server, env_name in TOKEN_ENV_BY_SERVER.items():
        val = os.environ.get(env_name)
        if val:
            tokens[server] = val
        url = os.environ.get(f"{env_name}_URL")
        if url:
            urls[server] = url
    if not tokens:
        return None
    return {"tokens": tokens, "urls": urls}


def _dotenv_path(state: Path) -> Path:
    return state / ".env"


def _read_dotenv_map(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        m = _ENV_LINE.match(stripped)
        if not m:
            continue
        out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def _write_dotenv_map(path: Path, values: dict[str, str]) -> None:
    """Merge ``values`` into ``.env`` without overwriting existing keys."""
    existing = _read_dotenv_map(path)
    changed = False
    for key, val in values.items():
        if not val:
            continue
        if key in existing and existing[key]:
            continue
        existing[key] = val
        changed = True
    if not changed and path.is_file():
        return
    lines = [f"{k}={v}" for k, v in sorted(existing.items())]
    write_private_text(path, "\n".join(lines) + ("\n" if lines else ""))


def _token_for_server(payload: dict[str, Any], server: str) -> str:
    tokens = payload.get("tokens") or {}
    if not isinstance(tokens, dict):
        return ""
    direct = tokens.get(server)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    env_name = token_env_for(server)
    alt = tokens.get(env_name)
    if isinstance(alt, str) and alt.strip():
        return alt.strip()
    return ""


def _url_override(payload: dict[str, Any], server: str) -> str:
    urls = payload.get("urls") or {}
    if not isinstance(urls, dict):
        return ""
    val = urls.get(server)
    return str(val).strip() if val else ""


def _non_secret_fields(template: dict[str, Any], url: str) -> dict[str, Any]:
    cfg = dict(template)
    cfg["url"] = url
    cfg[BUILTIN_FLAG] = True
    cfg.setdefault(BUILTIN_VERSION_KEY, 1)
    cfg.setdefault("enabled", True)
    cfg.setdefault("requires_approval", True)
    # Ensure headers keep ${VAR} form from template.
    return cfg


def seed_builtin_mcp(*, state_dir: Path | None = None) -> list[str]:
    """Seed managed builtin MCP entries. Returns newly written server names.

    ``state_dir`` defaults to ChemClaw state (``secrets.state_dir()``).
    """
    from ..secrets import state_dir as default_state_dir

    state = Path(state_dir) if state_dir else default_state_dir()
    payload = load_bundle_payload()
    if not payload:
        return []

    templates = load_builtin_templates()
    if not templates:
        return []

    existing = read_global()
    seeded: list[str] = []
    env_to_set: dict[str, str] = {}

    for name, template in templates.items():
        token = _token_for_server(payload, name)
        url = _url_override(payload, name) or str(template.get("url") or "").strip()
        if not token or not url:
            continue

        env_name = token_env_for(name)
        # Strip accidental "Bearer " prefix so template "Bearer ${VAR}" stays valid.
        token_value = token
        if token_value.lower().startswith("bearer "):
            token_value = token_value[7:].strip()
        env_to_set[env_name] = token_value

        current = existing.get(name)
        if current is not None and not is_builtin_config(current):
            # User-owned config — never overwrite.
            continue

        desired = _non_secret_fields(template, url)
        # Keep template headers (with ${VAR}); rewrite Authorization to known env.
        headers = dict(desired.get("headers") or {})
        if "Authorization" in headers or headers:
            headers["Authorization"] = f"Bearer ${{{env_name}}}"
            desired["headers"] = headers

        if current is None:
            put_global_server(name, desired)
            seeded.append(name)
            existing[name] = desired
            continue

        # Already builtin: refresh non-secret fields when version increases or URL drifted.
        cur_ver = int(current.get(BUILTIN_VERSION_KEY) or 0)
        new_ver = int(desired.get(BUILTIN_VERSION_KEY) or 0)
        if cur_ver < new_ver or str(current.get("url") or "") != url:
            merged = {**current, **desired}
            # Preserve user enabled toggle.
            if "enabled" in current:
                merged["enabled"] = bool(current.get("enabled"))
            put_global_server(name, merged)
            seeded.append(name)
            existing[name] = merged

    if env_to_set:
        _write_dotenv_map(_dotenv_path(state), env_to_set)

    if seeded:
        logger.info("seeded builtin MCP servers: %s", ", ".join(seeded))
    return seeded
