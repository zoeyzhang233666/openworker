import json
from copy import deepcopy

import pytest

from coworker.answer_context import chart_result, fast_evidence_view, unicode_json
from coworker.engine import chart_finished_sidecar
from coworker.providers import AssistantTurn, ToolCall
from coworker.report_html.chart_spec import bake_short_ref, collect_chart_tool_results_from_messages
from tests.test_engine import _collect
from tests.test_runtime_resume import engine


def test_unicode_view_is_lossless_and_not_a_literal_escape_decoder():
    data = {"中文": "业务组成：产品、服务", "literal": r"\u4e2d", "path": r"D:\工作区\report.md"}
    raw = json.dumps(data)
    assert json.loads(unicode_json(raw)) == data
    assert len(unicode_json(raw)) < len(raw)
    assert unicode_json(r"plain \u4e2d") == r"plain \u4e2d"


def test_web_excerpt_retains_sources_relevant_numbers_and_exact_recovery(tmp_path):
    snippet = "网站导航与一般说明。" * 300 + "业务构成：Alpha 产品收入 123.45 万元，日期 2026-09-29。" + "其他描述。" * 300
    raw = json.dumps({"provider": "fake", "results": [{"title": "Alpha 官网", "url": "https://example.test/about",
        "published_date": "2026-09-29", "snippet": snippet}]})
    view = json.loads(fast_evidence_view(raw, tool_name="web_search", query="Alpha 业务构成", workspace=tmp_path))
    assert "123.45" in view["results"][0]["snippet"]
    assert view["results"][0]["url"] == "https://example.test/about"
    assert view["results"][0]["published_date"] == "2026-09-29"
    assert json.loads((tmp_path / view["full_result_path"]).read_text(encoding="utf-8")) == json.loads(raw)
    assert len(json.dumps(view, ensure_ascii=False)) < len(raw) / 5
    assert fast_evidence_view(raw, tool_name="web_search", query="Alpha 业务构成", workspace=tmp_path) == json.dumps(view, ensure_ascii=False, separators=(",", ":"))


def test_failed_offload_keeps_evidence_and_never_advertises_missing_file(tmp_path):
    root = tmp_path / "file"
    root.write_text("not a directory")
    raw = json.dumps({"text": "价格 12.50 元。" * 2000, "url": "https://example.test"})
    view = fast_evidence_view(raw, tool_name="web_fetch", query="价格", workspace=root)
    assert json.loads(view) == json.loads(raw)
    assert "full_result_path" not in view


@pytest.mark.parametrize("kind", ["line", "candlestick"])
def test_full_chart_survives_live_history_and_html_but_not_model_arrays(tmp_path, kind):
    spec = {"version": 1, "type": kind, "title": "甲醇现货" if kind == "line" else "甲醇期货",
        "unit": "元/吨", "labels": [f"2026-08-{i:02d}" for i in range(1, 31)]}
    if kind == "line":
        spec["series"] = [{"name": "山东", "values": list(range(2000, 2030))}]
    else:
        spec["ohlc"] = [{"o": 2000 + i, "h": 2100 + i, "l": 1900 + i, "c": 2050 + i} for i in range(30)]
    name = "mcp__custom__series" if kind == "line" else "lookup_cn_futures_ohlc"
    result = chart_result(name, "call-price", {}, {"status": "ok", "chart_spec": spec, "source": "离线来源"})
    assert chart_finished_sidecar(result)["chart_id"] == "call-price"
    assert chart_finished_sidecar(result)["chart_spec"]["labels"] == spec["labels"]
    view = json.loads(fast_evidence_view(json.dumps(result), tool_name=name, query="查价格", workspace=tmp_path))
    assert view["chart_ref"] == {"version": 1, "from_tool": name, "chart_id": "call-price"}
    assert "ohlc" not in view and "chart_spec" not in view
    assert view["chart_summary"]["points"] == 30
    messages = [{"role": "assistant", "tool_calls": [{"id": "call-price", "function": {"name": name, "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "call-price", "content": json.dumps(result)}]
    restored = collect_chart_tool_results_from_messages(json.loads(json.dumps(messages)))
    baked = bake_short_ref(view["chart_ref"], restored)
    assert baked["labels"] == spec["labels"] and baked["type"] == kind
    bad_ref = {**view["chart_ref"], "chart_id": "missing"}
    assert bake_short_ref(bad_ref, restored) == bad_ref
    assert json.loads((tmp_path / view["full_result_path"]).read_text(encoding="utf-8")) == result


def test_spot_adaptation_preserves_raw_and_rejects_single_or_invalid_dates():
    name = "mcp__chem-data-hub__get_price_trend"
    rows = [{"date": "2026-09-28", "price": 2000, "region": "山东", "unit": "元/吨"},
        {"date": "2026-09-29", "price": 2020, "region": "山东", "unit": "元/吨"}]
    raw = {"code": 0, "data": rows}
    before = deepcopy(raw)
    result = chart_result(name, "spot", {"product_name": "甲醇"}, raw)
    assert raw == before and result["data"] == rows
    assert result["chart_spec"]["series"][0]["values"] == [2000, 2020]
    assert "chart_id" not in chart_result(name, "one", {}, {"data": rows[:1]})
    assert "chart_id" not in chart_result(name, "bad", {}, {"data": [{"price": 1}, {"price": 2}]})


def test_actual_engine_fast_outbound_reduces_unicode_replay_without_changing_history(tmp_path):
    result = {"results": [{"title": "业务构成", "url": "https://example.test", "snippet": "业务构成与产品服务。" * 500}]}
    tc = ToolCall("search", "web_search", {"query": "业务构成"})
    e, _ = engine(tmp_path, [AssistantTurn(tool_calls=[tc]), AssistantTurn(text="有来源的答案。", finish_reason="stop")])
    e.research_depth = "fast"
    def web_search(query: str):
        return result
    e.registry.register(web_search)
    captured = []
    complete = e.provider.complete
    def probe(**kwargs):
        captured.append(kwargs)
        return complete(**kwargs)
    e.provider.complete = probe
    assert _collect(e, "业务构成")[-1].data["status"] == "completed"
    outbound = next(m["content"] for m in captured[-1]["messages"] if m["role"] == "tool")
    canonical = next(m["content"] for m in e.messages if m["role"] == "tool")
    assert json.loads(canonical) == result
    assert len(outbound) < len(json.dumps(result)) / 5
    assert "https://example.test" in outbound
    assert not any(m.get("role") == "tool" and m.get("tool_call_id") != "search" for m in captured[-1]["messages"])


def test_deep_outbound_also_bounds_large_web_and_keeps_history_intact(tmp_path):
    """Deep mode still needs token hygiene; only the excerpt budget is larger."""
    result = {"results": [{"title": "业务构成", "url": "https://example.test/deep",
                           "snippet": "业务构成与产品服务。" * 800, "published_date": "2026-09-29"}]}
    tc = ToolCall("search", "web_search", {"query": "业务构成"})
    e, _ = engine(tmp_path, [AssistantTurn(tool_calls=[tc]), AssistantTurn(text="深度答案。", finish_reason="stop")])
    e.research_depth = "deep"
    def web_search(query: str):
        return result
    e.registry.register(web_search)
    captured = []
    complete = e.provider.complete
    def probe(**kwargs):
        captured.append(kwargs)
        return complete(**kwargs)
    e.provider.complete = probe
    assert _collect(e, "业务构成")[-1].data["status"] == "completed"
    outbound = next(m["content"] for m in captured[-1]["messages"] if m["role"] == "tool")
    view = json.loads(outbound)
    assert view["results"][0]["url"] == "https://example.test/deep"
    assert "业务构成" in view["results"][0]["snippet"]
    assert "full_result_path" in view
    assert len(outbound) < len(json.dumps(result, ensure_ascii=False)) / 3
    canonical = next(m["content"] for m in e.messages if m["role"] == "tool")
    assert json.loads(canonical) == result


def test_deep_keeps_small_unicode_evidence_without_offload(tmp_path):
    raw = json.dumps({"results": [{"title": "短", "url": "https://example.test", "snippet": "中文结果"}]}, ensure_ascii=True)
    messages = [{"role": "user", "content": "研究"}, {"role": "tool", "tool_call_id": "t", "content": raw}]
    e, _ = engine(tmp_path, [], messages=messages)
    e.research_depth = "deep"
    outbound = e._outbound_messages()[1]["content"]
    assert json.loads(outbound) == json.loads(raw)
    assert "full_result_path" not in outbound
    assert e.messages[1]["content"] == raw
    assert "\\u" not in outbound  # ASCII escapes removed for the provider copy
