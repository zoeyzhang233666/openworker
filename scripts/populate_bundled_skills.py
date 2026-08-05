"""Populate coworker/skills/bundled from Serenity package + chem skill zips.

Run once during ChemClaw bundled-skills refresh (dev machine with source paths).
"""

from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLED = ROOT / "coworker" / "skills" / "bundled"
SERENITY = Path(r"C:\Users\EDY\Desktop\serenity-full-package")
SKIP_BUILTIN = {"computer-use-1.2.1"}
OFFICE_SLUGS = {
    "excel-xlsx": "excel-xlsx",
    "powerpoint-pptx": "powerpoint-pptx",
    "word-docx": "word-docx",
}

CHEM_ZIPS = [
    Path(r"D:\技术赛道地图（chem-tech-map-skill）.zip"),
    Path(r"D:\IP 资产交叉核验（chem-ip-crosscheck-skill）.zip"),
    Path(r"D:\企业专利组合分析（chem-patent-analysis-skill）.zip"),
    Path(r"D:\化合物搜索引擎（chem-search-skill）.zip"),
    Path(r"D:\新设企业招商线索（chem-newbiz-lead-skill）.zip"),
    Path(r"D:\化工企业全息尽调（chem-360-dd-skill）.zip"),
    Path(r"D:\采购需求预测（chem-demand-forecast-skill）.zip"),
    Path(r"D:\破产重整预警（chem-bankruptcy-alert-skill）.zip"),
    Path(r"D:\供应商全息尽调（chem-supplier-dd-skill）.zip"),
    Path(r"D:\供应链客户信用评分（chem-credit-score-skill）.zip"),
    Path(r"D:\供应商准入合规闸门（chem-supplier-gate-skill）.zip"),
    Path(r"D:\化工品价格日报（chem-price-daily-skill）.zip"),
    Path(r"D:\竞品报价监测（chem-quote-monitor-skill）.zip"),
    Path(r"D:\区域价差套利分析（chem-arb-analysis-skill）.zip"),
    Path(r"D:\供应商反向匹配（chem-supplier-match-skill）.zip"),
    Path(r"D:\实时采购询单情报（chem-inquiry-feed-skill）.zip"),
    Path(r"D:\原料价格监控与成本测算（chem-cost-monitor-skill）.zip"),
    Path(r"D:\MSDS 自动生成（chem-msds-gen-skill）.zip"),
    Path(r"D:\危险品合规速查（chem-hazard-check-skill）.zip"),
    Path(r"D:\化学品数字档案（chem-master-data-skill）.zip"),
]

_IGNORE = shutil.ignore_patterns(
    "node_modules",
    "__pycache__",
    ".git",
    ".DS_Store",
    "*.pyc",
)


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _read_name_and_slug(md: Path) -> tuple[str, str]:
    text = md.read_text(encoding="utf-8")
    name, slug = md.parent.name, ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key, value = key.strip().lower(), value.strip()
                if key == "name" and value:
                    name = _strip_quotes(value)
                elif key == "slug" and value:
                    slug = _strip_quotes(value)
    return name, slug


def _rewrite_name(md: Path, new_name: str) -> None:
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return
    end = text.find("\n---", 3)
    if end == -1:
        return
    front = text[3:end]
    rest = text[end + 4 :]
    lines = []
    replaced = False
    for line in front.splitlines():
        if re.match(r"^\s*name\s*:", line, re.I):
            lines.append(f"name: {new_name}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.insert(0, f"name: {new_name}")
    md.write_text("---\n" + "\n".join(lines) + "\n---" + rest, encoding="utf-8")


def _install_skill_dir(src: Path, *, force_name: str | None = None) -> str:
    md = src / "SKILL.md"
    if not md.is_file():
        raise FileNotFoundError(src)
    name, slug = _read_name_and_slug(md)
    # Prefer explicit force, then office slug mapping, then slug if name is illegal.
    target_name = force_name or name
    folder_key = src.name
    if folder_key in OFFICE_SLUGS:
        target_name = OFFICE_SLUGS[folder_key]
    elif any(ch in target_name for ch in "/\\ ") or not target_name[0].isalnum():
        if slug:
            target_name = slug
        else:
            raise ValueError(f"Cannot derive legal name for {src}: {name!r}")

    dest = BUNDLED / target_name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=_IGNORE)
    if target_name != name:
        _rewrite_name(dest / "SKILL.md", target_name)
    # Drop accidental node_modules if ignore missed nested
    for nm in dest.rglob("node_modules"):
        if nm.is_dir():
            shutil.rmtree(nm, ignore_errors=True)
    return target_name


def main() -> None:
    if BUNDLED.exists():
        shutil.rmtree(BUNDLED)
    BUNDLED.mkdir(parents=True)

    installed: list[str] = []

    skills_root = SERENITY / "skills"
    for d in sorted(skills_root.iterdir()):
        if d.is_dir() and (d / "SKILL.md").is_file():
            installed.append(_install_skill_dir(d))

    builtin_root = SERENITY / "builtin-skills"
    for d in sorted(builtin_root.iterdir()):
        if not d.is_dir() or d.name in SKIP_BUILTIN:
            continue
        if (d / "SKILL.md").is_file():
            installed.append(_install_skill_dir(d))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for zpath in CHEM_ZIPS:
            if not zpath.is_file():
                raise FileNotFoundError(zpath)
            dest = tmp_path / zpath.stem
            if dest.exists():
                shutil.rmtree(dest)
            with zipfile.ZipFile(zpath, "r") as zf:
                zf.extractall(dest)
            md_files = list(dest.rglob("SKILL.md"))
            if len(md_files) != 1:
                raise RuntimeError(f"{zpath.name}: expected 1 SKILL.md, got {len(md_files)}")
            installed.append(_install_skill_dir(md_files[0].parent))

    print(f"Installed {len(installed)} bundled skills into {BUNDLED}")
    for name in sorted(installed):
        print(f"  - {name}")
    assert "computer-use" not in installed
    assert not (BUNDLED / "serenity.industry-chain-mapping").exists()


if __name__ == "__main__":
    main()
