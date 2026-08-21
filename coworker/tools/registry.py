"""Tool registry — wraps callables (incl. aisuite toolkit tools) into a registry the
runtime owns: JSON schemas for the model, plus execution. Permission checks live in the
PermissionEngine and are applied by the turn engine, not here.

Schema generation is reused from aisuite (`Tools`) so we don't reimplement
docstring/type-hint → JSON-schema extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from aisuite.utils.tools import Tools


@dataclass
class ToolSpec:
    name: str
    schema: dict[str, Any]  # OpenAI-format function tool schema
    func: Callable[..., Any]
    metadata: Any = None  # aisuite ToolMetadata or None


@dataclass(frozen=True)
class ToolDescriptor:
    """Read-only routing metadata for one registered Tool.

    The planner needs capability/category facts for dynamic MCP tools, but it must not
    learn registry execution details or receive mutable ToolSpec objects.
    """

    name: str
    category: str = ""
    capabilities: tuple[str, ...] = ()
    provider_id: str = ""
    network_scope: str = ""
    risk: str = ""


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        func: Callable[..., Any],
        *,
        metadata: Any = None,
        schema: Optional[dict[str, Any]] = None,
    ) -> ToolSpec:
        name = getattr(func, "__name__", None)
        if not name:
            raise ValueError("Tool function must have a __name__.")
        meta = metadata or getattr(func, "__aisuite_tool_metadata__", None)
        # Allow an explicit schema override (param or a `__coworker_schema__` attribute)
        # for tools whose signature can't be auto-converted to a valid JSON schema.
        resolved_schema = (
            schema or getattr(func, "__coworker_schema__", None) or _schema_for(func)
        )
        spec = ToolSpec(name=name, schema=resolved_schema, func=func, metadata=meta)
        self._tools[name] = spec
        return spec

    def register_all(self, funcs: list[Callable[..., Any]]) -> None:
        for func in funcs:
            self.register(func)

    def names(self) -> list[str]:
        return list(self._tools)

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def schemas(self) -> list[dict[str, Any]]:
        return [spec.schema for spec in self._tools.values()]

    def descriptors(self) -> list[ToolDescriptor]:
        out: list[ToolDescriptor] = []
        for spec in self._tools.values():
            metadata = spec.metadata
            raw_capabilities = getattr(metadata, "capabilities", ()) or ()
            out.append(
                ToolDescriptor(
                    name=spec.name,
                    category=str(getattr(metadata, "category", "") or ""),
                    capabilities=tuple(str(item) for item in raw_capabilities),
                    provider_id=str(
                        getattr(metadata, "provider_id", "")
                        or getattr(metadata, "server_id", "")
                        or ""
                    ),
                    network_scope=str(
                        getattr(metadata, "network_scope", "") or ""
                    ),
                    risk=str(getattr(metadata, "risk_level", "") or ""),
                )
            )
        return out

    def retain(self, names: set[str] | frozenset[str] | tuple[str, ...]) -> None:
        """Restrict this registry to a platform-owned allowlist.

        Used only while constructing a child Agent profile. PermissionEngine remains the
        authority for every retained tool; this method prevents undeclared tools from being
        projected or executed at all.
        """
        allowed = set(names)
        self._tools = {name: spec for name, spec in self._tools.items() if name in allowed}

    def execute(self, name: str, arguments: Optional[dict[str, Any]] = None) -> Any:
        spec = self._tools.get(name)
        if spec is None:
            raise KeyError(f"Tool not registered: {name}")
        return spec.func(**(arguments or {}))


def _schema_for(func: Callable[..., Any]) -> dict[str, Any]:
    """Generate one OpenAI-format tool schema via aisuite's schema generator."""
    return Tools([func]).tools(format="openai")[0]
