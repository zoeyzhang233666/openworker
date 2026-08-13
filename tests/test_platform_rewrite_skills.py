"""Contract tests for platform-rewrite bundled skills (M1)."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from coworker.skills.base import SkillLoader, _parse_skill
from coworker.skills.bootstrap import BUNDLED_DIR, seed_bundled_skills
from coworker.skills.store import SkillStore


ROOT = Path(__file__).resolve().parents[1]
BUNDLED = ROOT / "coworker" / "skills" / "bundled"

SKILL_IDS = (
    "chem-rewrite-brief",
    "chem-platform-rewrite",
    "chem-content-policy",
    "chem-content-quality-check",
    "chem-hook-cta-pack",
)

FIXTURES = ROOT / "docs" / "chemclaw" / "platform-rewrite" / "fixtures"


def _load_script(skill: str, script_name: str):
    path = BUNDLED / skill / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(f"{skill}_{script_name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_platform_rewrite_skills_exist_with_assets() -> None:
    for name in SKILL_IDS:
        skill_dir = BUNDLED / name
        md = skill_dir / "SKILL.md"
        assert md.is_file(), name
        skill = _parse_skill(md)
        assert skill.name == name
        assert skill.description.strip()
        assert (skill_dir / "references").is_dir()
        assert list((skill_dir / "schemas").glob("*.json")) or name == "chem-content-policy"


def test_platform_rewrite_skills_seed_byte_identical(tmp_path: Path) -> None:
    store = SkillStore(
        global_dir=tmp_path / "skills",
        settings_path=tmp_path / "skills-settings.json",
    )
    installed = set(seed_bundled_skills(store))
    assert set(SKILL_IDS) <= installed
    loader = SkillLoader([store.global_dir])
    for name in SKILL_IDS:
        assert loader.get(name) is not None
        source = BUNDLED_DIR / name
        target = store.global_dir / name
        source_files = {
            p.relative_to(source): p.read_bytes()
            for p in source.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        target_files = {
            p.relative_to(target): p.read_bytes()
            for p in target.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        assert target_files == source_files


def test_rewrite_brief_schema_accepts_minimal_fixture() -> None:
    schema = json.loads(
        (BUNDLED / "chem-rewrite-brief" / "schemas" / "rewrite-brief.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    brief = json.loads((FIXTURES / "brief-minimal.json").read_text(encoding="utf-8"))
    validator.validate(brief)


def test_scan_content_flags_blocked_terms() -> None:
    scan = _load_script("chem-content-policy", "scan_content.py")
    lexicon = (
        BUNDLED / "chem-content-policy" / "references" / "lexicon" / "managed" / "base.csv"
    )
    text = "本产品为国家级第一品牌，包过检测，绝对安全，100%无风险。"
    result = scan.scan_content(text, lexicon_path=lexicon)
    terms = {hit["term"] for hit in result["hits"]}
    for expected in ("国家级", "第一", "包过", "绝对安全", "100%无风险"):
        assert expected in terms
    assert result["blocked"] is True
    assert any(h["severity"] == "block" for h in result["hits"])
    assert result["rule_set"]["id"] == "chem-content-policy"
    assert result["rule_set"]["version"] == "1.0.0"


def test_scan_content_merges_user_override_and_suppress(tmp_path: Path) -> None:
    scan = _load_script("chem-content-policy", "scan_content.py")
    managed = (
        BUNDLED / "chem-content-policy" / "references" / "lexicon" / "managed" / "base.csv"
    )
    user = tmp_path / "user.csv"
    user.write_text(
        "rule_id,term,platform,locale,category,severity,action,replacement_strategy,notes\n"
        "safety-absolute,,,zh-CN,safety,block,suppress,,关掉绝对安全\n"
        "custom-ban,私自加禁词,all,zh-CN,custom,block,rewrite,删除,用户新增\n",
        encoding="utf-8",
    )
    text = "绝对安全，另有私自加禁词。"
    result = scan.scan_content(text, lexicon_path=managed, lexicon_user=user)
    terms = {hit["term"] for hit in result["hits"]}
    assert "绝对安全" not in terms
    assert "私自加禁词" in terms
    assert result["blocked"] is True
    assert result["rule_set"]["version"] == "1.0.0"


def test_scan_content_default_paths_include_rule_set() -> None:
    scan = _load_script("chem-content-policy", "scan_content.py")
    result = scan.scan_content("绝对安全")
    assert result["rule_set"]["id"] == "chem-content-policy"
    assert result["rule_set"]["version"]
    assert result["blocked"] is True


def test_check_content_blocks_on_policy_and_fact_drift() -> None:
    check = _load_script("chem-content-quality-check", "check_content.py")
    brief = json.loads((FIXTURES / "brief-minimal.json").read_text(encoding="utf-8"))
    source = (FIXTURES / "source-safe.txt").read_text(encoding="utf-8")
    bad_output = (
        "我们的对羟基苯甲酸甲酯纯度 99.9%，CAS 99-76-3，20kg/袋，"
        "国家级第一，绝对安全，包过认证。"
    )
    result = check.check_content(
        {
            "source_text": source,
            "output_text": bad_output,
            "brief": brief,
            "target_platform": "xiaohongshu",
            "required_sections": ["标题", "正文", "标签", "改写说明"],
            "policy_hits": [
                {
                    "term": "绝对安全",
                    "severity": "block",
                    "action": "block",
                    "rule_id": "safety-absolute",
                }
            ],
        }
    )
    assert result["verdict"] in ("revise", "blocked")
    assert result["recommended_action"] != "ready_for_publish_review"
    assert result["fact_integrity"]["passed"] is False
    assert result["policy_scan"]["passed"] is False


def test_check_content_passes_clean_rewrite() -> None:
    check = _load_script("chem-content-quality-check", "check_content.py")
    brief = json.loads((FIXTURES / "brief-minimal.json").read_text(encoding="utf-8"))
    source = (FIXTURES / "source-safe.txt").read_text(encoding="utf-8")
    good = (FIXTURES / "output-xhs-clean.txt").read_text(encoding="utf-8")
    result = check.check_content(
        {
            "source_text": source,
            "output_text": good,
            "brief": brief,
            "target_platform": "xiaohongshu",
            "required_sections": ["标题", "封面字", "正文", "标签", "改写说明"],
            "policy_hits": [],
        }
    )
    assert result["verdict"] == "pass"
    assert result["recommended_action"] == "ready_for_publish_review"
    assert result["fact_integrity"]["passed"] is True
    assert result["policy_scan"]["passed"] is True


def test_lexicon_csv_has_required_columns() -> None:
    path = (
        BUNDLED / "chem-content-policy" / "references" / "lexicon" / "managed" / "base.csv"
    )
    version = (
        BUNDLED
        / "chem-content-policy"
        / "references"
        / "lexicon"
        / "managed"
        / "rule_version.txt"
    )
    user = BUNDLED / "chem-content-policy" / "references" / "lexicon" / "user.csv"
    assert version.is_file()
    assert version.read_text(encoding="utf-8").strip() == "1.0.0"
    assert user.is_file()
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows
    required = {
        "rule_id",
        "term",
        "platform",
        "locale",
        "category",
        "severity",
        "action",
        "replacement_strategy",
        "notes",
    }
    assert required <= set(rows[0].keys())
    assert any(r["term"] == "绝对安全" and r["severity"] == "block" for r in rows)


def test_content_scan_schema_requires_rule_set() -> None:
    schema = json.loads(
        (
            BUNDLED
            / "chem-content-policy"
            / "schemas"
            / "content-scan-output.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    scan = _load_script("chem-content-policy", "scan_content.py")
    result = scan.scan_content("绝对安全")
    validator.validate(result)


def test_platform_references_exist() -> None:
    base = BUNDLED / "chem-platform-rewrite" / "references" / "platforms"
    for name in ("xiaohongshu.md", "douyin.md", "x.md"):
        path = base / name
        assert path.is_file()
        assert len(path.read_text(encoding="utf-8").strip()) > 40


def test_hook_cta_pack_assets_and_schema() -> None:
    skill_dir = BUNDLED / "chem-hook-cta-pack"
    assert (skill_dir / "SKILL.md").is_file()
    skill = _parse_skill(skill_dir / "SKILL.md")
    assert skill.name == "chem-hook-cta-pack"
    assert "钩子" in skill.description or "CTA" in skill.description or "标题" in skill.description
    for name in (
        "hooks-xiaohongshu.md",
        "hooks-douyin.md",
        "hooks-x.md",
        "cta-patterns.md",
        "anti-patterns.md",
    ):
        path = skill_dir / "references" / name
        assert path.is_file(), name
        text = path.read_text(encoding="utf-8")
        assert len(text.strip()) > 40
        if name == "anti-patterns.md":
            assert "不得新增" in text or "禁止" in text

    schema = json.loads(
        (skill_dir / "schemas" / "hook-cta-pack.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    sample = {
        "schema_version": "chemclaw.hook-cta-pack.v1",
        "target_platform": "xiaohongshu",
        "title_candidates": ["工业级甲酯防腐评估笔记"],
        "cover_text_candidates": ["99.5% · 25kg/袋"],
        "hook_candidates": ["配方评估前先对齐规格"],
        "cta_candidates": ["评论区留言索取规格资料"],
        "facts_unchanged": True,
        "notes": "未新增 CAS/认证/案例",
    }
    validator.validate(sample)


def test_regression_fixtures_present() -> None:
    for name in (
        "brief-minimal.json",
        "source-safe.txt",
        "source-risky.txt",
        "output-xhs-clean.txt",
        "output-douyin-clean.txt",
        "output-x-clean.txt",
    ):
        assert (FIXTURES / name).is_file(), name
