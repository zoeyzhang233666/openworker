"""Endpoint-scoped model facts. Unknown values are estimates, never inferred from names."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .matrix import model_context_windows


def endpoint_identity(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    host = parsed.hostname or ""
    if parsed.port:
        host += f":{parsed.port}"
    return urlunsplit((parsed.scheme.lower(), host.lower(), parsed.path.rstrip("/"), "", ""))


@dataclass(frozen=True)
class ModelProfile:
    key: str
    provider: str
    endpoint: str
    model: str
    context_window: int = 128_000
    max_output_tokens: int = 8_192
    reasoning_effort: str = ""  # empty: do not send a vendor-specific knob
    structured_tools_streaming: bool | None = None
    source: str = "estimated"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_overrides(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("模型能力配置必须是对象")
    allowed = {"context_window", "max_output_tokens", "reasoning_effort", "structured_tools_streaming"}
    if set(raw) - allowed:
        raise ValueError("模型能力配置包含未知字段")
    result = {}
    for key, value in raw.items():
        if value is None:
            continue
        if key in {"context_window", "max_output_tokens"}:
            if isinstance(value, bool) or not isinstance(value, int) or not 256 <= value <= 10_000_000:
                raise ValueError(f"{key} 必须是 256–10000000 的整数")
        elif key == "reasoning_effort":
            if value not in {"", "none", "minimal", "low", "medium", "high", "xhigh"}:
                raise ValueError("不支持的推理参数")
        elif not isinstance(value, bool):
            raise ValueError("流式工具能力必须是布尔值")
        result[key] = value
    return result


def resolve_model_profile(model: str, *, provider: str = "", endpoint: str = "",
                          overrides: dict | None = None) -> ModelProfile:
    endpoint = endpoint_identity(endpoint)
    identity = json.dumps([provider, endpoint, model], ensure_ascii=False)
    key = hashlib.sha256(identity.encode()).hexdigest()
    known = model_context_windows().get(model)
    values = validate_overrides((overrides or {}).get(key, {}))
    return ModelProfile(
        key=key, provider=provider, endpoint=endpoint, model=model,
        context_window=values.get("context_window", known or 128_000),
        max_output_tokens=values.get("max_output_tokens", 8_192),
        reasoning_effort=values.get("reasoning_effort", ""),
        structured_tools_streaming=values.get("structured_tools_streaming"),
        source="override" if "context_window" in values else ("matrix" if known else "estimated"),
    )
