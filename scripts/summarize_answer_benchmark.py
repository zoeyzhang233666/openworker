"""Summarize explicitly exported benchmark records. No model, network or live DB access.

Input: [{case_id, variant, configuration_id, measurement_kind: offline|live,
         trace: TurnTrace JSON, first_useful_answer_ms?: number,
         screen_first_text_ms?: number, quality?: {dimension: 0|1|2}}]
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from statistics import median
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coworker.tracing.models import TurnTrace


QUALITY = ("coverage", "factuality", "citation_support", "analysis", "uncertainty", "readability")


def distribution(values):
    numbers = sorted(v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)
                     and math.isfinite(v) and v >= 0)
    return {"n": len(numbers), "median": median(numbers) if numbers else None,
            # Small samples cannot support a stable tail estimate.
            "p95": numbers[math.ceil(len(numbers) * .95) - 1] if len(numbers) >= 20 else None}


def summarize(records):
    groups = defaultdict(list)
    for row in records:
        if row.get("measurement_kind") not in {"offline", "live"}:
            raise ValueError("measurement_kind 必须为 offline 或 live")
        for field in ("case_id", "variant", "configuration_id"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"缺少 {field}")
        trace = TurnTrace.model_validate(row["trace"])
        key = (row["case_id"], row["variant"], row["configuration_id"], row["measurement_kind"], trace.model)
        groups[key].append((row, trace))
    result = []
    for key, entries in sorted(groups.items()):
        metrics = defaultdict(list, {"first_call_upstream_content_ms": [], "http_header_wait_ms": []})
        quality = defaultdict(list)
        statuses = defaultdict(int)
        usage_complete = 0
        for row, trace in entries:
            statuses[trace.status] += 1
            metrics["total_ms"].append(trace.stage_elapsed_ms.get("total"))
            metrics["first_engine_text_ms"].append(trace.stage_elapsed_ms.get("first_engine_text"))
            for stage in ("model_calls", "tools_and_approval", "compaction"):
                metrics[stage + "_ms"].append(trace.stage_elapsed_ms.get(stage))
            metrics["screen_first_text_ms"].append(row.get("screen_first_text_ms"))
            metrics["first_useful_answer_ms"].append(row.get("first_useful_answer_ms"))
            metrics["model_calls"].append(trace.model_calls)
            metrics["tool_calls"].append(trace.tool_calls)
            metrics["web_calls"].append(trace.web_calls)
            complete = trace.model_calls > 0 and trace.usage_reported_calls == trace.model_calls
            usage_complete += int(complete)
            for name in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"):
                metrics[name].append(getattr(trace, name) if complete else None)
            if trace.model_call_timings:
                first = trace.model_call_timings[0]
                metrics["first_call_upstream_content_ms"].append(first.upstream_first_content_ms)
                for call in trace.model_call_timings:
                    metrics["provider_prepare_ms"].append(call.provider_start_ms)
                    for request in call.http_requests:
                        metrics["http_header_wait_ms"].append(
                            request.headers_ms - request.request_ms if request.headers_ms is not None else None)
            scores = row.get("quality") or {}
            for dimension in QUALITY:
                score = scores.get(dimension)
                quality[dimension].append(score if type(score) is int and 0 <= score <= 2 else None)
        result.append({**dict(zip(("case_id", "variant", "configuration_id", "measurement_kind", "model"), key)),
                       "samples": len(entries), "statuses": dict(statuses),
                       "complete_usage_samples": usage_complete,
                       "metrics": {k: distribution(v) for k, v in sorted(metrics.items())},
                       "quality": {k: distribution(v) for k, v in sorted(quality.items())}})
    return {"version": 1, "groups": result,
            "notes": ["offline 仅验证计时链路，不能代表真实速度。", "缺失值不按零计算；P95 至少需要 20 个有效样本。",
                      "引擎正文可包含过程叙述，不能当作屏幕绘制或有用结论。", "不同配置分组；质量评分由人工核验填写。",
                      "HTTP 等待分布按请求计数；总耗时分布按轮次计数。"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = summarize(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
