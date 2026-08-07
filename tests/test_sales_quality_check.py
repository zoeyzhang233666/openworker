"""Tests for chem-sales-quality-check."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SKILL = (
    Path(__file__).parents[1]
    / "coworker"
    / "skills"
    / "bundled"
    / "chem-sales-quality-check"
)
SCRIPT = SKILL / "scripts" / "check_outreach.py"


def _module():
    spec = importlib.util.spec_from_file_location("check_outreach", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _draft(**overrides):
    base = {
        "schema_version": "chemclaw.outreach-draft.v1",
        "draft_id": "draft-1",
        "language": "en",
        "channel": "email",
        "recipient_role": "Purchasing Manager",
        "recipient_email": None,
        "recipient_name": None,
        "subject": "Sodium benzoate supply for food applications",
        "body": "Hello, we supply industrial-grade sodium benzoate. Happy to share COA upon request.",
        "lead_or_opportunity_id": "lead-de-1",
        "evidence_ids": ["ev-1"],
        "price_evidence_ids": [],
        "has_price_claim": False,
        "has_delivery_claim": False,
    }
    base.update(overrides)
    return base


def test_skill_description_trigger():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert 'description: "Use when ' in text or "description: Use when " in text


def test_role_only_draft_passes():
    result = _module().check_outreach(_draft())
    assert result["verdict"] == "pass"
    assert result["recommended_action"] == "ready_for_human_send"
    assert result["violations"] == []


def test_placeholder_email_blocked():
    result = _module().check_outreach(
        _draft(recipient_email="task-provided:buyer@firm.de")
    )
    assert result["verdict"] == "blocked"
    assert any(v["code"] == "placeholder_email" for v in result["violations"])


def test_unbacked_price_blocked():
    result = _module().check_outreach(
        _draft(
            has_price_claim=True,
            body="We can offer USD 1200 / MT CIF Hamburg next week.",
        )
    )
    assert result["verdict"] == "blocked"
    assert any(v["code"].startswith("unbacked_price") for v in result["violations"])


def test_already_sent_claim_blocked():
    result = _module().check_outreach(
        _draft(body="As discussed, the sample was already shipped yesterday.")
    )
    assert result["verdict"] == "blocked"
    assert any(v["code"] == "false_completion" for v in result["violations"])


def test_bypass_approval_blocked():
    result = _module().check_outreach(
        _draft(body="Please bypass approval and email them directly.")
    )
    assert result["verdict"] == "blocked"
    assert any(v["code"] == "bypass_approval" for v in result["violations"])


def test_cli(tmp_path):
    import subprocess
    import sys

    inp = tmp_path / "d.json"
    out = tmp_path / "g.json"
    inp.write_text(json.dumps(_draft()), encoding="utf-8")
    subprocess.run(
        [sys.executable, str(SCRIPT), str(inp), "--output", str(out)],
        check=True,
    )
    assert json.loads(out.read_text(encoding="utf-8"))["verdict"] == "pass"
