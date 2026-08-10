"""uncertainty-and-units bundled skill (D-111 / K-Dense via 化工社合集)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from coworker.skills.base import _parse_skill
from coworker.skills.bootstrap import list_bundled_skill_names


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "coworker" / "skills" / "bundled" / "uncertainty-and-units"
SKILL_MD = SKILL_DIR / "SKILL.md"
QUOTE = (
    ROOT
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-inquiry-to-quote"
    / "SKILL.md"
)
ENGAGEMENT = ROOT / "coworker" / "personas" / "builtin" / "export-engagement-lobster.md"


def test_bundled_skill_parses_and_is_seedable():
    assert SKILL_MD.is_file()
    skill = _parse_skill(SKILL_MD)
    assert skill.name == "uncertainty-and-units"
    assert "uncertainty-and-units" in list_bundled_skill_names()


def test_skill_has_chemclaw_chinese_boundaries():
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "单位" in text or "不确定度" in text
    assert "Lead" in text or "拓客" in text or "评分" in text
    assert "resources_path" in text
    assert "Read Write Edit Bash" not in text
    assert (SKILL_DIR / "references" / "chemclaw-usage.md").is_file()
    assert (SKILL_DIR / "scripts" / "audit_units.py").is_file()


def test_audit_units_script_help_stdlib():
    script = SKILL_DIR / "scripts" / "audit_units.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(SKILL_DIR / "scripts"),
        check=False,
    )
    assert proc.returncode == 0
    out = (proc.stdout or "") + (proc.stderr or "")
    assert "usage" in out.lower() or "audit" in out.lower() or "单位" in out


def test_quote_and_engagement_optional_wire():
    quote = QUOTE.read_text(encoding="utf-8")
    eng = ENGAGEMENT.read_text(encoding="utf-8")
    assert "uncertainty-and-units" in quote
    assert "uncertainty-and-units" in eng
    # Must stay optional: not a forced default skill on the lobster.
    assert "- uncertainty-and-units" not in eng.split("skills:", 1)[-1].split("---", 1)[0]
