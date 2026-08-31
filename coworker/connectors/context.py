"""Task-local Channel reply context used by outbound tools.

The value is deliberately an opaque target string.  It is set only while a Channel
turn is executing, so a GUI or scheduled turn can never inherit a previous recipient.
"""

from __future__ import annotations

from contextvars import ContextVar, Token


_current_channel_target: ContextVar[str] = ContextVar(
    "chemclaw_current_channel_target", default=""
)


def current_channel_target() -> str:
    return _current_channel_target.get()


def set_current_channel_target(target: str) -> Token:
    return _current_channel_target.set((target or "").strip())


def reset_current_channel_target(token: Token) -> None:
    _current_channel_target.reset(token)
