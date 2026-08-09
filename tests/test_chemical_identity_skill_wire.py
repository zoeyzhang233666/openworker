"""Skill wiring for PubChem chemical identity Tool (D-095)."""

from __future__ import annotations

from pathlib import Path

from coworker.skills.base import _parse_skill


ROOT = Path(__file__).resolve().parents[1]
SKILL = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-product-intelligence"
    / "SKILL.md"
)


def test_product_intelligence_documents_lookup_tool():
    skill = _parse_skill(SKILL)
    text = skill.instructions
    assert "lookup_chemical_identity" in text
    assert "PubChem" in text
    assert "cas.py" in text
    assert "unresolved" in text
    assert "不在本 Skill 内直接访问" in text or "平台 Provider" in text


def test_cas_script_still_validates_without_network():
    import json
    import os
    import subprocess
    import sys

    script = SKILL.parent / "scripts" / "cas.py"
    # Avoid writing __pycache__ into bundled skill (seed/bytecode contract tests).
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    ok = subprocess.run(
        [sys.executable, "-B", str(script), "532-32-1"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    bad = subprocess.run(
        [sys.executable, "-B", str(script), "532-32-2"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert ok.returncode == 0
    assert json.loads(ok.stdout)["valid"] is True
    assert bad.returncode != 0
