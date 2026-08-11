"""Resolve on-disk ChemClaw package assets for source and frozen (PyInstaller) runs."""

from __future__ import annotations

import sys
from pathlib import Path


def _meipass() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    raw = getattr(sys, "_MEIPASS", None)
    return Path(raw) if raw else None


def packaged_coworker_dir() -> Path | None:
    """Return ``<MEIPASS>/coworker`` when the sidecar was frozen with datas trees."""
    root = _meipass()
    if root is None:
        return None
    cand = root / "coworker"
    return cand if cand.is_dir() else None


def bundled_skills_dir() -> Path:
    """``coworker/skills/bundled`` — source tree or PyInstaller datas."""
    pkg = packaged_coworker_dir()
    if pkg is not None:
        return pkg / "skills" / "bundled"
    return Path(__file__).resolve().parent / "skills" / "bundled"


def builtin_personas_dir() -> Path:
    """``coworker/personas/builtin`` — source tree or PyInstaller datas."""
    pkg = packaged_coworker_dir()
    if pkg is not None:
        return pkg / "personas" / "builtin"
    return Path(__file__).resolve().parent / "personas" / "builtin"
