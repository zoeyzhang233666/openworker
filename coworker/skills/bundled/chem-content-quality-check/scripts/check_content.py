#!/usr/bin/env python3
"""Deterministic quality gate for chem platform rewrite outputs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


RULE_SET = "chem-content-quality@1.0.0"
# Marketing-ish long copy overlap threshold (chars); short spec lines are exempt.
MAX_MARKETING_LCS = 48
SPEC_HINT = re.compile(
    r"(CAS|纯度|%|kg|g/|吨|袋|桶|drum|purity|pack)",
    re.I,
)


def _lcs_length(a: str, b: str) -> int:
    if not a or not b:
        return 0
    # Bound cost for long texts
    a = a[:2000]
    b = b[:2000]
    prev = [0] * (len(b) + 1)
    best = 0
    for ch in a:
        cur = [0]
        for j, bh in enumerate(b, start=1):
            if ch == bh:
                val = prev[j - 1] + 1
                cur.append(val)
                if val > best:
                    best = val
            else:
                cur.append(0)
        prev = cur
    return best


def _fact_issues(brief: dict[str, Any], output: str) -> list[str]:
    issues: list[str] = []
    facts = brief.get("immutable_facts") or {}
    for key in ("product_name", "cas", "purity", "packaging"):
        value = facts.get(key)
        if isinstance(value, str) and value.strip() and value not in output:
            issues.append(f"missing_immutable:{key}:{value}")
    for claim in facts.get("numeric_claims") or []:
        if isinstance(claim, str) and claim.strip() and claim not in output:
            issues.append(f"missing_numeric_claim:{claim}")
    # Detect common purity drift when brief purity is present
    purity = facts.get("purity")
    if isinstance(purity, str) and purity.strip():
        found = re.findall(r"\d+(?:\.\d+)?\s*%", output)
        if found and purity not in found and all(p != purity for p in found):
            # If any percent appears that is not the brief purity and brief purity missing → already flagged;
            # additionally flag explicit alternate percents when brief purity absent from output.
            for p in found:
                if p != purity and purity not in output:
                    issues.append(f"purity_drift:{purity}->{p}")
                    break
    packaging = facts.get("packaging")
    if isinstance(packaging, str) and packaging.strip():
        packs = re.findall(r"\d+\s*kg\s*/\s*袋", output, flags=re.I)
        if packs and packaging not in output:
            for p in packs:
                issues.append(f"packaging_drift:{packaging}->{p}")
                break
    return issues


def _policy_issues(hits: list[dict[str, Any]], output: str) -> list[str]:
    issues: list[str] = []
    for hit in hits:
        term = hit.get("term") or ""
        severity = hit.get("severity") or "warning"
        if severity == "block" and term and term in output:
            issues.append(f"policy_block_residual:{term}")
        elif severity == "block":
            # Caller may pass pre-scan hits from source; residual in output is what matters.
            # If term not in output, treat as cleaned for that hit.
            pass
    # Also scan output for known hard terms if hits empty but text still dirty
    for term in ("绝对安全", "100%无风险", "包过", "国家级"):
        if term in output and not any(
            (h.get("term") == term and h.get("severity") == "block") for h in hits
        ):
            issues.append(f"policy_block_residual:{term}")
    return issues


def _platform_issues(output: str, required_sections: list[str]) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    for section in required_sections:
        token = section if section.startswith("【") else f"【{section}】"
        # Accept either 【标题】 or bare 标题： patterns
        if token not in output and f"【{section}】" not in output and f"{section}】" not in output:
            # also allow markdown-ish headers
            if f"{section}" in output and ("【" in output or "#" in output):
                # soft: section name appears inside bracketed layout elsewhere
                if f"【{section}】" not in output:
                    missing.append(section)
            else:
                missing.append(section)
    # Tighten: require 【section】 form
    missing = [s for s in required_sections if f"【{s}】" not in output]
    return ([f"missing_section:{s}" for s in missing], missing)


def _expression_issues(source: str, output: str) -> list[str]:
    # Strip obvious section markers for overlap check
    clean_out = re.sub(r"【[^】]+】", "", output)
    clean_src = source.strip()
    # Exempt if overlap looks like a short spec line
    lcs = _lcs_length(clean_src, clean_out)
    if lcs >= MAX_MARKETING_LCS:
        # Find a sample of the long overlap region roughly via shared chunk search
        for size in range(min(lcs, 80), MAX_MARKETING_LCS - 1, -1):
            for i in range(0, max(len(clean_src) - size + 1, 1)):
                chunk = clean_src[i : i + size]
                if chunk and chunk in clean_out and not SPEC_HINT.search(chunk):
                    return [f"long_verbatim_overlap:{size}"]
        # Spec-heavy overlap is OK
        if SPEC_HINT.search(clean_src) and SPEC_HINT.search(clean_out):
            return []
        return [f"long_verbatim_overlap:{lcs}"]
    return []


def check_content(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("source_text") or ""
    output = payload.get("output_text") or ""
    brief = payload.get("brief") or {}
    required = list(payload.get("required_sections") or [])
    hits = list(payload.get("policy_hits") or [])

    fact_issues = _fact_issues(brief, output)
    policy_issues = _policy_issues(hits, output)
    # If hits say blocked terms still conceptually "reported", also catch residuals
    for hit in hits:
        if hit.get("severity") == "block" and hit.get("term") in output:
            code = f"policy_block_residual:{hit['term']}"
            if code not in policy_issues:
                policy_issues.append(code)

    platform_issue_list, missing = _platform_issues(output, required)
    expr_issues = _expression_issues(source, output)

    fact_ok = not fact_issues
    policy_ok = not policy_issues
    platform_ok = not platform_issue_list
    expr_ok = not expr_issues

    if not policy_ok:
        verdict = "blocked"
        action = "revise"
    elif not fact_ok or not platform_ok or not expr_ok:
        verdict = "revise"
        action = "revise"
    else:
        verdict = "pass"
        action = "ready_for_publish_review"

    return {
        "schema_version": "chemclaw.content-gate.v1",
        "rule_set": RULE_SET,
        "verdict": verdict,
        "fact_integrity": {"passed": fact_ok, "issues": fact_issues},
        "policy_scan": {"passed": policy_ok, "issues": policy_issues},
        "platform_fit": {"passed": platform_ok, "issues": platform_issue_list},
        "independent_expression": {"passed": expr_ok, "issues": expr_issues},
        "missing_required_sections": missing,
        "recommended_action": action,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chem content quality gate")
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    result = check_content(payload)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
