"""D-195 report HTML cook + ChartSpec bake tests."""

from __future__ import annotations

import json
from pathlib import Path

from coworker.filestore.memory import MemoryFileStorage
from coworker.report_html.cook import cook_report_html, find_report_markdown
from coworker.report_html.chart_spec import bake_short_ref, parse_chart_spec
from coworker.channels.wecom_reply import (
    compose_wecom_final_reply,
    wants_full_bubble,
)


def test_parse_line_chart_spec():
    spec, err = parse_chart_spec(
        {
            "version": 1,
            "type": "line",
            "title": "甲醇",
            "labels": ["d1", "d2", "d3"],
            "series": [{"name": "价格", "values": [1, 2, 3]}],
        }
    )
    assert err is None
    assert spec is not None
    assert spec["type"] == "line"
    assert len(spec["series"][0]["values"]) == 3


def test_parse_candlestick_array_ohlc():
    spec, err = parse_chart_spec(
        {
            "type": "candlestick",
            "labels": ["a", "b"],
            "ohlc": [[1, 2, 0.5, 1.5], [1.5, 2.5, 1, 2]],
        }
    )
    assert err is None
    assert spec["ohlc"][0]["o"] == 1


def test_bake_short_ref_from_tool_sidecar():
    raw = {"from_tool": "lookup_yahoo_ohlc", "symbol": "GC=F", "version": 1, "type": "candlestick"}
    baked = bake_short_ref(
        raw,
        [
            {
                "name": "lookup_yahoo_ohlc",
                "args": {"symbol": "GC=F"},
                "chart_spec": {
                    "version": 1,
                    "type": "candlestick",
                    "labels": ["2024-01-01", "2024-01-02"],
                    "ohlc": [{"o": 1, "h": 2, "l": 0.5, "c": 1.5}, {"o": 1.5, "h": 3, "l": 1, "c": 2}],
                },
            }
        ],
    )
    assert "labels" in baked
    assert baked.get("from_tool") is None
    spec, err = parse_chart_spec(baked)
    assert err is None and spec is not None


def test_bake_short_ref_cn_futures_symbol_fuzzy():
    raw = {
        "from_tool": "lookup_cn_futures_ohlc",
        "symbol": "SC2610",
        "version": 1,
        "type": "candlestick",
        "title": "上海原油期货 SC2610 (INE, 日线)",
    }
    baked = bake_short_ref(
        raw,
        [
            {
                "name": "lookup_cn_futures_ohlc",
                "args": {"symbol": "SC2610.INE"},
                "symbol": "SC2610.INE",
                "series_name": "上海原油",
                "aliases": ["SC2610", "原油"],
                "chart_spec": {
                    "version": 1,
                    "type": "candlestick",
                    "title": "SC2610.INE",
                    "labels": ["2026-06-01", "2026-06-02"],
                    "ohlc": [
                        {"o": 590, "h": 610, "l": 580, "c": 605},
                        {"o": 605, "h": 620, "l": 600, "c": 615},
                    ],
                },
            }
        ],
    )
    assert baked.get("from_tool") is None
    assert baked["title"] == "上海原油期货 SC2610 (INE, 日线)"
    spec, err = parse_chart_spec(baked)
    assert err is None and spec is not None
    assert len(spec["labels"]) == 2


def test_cook_short_ref_cn_futures_html():
    from coworker.report_html.chart_spec import collect_chart_tool_results_from_messages

    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc1",
                    "function": {
                        "name": "lookup_cn_futures_ohlc",
                        "arguments": '{"symbol":"SC2610.INE"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "tc1",
            "content": json.dumps(
                {
                    "status": "ok",
                    "symbol": "SC2610.INE",
                    "name": "上海原油",
                    "aliases": ["SC2610"],
                    "chart_spec": {
                        "version": 1,
                        "type": "candlestick",
                        "title": "SC2610.INE",
                        "labels": ["2026-06-01", "2026-06-02"],
                        "ohlc": [
                            {"o": 590, "h": 610, "l": 580, "c": 605},
                            {"o": 605, "h": 620, "l": 600, "c": 615},
                        ],
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]
    md = """已获取上海原油期货 SC2610 近三个月日线。

```chart
{"from_tool":"lookup_cn_futures_ohlc","symbol":"SC2610","type":"candlestick","version":1}
```
"""
    sidecars = collect_chart_tool_results_from_messages(messages)
    result = cook_report_html(md, chart_tool_results=sidecars, write_local=False)
    assert result.chart_count == 1
    assert "短引用图表缺少烘焙数据" not in result.html
    assert "chemclaw-chart-0" in result.html


def test_cook_embeds_chart_js_zoom_and_fullscreen(tmp_path: Path):
    md = """# 价格报告

要点如下。

```chart
{"version":1,"type":"line","title":"现货","labels":["1月","2月","3月"],"series":[{"name":"价","values":[100,110,105]}]}
```
"""
    result = cook_report_html(md, workspace=tmp_path, write_local=True)
    assert result.chart_count == 1
    assert "chart.js" in result.html
    assert "chartjs-chart-financial" in result.html
    assert "chartjs-plugin-zoom" in result.html
    assert "chart-axis-panel" in result.html
    assert "CHEMCLAW_CHART_BOOT" in result.html
    assert "chemclaw-chart-0" in result.html
    assert result.local_path is not None and result.local_path.is_file()


def test_cook_html_includes_mobile_chart_polish():
    md = """```chart
{"version":1,"type":"line","title":"现货","labels":["d1","d2"],"series":[{"name":"价","values":[1,2]}]}
```"""
    result = cook_report_html(md, write_local=False)
    assert "max-width: 640px" in result.html
    assert "chart-wrap--interactive" in result.html
    assert "zoomScale('x'" in result.html or "onZoomComplete" in result.html


def test_cook_renders_gfm_tables_as_html():
    md = """# 报告

### 主体清单

| 主体 | 统一社会信用代码 | 成立日 |
|---|---|---|
| 上海芯化和云科技有限公司 | 91310000MA1FL3XXXX | 2019-01-01 |
| 示例子公司 | 91310000MA1FL4XXXX | 2020-02-02 |

说明：以上为调研结果。
"""
    html = cook_report_html(md, write_local=False).html
    assert "<table>" in html
    assert "</table>" in html
    assert "table-scroll" in html
    assert "上海芯化和云科技有限公司" in html
    assert "|---|" not in html
    assert "thead" in html.lower() or "<th>" in html


def test_cook_renders_table_without_leading_pipes():
    md = """# T

Col A | Col B
--- | ---
一 | 二
"""
    html = cook_report_html(md, write_local=False).html
    assert "<table>" in html
    assert "<th>" in html
    assert "一" in html


def test_cook_renders_table_immediately_after_heading_with_chart():
    """Assistant market replies often omit the blank line before pipe tables."""
    md = """✅ 原油现货价格（口径：化工现货 · 山东市场 · 元/吨）

### 最新现货价（8/31，较前一交易日 8/28）
| 规格 | 价格 | 日涨跌 |
|---|---|---|
| 南美原油 | 6,040 元/吨 | -20 (-0.33%) |
| 阿曼原油 | 5,240 元/吨 | -25 (-0.47%) |

### 近 6 周走势要点
- 7 月下旬至 8 月上旬震荡

```chart
{"version":1,"type":"line","title":"走势","labels":["07-20","07-21"],"series":[{"name":"现货","values":[6000,6010]}]}
```
"""
    html = cook_report_html(md, write_local=False).html
    assert "<table>" in html
    assert "南美原油" in html
    assert "|---|" not in html
    assert "| 规格 |" not in html
    assert "chemclaw-chart-0" in html
    assert "<ul>" in html
    assert "7 月下旬至 8 月上旬震荡" in html


def test_cook_renders_markdown_lists_without_blank_line_after_heading():
    md = """**要点速览：**
- 最新收盘 (9/1)：5930 元/吨
- 6 月初至 7 月下旬震荡
- 8 月 28 日放量反弹

数据来源：新浪期货日线。
"""
    html = cook_report_html(md, write_local=False).html
    assert "<ul>" in html
    assert "<li>最新收盘 (9/1)：5930 元/吨</li>" in html
    assert "<p>- 最新收盘" not in html


def test_cook_html_includes_crosshair_status_and_dblclick():
    md = """```chart
{"version":1,"type":"line","title":"现货","labels":["d1","d2"],"series":[{"name":"价","values":[1,2]}]}
```"""
    html = cook_report_html(md, write_local=False).html
    assert "chemclaw-chart-0-status" in html
    assert "十字线跟随鼠标" in html
    assert "单击固定 · 双击取消" in html
    assert "updateCrosshairStatus" in html
    assert 'addEventListener("dblclick"' in html


def test_cook_html_footer_omits_layout_boilerplate():
    html = cook_report_html("# 报告\n\n正文", write_local=False).html
    assert "由 ChemClaw 从 Markdown 报告生成" in html
    assert "表格与结构图已排版" not in html


def test_cook_mermaid_uses_div_not_dark_code_block():
    md = """# 架构

```mermaid
graph TD
  W["实控人"] -->|"控股"| C["芯化和云"]
```
"""
    result = cook_report_html(md, write_local=False)
    assert result.mermaid_count == 1
    assert 'class="mermaid"' in result.html
    assert "mermaid@10" in result.html or "mermaid.min.js" in result.html
    assert "diagram-figure" in result.html
    # Must not dump mermaid as the sole dark pre/code treatment for this fence
    assert "```mermaid" not in result.html
    assert "graph TD" in result.html


def test_cook_html_includes_stage_band_runtime():
    md = """```chart
{"version":1,"type":"candlestick","title":"沥青","labels":["2026-06-01","2026-06-15","2026-07-01","2026-08-01"],"ohlc":[[4800,4900,4700,4850],[4850,4950,4800,4900],[4900,5000,4850,4950],[4950,5100,4900,5050]],"stages":[{"start":"2026-06-01","end":"2026-06-15","tone":"down","reason":"回调"},{"start":"2026-07-01","end":"2026-08-01","tone":"up","reason":"反弹"}]}
```"""
    html = cook_report_html(md, write_local=False).html
    assert "chartjs-plugin-annotation" in html
    assert "paintStageBands" in html or "stageBand" in html
    assert "beforeDatasetsDraw" in html
    assert "STAGE_TONE_COLORS" in html or "rgba(229, 57, 53, 0.12)" in html
    html = cook_report_html("# Hi\n\nhello", write_local=False).html
    assert "table-scroll" in html or ".table-scroll" in html
    assert "Noto Sans SC" in html
    assert "--cc-blue" in html
    assert "zebra" in html or "nth-child(even)" in html


def test_find_report_prefers_artifact_link(tmp_path: Path):
    report = tmp_path / "甲醇周报.md"
    report.write_text("# 周报\n\n正文", encoding="utf-8")
    other = tmp_path / "notes.md"
    other.write_text("old", encoding="utf-8")
    found = find_report_markdown(
        "结论见 [甲醇周报](artifact:甲醇周报.md)", tmp_path
    )
    assert found == report.resolve()


def test_wants_full_bubble_heuristic():
    assert wants_full_bubble("请把完整回答直接发在对话里")
    assert wants_full_bubble("不要链接，气泡里全文")
    assert not wants_full_bubble("帮我看看甲醇价格")


def test_compose_summary_link_uploads_html(tmp_path: Path):
    report = tmp_path / "研究.md"
    report.write_text("# 研究\n\n详细内容", encoding="utf-8")
    storage = MemoryFileStorage(pub_url="https://cos.example/")
    composed = compose_wecom_final_reply(
        assistant_text="结论三点。\n\n[研究](artifact:研究.md)",
        user_text="研究一下甲醇",
        workspace=tmp_path,
        file_storage=storage,
    )
    assert composed.mode == "summary_link"
    assert composed.html_url
    assert "查看完整版" in composed.text
    assert composed.html_url.startswith("https://cos.example/")
    # Ensure uploaded object is HTML
    assert any(k.endswith(".html") or "html" in k for k in storage.objects)


def test_compose_full_bubble_skips_html(tmp_path: Path):
    report = tmp_path / "研究.md"
    report.write_text("# 研究\n\n详细", encoding="utf-8")
    storage = MemoryFileStorage()
    composed = compose_wecom_final_reply(
        assistant_text="很长的全文……\n\n[研究](artifact:研究.md)",
        user_text="请把完整回答直接发在对话里",
        workspace=tmp_path,
        file_storage=storage,
    )
    assert composed.mode == "full_bubble"
    assert composed.html_url is None
    assert "查看完整版" not in composed.text
    assert storage.objects == {}


def test_compose_without_md_no_fake_html(tmp_path: Path):
    storage = MemoryFileStorage()
    composed = compose_wecom_final_reply(
        assistant_text="你好，我是 ChemClaw。",
        user_text="你好",
        workspace=tmp_path,
        file_storage=storage,
    )
    assert composed.mode == "summary_only"
    assert "查看完整版" not in composed.text
    assert storage.objects == {}


def test_strip_md_artifacts_from_wecom_bubble():
    from coworker.channels.wecom_reply import strip_md_artifacts_for_wecom

    cleaned = strip_md_artifacts_for_wecom(
        "结论三点。\n\n[企业调研报告](artifact:企业调研报告.md)\n完。"
    )
    assert "artifact:" not in cleaned
    assert ".md" not in cleaned
    assert "企业调研报告" in cleaned


def test_wecom_guidance_forbids_md_files():
    from coworker.channels.wecom_reply import channel_turn_guidance_suffix, wecom_turn_guidance_suffix

    g = wecom_turn_guidance_suffix()
    assert "send_file" in g
    assert "```chart" in g
    assert "禁止声称" in g or "无法发送" in g
    assert "精装 HTML" in g or "HTML" in g
    assert "查价要快" in g
    assert "无法调用 MCP" in g
    assert channel_turn_guidance_suffix("weixin") != ""
    assert "```chart" in channel_turn_guidance_suffix("feishu")


def test_compose_summary_strips_artifact_md(tmp_path: Path):
    report = tmp_path / "研究.md"
    report.write_text("# 研究\n\n详细内容", encoding="utf-8")
    storage = MemoryFileStorage(pub_url="https://cos.example/")
    composed = compose_wecom_final_reply(
        assistant_text="结论三点。\n\n[研究](artifact:研究.md)",
        user_text="研究一下甲醇",
        workspace=tmp_path,
        file_storage=storage,
    )
    assert composed.mode == "summary_link"
    assert "artifact:" not in composed.text
    assert "查看完整版" in composed.text
    assert composed.html_url


def test_compose_cos_missing_degrades(tmp_path: Path):
    from coworker.filestore.base import NullFileStorage

    report = tmp_path / "研究.md"
    report.write_text("# 研究\n\n详细", encoding="utf-8")
    composed = compose_wecom_final_reply(
        assistant_text="结论。\n\n[研究](artifact:研究.md)",
        user_text="写份报告",
        workspace=tmp_path,
        file_storage=NullFileStorage(),
    )
    assert composed.mode == "summary_only"
    assert "云文件存储" in composed.text
