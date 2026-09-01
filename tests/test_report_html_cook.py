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
    assert "chartjs-plugin-zoom" in result.html
    assert "requestFullscreen" in result.html
    assert "chemclaw-chart-0" in result.html
    assert result.local_path is not None and result.local_path.is_file()


def test_cook_html_includes_mobile_chart_polish():
    md = """```chart
{"version":1,"type":"line","title":"现货","labels":["d1","d2"],"series":[{"name":"价","values":[1,2]}]}
```"""
    result = cook_report_html(md, write_local=False)
    assert "max-width: 640px" in result.html
    assert "chart-wrap { height: clamp(280px, 52vw, 420px);" in result.html
    assert "zoomScale('x'" in result.html
    assert "labels.length - 24" in result.html


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


def test_cook_css_has_table_and_mermaid_polish():
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
    from coworker.channels.wecom_reply import wecom_turn_guidance_suffix

    g = wecom_turn_guidance_suffix()
    assert "不要用 send_file 发送" in g or ".md" in g
    assert "普通问答" in g
    assert "精装 HTML" in g


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
