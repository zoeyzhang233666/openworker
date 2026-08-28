"""MCP connect-failure messages for GUI / logs (no secrets).

MCP HTTP transports (anyio TaskGroup / ExceptionGroup) often wrap the real
cause; D-189 surfaces failures, and this module unwraps the leaf for humans.
"""

from __future__ import annotations

import re
from typing import Optional

_OPAQUE_SHELL = re.compile(
    r"unhandled errors in a (?:TaskGroup|ExceptionGroup)",
    re.IGNORECASE,
)


def _leaf_exception(exc: BaseException, *, _seen: Optional[set[int]] = None) -> BaseException:
    """Walk ExceptionGroup / cause / context to the most informative leaf."""
    seen = _seen if _seen is not None else set()
    ident = id(exc)
    if ident in seen:
        return exc
    seen.add(ident)

    subs = getattr(exc, "exceptions", None)
    if subs:
        # Prefer the first non-opaque child; otherwise recurse into the first.
        for sub in subs:
            if isinstance(sub, BaseException):
                return _leaf_exception(sub, _seen=seen)

    for attr in ("__cause__", "__context__"):
        linked = getattr(exc, attr, None)
        if isinstance(linked, BaseException) and linked is not exc:
            return _leaf_exception(linked, _seen=seen)
    return exc


def _raw_text(exc: BaseException) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    first = text.splitlines()[0].strip()
    return first or exc.__class__.__name__


def _chinese_prefix(text: str, class_name: str) -> str:
    lowered = f"{text} {class_name}".lower()
    if any(
        m in lowered
        for m in ("401", "403", "unauthorized", "forbidden", "invalid token", "invalid api")
    ):
        return "鉴权失败"
    if (
        "connectionerror" in lowered
        or "connecterror" in lowered
        or any(
            m in lowered
            for m in (
                "connection refused",
                "connect error",
                "namenotresolved",
                "getaddrinfo",
                "nodename nor servname",
                "failed to establish",
                "network is unreachable",
                "timed out",
                "timeout",
                "refused",
            )
        )
    ):
        return "无法连接服务器"
    if any(m in lowered for m in ("ssl", "certificate", "certifi", "tls")):
        return "证书/TLS 失败"
    if "unresolved" in lowered:
        return "配置不完整"
    return ""


def format_mcp_connect_error(exc: BaseException) -> str:
    """Short GUI/log message: optional zh prefix + leaf technical text (max 300)."""
    leaf = _leaf_exception(exc)
    tech = _raw_text(leaf)
    # If we somehow still only have the opaque shell, try siblings on the root group.
    if _OPAQUE_SHELL.search(tech):
        subs = getattr(exc, "exceptions", None) or ()
        for sub in subs:
            if isinstance(sub, BaseException):
                candidate = _raw_text(_leaf_exception(sub))
                if candidate and not _OPAQUE_SHELL.search(candidate):
                    tech = candidate
                    leaf = sub
                    break
    prefix = _chinese_prefix(tech, leaf.__class__.__name__)
    if prefix and not tech.startswith(prefix):
        msg = f"{prefix}：{tech}"
    else:
        msg = tech
    return msg[:300]
