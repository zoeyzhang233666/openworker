"""Vendor superpowers + mattpocock skills into coworker/skills/bundled (D-072)."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BUNDLED = ROOT / "coworker" / "skills" / "bundled"
VENDOR = Path(r"D:/OpenWorker/.chemclaw-dev/vendor")

SOURCES = [
    (VENDOR / "superpowers" / "skills", "sp"),
    (VENDOR / "mattpocock-skills-zh-CN" / "skills", "matt"),
]

EXTRA = [
    (Path(r"C:/Users/EDY/.agents/skills/grilling"), "local"),
    (Path(r"C:/Users/EDY/.agents/skills/domain-modeling"), "local"),
]


def read_name(md: Path) -> str | None:
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    meta = yaml.safe_load(text[3:end]) or {}
    if not isinstance(meta, dict):
        return None
    name = str(meta.get("name") or "").strip()
    return name or None


def write_named(dest: Path, name: str, source_tag: str) -> None:
    md = dest / "SKILL.md"
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return
    end = text.find("\n---", 3)
    raw = text[3:end]
    body = text[end + 4 :]
    meta = yaml.safe_load(raw) or {}
    if not isinstance(meta, dict):
        meta = {}
    meta["name"] = name
    meta.setdefault("source", f"bundled:{source_tag}")
    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    md.write_text(f"---\n{front}\n---{body}", encoding="utf-8")


def unique_name(base: str, existing: set[str], prefix: str) -> str:
    if base not in existing:
        return base
    cand = f"{prefix}-{base}"
    while cand in existing:
        cand = f"{prefix}-{cand}"
    return cand


def ingest(skill_dir: Path, prefix: str, existing: set[str]) -> str | None:
    md = skill_dir / "SKILL.md"
    if not skill_dir.is_dir() or not md.is_file():
        return None
    try:
        name = read_name(md)
    except Exception:
        return None
    if not name or any(c in name for c in ("/", "\\", " ")) or ".." in name:
        name = skill_dir.name
    dest_name = unique_name(name, existing, prefix)
    dest = BUNDLED / dest_name
    if dest.exists():
        return None
    shutil.copytree(skill_dir, dest)
    write_named(dest, dest_name, prefix)
    existing.add(dest_name)
    return dest_name


def iter_skill_dirs(root: Path) -> list[Path]:
    """Return skill directories (contain SKILL.md), skipping nested skill trees' junk."""
    found: list[Path] = []
    root = root.resolve()
    for md in sorted(root.rglob("SKILL.md")):
        try:
            rel_parts = md.relative_to(root).parts
        except ValueError:
            continue
        if any(part.startswith(".") for part in rel_parts):
            continue
        if "deprecated" in rel_parts or "in-progress" in rel_parts:
            continue
        found.append(md.parent)
    return found


def main() -> None:
    BUNDLED.mkdir(parents=True, exist_ok=True)
    existing = {p.name for p in BUNDLED.iterdir() if p.is_dir()}
    copied: list[str] = []
    for root, prefix in SOURCES:
        if not root.is_dir():
            print("MISSING", root)
            continue
        for skill_dir in iter_skill_dirs(root):
            got = ingest(skill_dir, prefix, existing)
            if got:
                copied.append(got)
    for skill_dir, prefix in EXTRA:
        if skill_dir.is_dir():
            got = ingest(skill_dir, prefix, existing)
            if got:
                copied.append(got)
    notice = BUNDLED / "THIRD_PARTY_PROCESS_SKILLS.md"
    notice.write_text(
        "# Third-party process skills (ChemClaw D-071)\n\n"
        "Bundled from:\n\n"
        "- https://github.com/obra/superpowers (MIT)\n"
        "- https://github.com/vinvcn/mattpocock-skills-zh-CN (MIT; localization of mattpocock/skills)\n\n"
        "These skills are seeded into the skill library but are **not** default-mounted "
        "on personas. Load on demand via `load_skill` (global G4 pointer).\n",
        encoding="utf-8",
    )
    print(f"copied {len(copied)}")
    for n in copied:
        print(" ", n)
    print(f"bundled dirs {len([p for p in BUNDLED.iterdir() if p.is_dir()])}")


if __name__ == "__main__":
    main()
