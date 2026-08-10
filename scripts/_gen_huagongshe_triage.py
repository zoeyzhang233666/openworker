"""Generate ChemClaw Huagongshe/K-Dense skill triage markdown (D-112)."""

from __future__ import annotations

import json
import re
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(r"D:\化工社skills合集")
REPO = Path(__file__).resolve().parents[1]
OUT_MD = REPO / "docs" / "chemclaw" / "HUAGONGSHE_SKILL_TRIAGE.md"
OUT_JSON = REPO / "docs" / "chemclaw" / "fixtures" / "huagongshe_skill_triage.json"

CURATED: dict[str, dict] = {
    "uncertainty-and-units": {
        "tier": "DONE",
        "action": "done",
        "score": 5,
        "chemclaw": "已 D-111 vendor；询盘/转化可选；不进 Lead 评分",
        "lobster": "export-engagement 可选",
    },
    "scientific-critical-thinking": {
        "tier": "P0",
        "action": "vendor_optional",
        "score": 5,
        "chemclaw": "中文边界；挂企业核验可选；关闭 OpenRouter 示意图；不改 score_lead",
        "lobster": "export/domestic 文档可选；qualification 指针",
    },
    "market-research-reports": {
        "tier": "P1",
        "action": "adapt_merge",
        "score": 4,
        "chemclaw": "提炼 Claims Ledger/来源台账；不全量 TeX/资产包",
        "lobster": "报告场景按需，不强制",
    },
    "exploratory-data-analysis": {
        "tier": "P1",
        "action": "adapt_ref",
        "score": 3,
        "chemclaw": "借鉴表格审计增强海关/展会文件分析；不全量 vendor",
        "lobster": "export 文档可选",
    },
    "research-lookup": {
        "tier": "P1",
        "action": "adapt_ref",
        "score": 3,
        "chemclaw": "检索纪律/溯源并入 buyer-discovery；勿双轨搜索",
        "lobster": "export/domestic 可选提示",
    },
    "peer-review": {
        "tier": "P1",
        "action": "adapt_ref",
        "score": 3,
        "chemclaw": "提炼检查项供 sales-quality / 报告门禁",
        "lobster": "engagement 可选",
    },
    "database-lookup": {
        "tier": "P2",
        "action": "ref_only",
        "score": 2,
        "chemclaw": "查库模式参考；具体 API 走平台 Provider",
        "lobster": "—",
    },
    "ontology-term-resolution": {
        "tier": "P2",
        "action": "ref_only",
        "score": 2,
        "chemclaw": "术语归一可参考 product-intelligence",
        "lobster": "—",
    },
    "scientific-writing": {
        "tier": "P2",
        "action": "ref_only",
        "score": 2,
        "chemclaw": "与现有 MD/报告重叠",
        "lobster": "—",
    },
    "scientific-brainstorming": {
        "tier": "P2",
        "action": "ref_only",
        "score": 2,
        "chemclaw": "已有 brainstorming/grilling",
        "lobster": "—",
    },
    "parallel-web": {
        "tier": "P2",
        "action": "ref_only",
        "score": 2,
        "chemclaw": "平台已有 web search",
        "lobster": "—",
    },
    "medchem": {
        "tier": "P2",
        "action": "ref_only",
        "score": 2,
        "chemclaw": "研发向；特殊 SKU 化学证据时参考",
        "lobster": "—",
    },
    "experimental-design": {
        "tier": "P2",
        "action": "ref_only",
        "score": 2,
        "chemclaw": "非销售主轴",
        "lobster": "—",
    },
    "statistical-analysis": {
        "tier": "P2",
        "action": "ref_only",
        "score": 2,
        "chemclaw": "报价敏感时偶用；勿整装",
        "lobster": "—",
    },
    "hypothesis-testing": {
        "tier": "P2",
        "action": "ref_only",
        "score": 1,
        "chemclaw": "科研统计",
        "lobster": "—",
    },
    "power-analysis": {
        "tier": "P2",
        "action": "ref_only",
        "score": 1,
        "chemclaw": "科研统计",
        "lobster": "—",
    },
    "rdkit": {
        "tier": "Skip",
        "action": "skip",
        "score": 1,
        "chemclaw": "D-090：销售首包禁止重依赖",
        "lobster": "—",
    },
    "datamol": {
        "tier": "Skip",
        "action": "skip",
        "score": 1,
        "chemclaw": "D-090：销售首包禁止重依赖",
        "lobster": "—",
    },
    "deepchem": {
        "tier": "Skip",
        "action": "skip",
        "score": 1,
        "chemclaw": "重 ML / 非销售主轴",
        "lobster": "—",
    },
    "timesfm-forecasting": {
        "tier": "Skip",
        "action": "skip",
        "score": 1,
        "chemclaw": "依赖过重且业务价值未验证",
        "lobster": "—",
    },
}


def dep_risk(name: str, compat: str, py_count: int, key: bool, net: bool) -> str:
    blob = f"{compat} {name}".lower()
    if any(x in blob for x in ("rdkit", "torch", "tensorflow", "scipy", "numpy", "cuda")):
        return "heavy"
    if key:
        return "api_key"
    if net:
        return "network"
    if py_count > 5:
        return "scripts_heavy"
    if py_count > 0:
        return "scripts"
    return "none"


def infer_uncurated(name: str) -> dict:
    score, tier, action = 1, "Skip", "skip"
    chemclaw = "与芯化和云销售主轴无关，或成本/依赖过高"
    lobster = "—"
    if any(k in name for k in ("document", "pdf", "docx", "markdown", "citation", "bibliography", "latex")):
        tier, action, score, chemclaw = "P2", "ref_only", 2, "文档工具与现有产物/MD 重叠，仅借鉴"
    if any(k in name for k in ("plot", "chart", "visual", "schematic", "matplotlib", "seaborn", "plotly")):
        tier, action, score, chemclaw = "P2", "ref_only", 1, "可视化与现有 Mermaid/报告重叠"
    if "patent" in name:
        tier, action, score = "P1", "adapt_ref", 3
        chemclaw = "专利检索纪律可辅商机/产品情报；评估后提炼，勿整装重复 chem-patent-*"
        lobster = "opportunity/export 可选提示"
    if any(k in name for k in ("toxicity", "hazard", "safety", "reach", "ghs")):
        tier, action, score = "P1", "adapt_ref", 3
        chemclaw = "危化/合规辅助；优先增强已有 chem-hazard-check，勿重复内置"
        lobster = "engagement/export 可选"
    if "chembl" in name or name in ("chebi",):
        tier, action, score, chemclaw = "P2", "ref_only", 2, "化学库应走平台 Provider，不整包 Skill"
    return {
        "tier": tier,
        "action": action,
        "score": score,
        "chemclaw": chemclaw,
        "lobster": lobster,
    }


def main() -> None:
    idx = json.loads((ROOT / "kdense-skills.json").read_text(encoding="utf-8"))
    name_to_dir = {z.stem: z.parent.name for z in ROOT.rglob("*.zip")}
    rows: list[dict] = []

    for r in idx:
        name = r["name"]
        folder = name_to_dir.get(name, "")
        zpath = ROOT / folder / f"{name}.zip" if folder else None
        if zpath is None or not zpath.exists():
            zpath = next(ROOT.rglob(f"{name}.zip"), None)

        py_count = 0
        compat = ""
        net = False
        key = False
        license_ = (r.get("license") or "").strip()
        if zpath and zpath.exists():
            with zipfile.ZipFile(zpath) as zf:
                names = zf.namelist()
                py_count = sum(1 for n in names if n.endswith(".py"))
                sm = next((n for n in names if n.endswith("SKILL.md")), None)
                if sm:
                    text = zf.read(sm).decode("utf-8", errors="replace")
                    m = re.search(r"^compatibility:\s*(.+)$", text, re.M)
                    if m:
                        compat = m.group(1).strip()[:160]
                    m = re.search(r"^license:\s*(.+)$", text, re.M)
                    if m and not license_:
                        license_ = m.group(1).strip()
                    low = text.lower()
                    net = any(x in low for x in ("network", "http", "openrouter", "outbound", "api"))
                    key = any(x in low for x in ("api_key", "api key", "openrouter", "bearer token"))

        if name in CURATED:
            meta = CURATED[name]
        else:
            meta = infer_uncurated(name)

        rows.append(
            {
                "name": name,
                "folder": folder,
                "category": r.get("category"),
                "license": license_[:64],
                "files": r.get("file_count"),
                "py": py_count,
                "dep": dep_risk(name, compat, py_count, key, net),
                "score": meta["score"],
                "tier": meta["tier"],
                "action": meta["action"],
                "chemclaw": meta["chemclaw"],
                "lobster": meta["lobster"],
                "desc": (r.get("description") or "")[:120],
                "compat": compat[:140],
                "github": r.get("github_path") or "",
            }
        )

    rows.sort(
        key=lambda x: (
            {"DONE": 0, "P0": 1, "P1": 2, "P2": 3, "Skip": 4}[x["tier"]],
            -x["score"],
            x["name"],
        )
    )

    counts = Counter(x["tier"] for x in rows)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def table(subset: list[dict]) -> str:
        lines = [
            "| 包名 | 分 | 动作 | 依赖风险 | ChemClaw 适配建议 | 建议挂载 |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
        for x in subset:
            lines.append(
                f"| `{x['name']}` | {x['score']} | `{x['action']}` | `{x['dep']}` | {x['chemclaw']} | {x['lobster']} |"
            )
        return "\n".join(lines)

    p0 = [x for x in rows if x["tier"] == "P0"]
    p1 = [x for x in rows if x["tier"] == "P1"]
    p2 = [x for x in rows if x["tier"] == "P2"]
    done = [x for x in rows if x["tier"] == "DONE"]
    skip = [x for x in rows if x["tier"] == "Skip"]

    # group skip by folder for appendix
    by_folder: dict[str, list[str]] = {}
    for x in skip:
        by_folder.setdefault(x["folder"] or "(unknown)", []).append(x["name"])

    skip_sections = []
    for folder, names in sorted(by_folder.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        listed = ", ".join(f"`{n}`" for n in sorted(names))
        skip_sections.append(f"### {folder}（{len(names)}）\n\n{listed}\n")

    md = f"""# 化工社 / K-Dense 合集 Skill 分流表（ChemClaw）

> 状态：Triage 初稿（D-112）— **待用户确认 P0/P1 名单后方可实现**  
> 来源：`D:\\化工社skills合集`（158 zip + `kdense-skills.json`）  
> 机器可读：[`fixtures/huagongshe_skill_triage.json`](fixtures/huagongshe_skill_triage.json)  
> 生成脚本：`scripts/_gen_huagongshe_triage.py`（可复跑）

## 1. 结论摘要

| 档 | 数量 | 含义 |
| --- | ---: | --- |
| DONE | {counts.get('DONE', 0)} | 已内置 |
| **P0** | {counts.get('P0', 0)} | 优先 vendor 为可选 bundled Skill（每批仍 1 个） |
| **P1** | {counts.get('P1', 0)} | 值得做，但以**改写合并/提炼**为主，不全量复制 |
| P2 | {counts.get('P2', 0)} | 只借鉴规则或模板，不装 Skill |
| Skip | {counts.get('Skip', 0)} | 不做（生信/重 ML/平台 SaaS/与销售无关等） |

**本表不是批准批量安装。** 实现仍须逐包小任务 + 新 D 编号 + 测试。

硬规则（D-090 / 销售规格 §16）：

- 销售首包不引入 RDKit / Datamol / TimesFM / 生信主轴
- HTTP/API 进平台 Tool/Provider，不塞进 Skill
- 不覆盖 `score_lead` / Lead Fit 数值
- 需 OpenRouter 等密钥的示意图能力：ChemClaw 默认关闭
- 与已有 PubChem / GLEIF / 海关 / 报价 / 证据分级重复者降档

合集**不含**官方 `huagongshe-reaction-publisher`；该能力单独评估（写反应 API + Token + 审批），不在本 158 表内自动升级为 P0。

## 2. 动作图例

| action | 含义 |
| --- | --- |
| `done` | 已交付 |
| `vendor_optional` | 解压进 `bundled/`，中文边界，龙虾**可选** `load_skill`，不强制 `skills:` |
| `adapt_merge` | 提炼模板/规则并入现有 `chem-*`，不全量 vendor |
| `adapt_ref` | 写短 reference / 纪律条款并入现有 Skill，不装新用户可见包 |
| `ref_only` | 文档层借鉴，代码不引入 |
| `skip` | 明确不做 |

## 3. DONE

{table(done)}

## 4. P0（建议下一实现批，仍一次一包）

{table(p0)}

建议实现顺序：`scientific-critical-thinking` →（你确认后开 D-113 级小任务）。

## 5. P1（改写合并优先）

{table(p1)}

## 6. P2（只借鉴）

{table(p2)}

## 7. Skip 附录（按合集目录）

共 {len(skip)} 个。默认理由：非销售主轴、重依赖、实验室 SaaS 集成、或与已有 ChemClaw 能力重复且无增量。若你要「捞回」某一包，回复包名即可改档。

{"".join(skip_sections)}

## 8. 与官方化工社 API 的边界

| 能力 | 处理 |
| --- | --- |
| 合集 158（K-Dense） | 本表分流 |
| `huagongshe-reaction-publisher` + 搜索/反应 API | **另案**：平台 Tool + 审批写；不进 Lead 评分 |

## 9. 请你确认

请回复是否认可：

1. P0 名单（当前仅 `scientific-critical-thinking`）
2. P1 名单与「改写不整装」策略
3. 是否有 Skip 中要捞回的包名

确认后下一刀再实现第一个 P0（或你点名的包）。
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print("wrote", OUT_MD)
    print("wrote", OUT_JSON)
    print("tiers", dict(counts))


if __name__ == "__main__":
    main()
