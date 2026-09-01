"""Cook Markdown report into a single-file ChemClaw HTML page (D-195 / D-195b)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Optional

from .chart_spec import bake_short_ref, parse_chart_spec
from .chart_theme import (
    CN_CANDLE_DOWN,
    CN_CANDLE_DOWN_WICK,
    CN_CANDLE_UP,
    CN_CANDLE_UP_WICK,
    SERIES_COLORS,
)
from .md_html import markdown_to_html_fragments

_ARTIFACT_MD = re.compile(
    r"\[[^\]]*\]\(artifact:([^)]+\.md)\)", re.IGNORECASE
)

CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
ZOOM_CDN = "https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"
HAMMER_CDN = "https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js"
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"


@dataclass
class CookResult:
    html: str
    title: str
    chart_count: int
    mermaid_count: int = 0
    local_path: Optional[Path] = None


def find_report_markdown(
    text: str,
    workspace: Path | str | None,
) -> Optional[Path]:
    """Prefer artifact:.md from assistant text; else newest non-hidden .md in workspace root."""
    ws = Path(workspace) if workspace else None
    if ws is not None and text:
        for match in _ARTIFACT_MD.finditer(text):
            rel = match.group(1).strip().lstrip("./")
            candidate = (ws / rel).resolve()
            try:
                candidate.relative_to(ws.resolve())
            except ValueError:
                continue
            if candidate.is_file() and not candidate.is_symlink():
                return candidate
    if ws is None or not ws.is_dir():
        return None
    md_files: list[Path] = []
    for path in ws.iterdir():
        if path.is_symlink() or not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() in {".md", ".markdown"}:
            md_files.append(path)
    if not md_files:
        for sub in ws.iterdir():
            if not sub.is_dir() or sub.name.startswith(".") or sub.name.startswith("_"):
                continue
            for path in sub.glob("*.md"):
                if path.is_file() and not path.is_symlink():
                    md_files.append(path)
    if not md_files:
        return None
    md_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return md_files[0]


def cook_report_html(
    markdown: str,
    *,
    title: str = "ChemClaw 报告",
    chart_tool_results: list[dict[str, Any]] | None = None,
    workspace: Path | str | None = None,
    write_local: bool = True,
) -> CookResult:
    charts: list[dict[str, Any]] = []
    mermaid_count = 0

    def fence_renderer(lang: str, body: str, index: int) -> str:
        nonlocal mermaid_count
        lang_l = (lang or "").strip().lower()
        if lang_l in {"mermaid", "mmd"}:
            mermaid_count += 1
            # Mermaid reads textContent; escape so HTML stays safe.
            return (
                f'<figure class="diagram-figure">'
                f'<figcaption class="diagram-caption">结构图</figcaption>'
                f'<div class="mermaid-wrap">'
                f'<div class="mermaid">{escape(body.rstrip())}</div>'
                f'<pre class="mermaid-fallback" hidden>{escape(body.rstrip())}</pre>'
                f"</div></figure>"
            )
        if lang_l != "chart":
            return (
                f'<pre><code class="language-{escape(lang_l)}">'
                f"{escape(body.rstrip())}</code></pre>"
            )
        raw: Any
        try:
            raw = json.loads(body)
        except json.JSONDecodeError:
            return '<div class="chart-error">图表 JSON 无法解析</div>'
        if isinstance(raw, dict):
            raw = bake_short_ref(raw, chart_tool_results)
        spec, err = parse_chart_spec(raw)
        if err or spec is None:
            return f'<div class="chart-error">图表不可用：{escape(err or "未知错误")}</div>'
        chart_id = f"chemclaw-chart-{len(charts)}"
        charts.append(spec)
        chart_title = escape(str(spec.get("title") or "图表"))
        return (
            f'<figure class="chart-figure" data-chart-index="{len(charts) - 1}">'
            f'<div class="chart-toolbar">'
            f"<figcaption>{chart_title}</figcaption>"
            f'<button type="button" class="chart-fs-btn" data-chart-fs="{chart_id}" '
            f'aria-label="全屏">全屏</button>'
            f"</div>"
            f'<div class="chart-wrap" id="{chart_id}-wrap">'
            f'<canvas id="{chart_id}"></canvas>'
            f"</div></figure>"
        )

    body_html = markdown_to_html_fragments(markdown, fence_renderer=fence_renderer)
    # Wrap tables for mobile horizontal scroll.
    body_html = re.sub(
        r"<table>",
        '<div class="table-scroll"><table>',
        body_html,
    )
    body_html = re.sub(r"</table>", "</table></div>", body_html)

    page_title = title
    first_h = re.search(r"^#\s+(.+)$", markdown or "", re.MULTILINE)
    if first_h:
        page_title = first_h.group(1).strip()[:120]
    html = _wrap_page(
        page_title, body_html, charts, mermaid_count=mermaid_count
    )
    local_path: Optional[Path] = None
    if write_local and workspace:
        ws = Path(workspace)
        out_dir = ws / "._chemclaw" / "reports"
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", page_title)[:60] or "report"
            local_path = out_dir / f"{safe}.html"
            local_path.write_text(html, encoding="utf-8")
        except OSError:
            local_path = None
    return CookResult(
        html=html,
        title=page_title,
        chart_count=len(charts),
        mermaid_count=mermaid_count,
        local_path=local_path,
    )


def _wrap_page(
    title: str,
    body_html: str,
    charts: list[dict[str, Any]],
    *,
    mermaid_count: int = 0,
) -> str:
    charts_json = json.dumps(charts, ensure_ascii=False)
    colors_json = json.dumps(list(SERIES_COLORS))
    mermaid_script = ""
    if mermaid_count > 0:
        mermaid_script = f"""
<script src="{MERMAID_CDN}"></script>
<script>
(function() {{
  function showFallbacks() {{
    document.querySelectorAll('.mermaid-wrap').forEach(function(wrap) {{
      var fb = wrap.querySelector('.mermaid-fallback');
      var live = wrap.querySelector('.mermaid');
      if (fb) {{ fb.hidden = false; }}
      if (live) {{ live.style.display = 'none'; }}
    }});
  }}
  if (typeof mermaid === 'undefined') {{
    showFallbacks();
    return;
  }}
  try {{
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'neutral',
      securityLevel: 'strict',
      flowchart: {{ htmlLabels: true, curve: 'basis' }}
    }});
  }} catch (err) {{
    showFallbacks();
  }}
}})();
</script>
"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{escape(title)}</title>
<style>
{_REPORT_CSS}
</style>
</head>
<body>
<div class="shell">
  <header class="brand">
    <div class="product">ChemClaw</div>
    <h1>{escape(title)}</h1>
  </header>
  <article class="report">
{body_html}
  </article>
  <footer class="note">由 ChemClaw 从 Markdown 报告生成 · 表格与结构图已排版 · 行情图支持缩放与全屏</footer>
</div>
<script src="{HAMMER_CDN}"></script>
<script src="{CHART_JS_CDN}"></script>
<script src="{ZOOM_CDN}"></script>
{mermaid_script}
<script>
(function() {{
  const SPECS = {charts_json};
  const COLORS = {colors_json};
  const UP = "{CN_CANDLE_UP}";
  const DOWN = "{CN_CANDLE_DOWN}";
  const UP_W = "{CN_CANDLE_UP_WICK}";
  const DOWN_W = "{CN_CANDLE_DOWN_WICK}";
  if (typeof Chart === "undefined" || !SPECS.length) return;
  if (typeof ChartZoom !== "undefined") {{
    Chart.register(ChartZoom);
  }} else if (window['chartjs-plugin-zoom']) {{
    Chart.register(window['chartjs-plugin-zoom']);
  }}
  function candleData(spec) {{
    const labels = spec.labels || [];
    const ohlc = spec.ohlc || [];
    return labels.map(function(label, i) {{
      const b = ohlc[i] || {{o:0,h:0,l:0,c:0}};
      return {{ x: i, o: b.o, h: b.h, l: b.l, c: b.c, label: label }};
    }});
  }}
  function buildConfig(spec) {{
    const labels = spec.labels || [];
    const mobile = typeof window !== 'undefined' && window.matchMedia('(max-width: 640px)').matches;
    const zoomOpts = {{
      zoom: {{ wheel: {{ enabled: true }}, pinch: {{ enabled: true }}, mode: 'x' }},
      pan: {{ enabled: true, mode: 'x' }}
    }};
    if (spec.type === 'candlestick') {{
      const pts = candleData(spec);
      return {{
        type: 'bar',
        data: {{
          labels: labels,
          datasets: [{{
            label: spec.title || 'OHLC',
            data: pts.map(function(p) {{ return [p.l, p.h]; }}),
            backgroundColor: pts.map(function(p) {{ return p.c >= p.o ? UP : DOWN; }}),
            borderColor: pts.map(function(p) {{ return p.c >= p.o ? UP_W : DOWN_W; }}),
            borderWidth: 1,
            barPercentage: 0.4,
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                label: function(ctx) {{
                  const p = pts[ctx.dataIndex];
                  if (!p) return '';
                  return '开 '+p.o+' 高 '+p.h+' 低 '+p.l+' 收 '+p.c;
                }}
              }}
            }},
            zoom: zoomOpts
          }},
          scales: {{
            x: {{ ticks: {{ maxTicksLimit: mobile ? 6 : 8, maxRotation: mobile ? 45 : 0, autoSkip: true }} }},
            y: {{ beginAtZero: false }}
          }}
        }}
      }};
    }}
    const type = spec.type === 'area' ? 'line' : (spec.type || 'line');
    const datasets = (spec.series || []).map(function(s, i) {{
      const color = COLORS[i % COLORS.length];
      return {{
        label: s.name,
        data: s.values,
        borderColor: color,
        backgroundColor: spec.type === 'area' ? color + '33' : color,
        fill: spec.type === 'area',
        tension: 0.25,
        pointRadius: labels.length > 24 ? 0 : 2,
      }};
    }});
    return {{
      type: type === 'scatter' ? 'scatter' : type,
      data: {{ labels: labels, datasets: datasets }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: spec.showLegend !== false }},
          zoom: zoomOpts
        }},
        scales: {{
          x: {{ ticks: {{ maxTicksLimit: mobile ? 6 : 8, maxRotation: mobile ? 45 : 0, autoSkip: true }} }},
          y: {{
            beginAtZero: false,
            min: spec.yMin,
            max: spec.yMax,
            title: {{ display: !!spec.yTitle, text: spec.yTitle || '' }}
          }}
        }}
      }}
    }};
  }}
  SPECS.forEach(function(spec, idx) {{
    const canvas = document.getElementById('chemclaw-chart-' + idx);
    if (!canvas) return;
    const labels = spec.labels || [];
    const chart = new Chart(canvas.getContext('2d'), buildConfig(spec));
    if (labels.length > 24 && chart.options.plugins && chart.options.plugins.zoom) {{
      const start = Math.max(0, labels.length - 24);
      chart.zoomScale('x', {{ min: start, max: labels.length - 1 }});
    }}
    const btn = document.querySelector('[data-chart-fs="chemclaw-chart-' + idx + '"]');
    const wrap = document.getElementById('chemclaw-chart-' + idx + '-wrap');
    if (btn && wrap) {{
      btn.addEventListener('click', function() {{
        const req = wrap.requestFullscreen || wrap.webkitRequestFullscreen;
        if (document.fullscreenElement || document.webkitFullscreenElement) {{
          (document.exitFullscreen || document.webkitExitFullscreen).call(document);
        }} else if (req) {{
          req.call(wrap);
        }}
      }});
    }}
  }});
}})();
</script>
</body>
</html>
"""


_REPORT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
:root {
  --cc-blue: #2563eb;
  --cc-blue-soft: #dbeafe;
  --cc-bg: #f1f5f9;
  --cc-card: #ffffff;
  --cc-text: #0f172a;
  --cc-muted: #64748b;
  --cc-border: #e2e8f0;
  --cc-thead: #eff6ff;
  --cc-stripe: #f8fafc;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
  background:
    radial-gradient(1200px 400px at 10% -10%, #dbeafe 0%, transparent 55%),
    linear-gradient(180deg, #eef4ff 0%, var(--cc-bg) 280px);
  color: var(--cc-text);
  line-height: 1.7;
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
}
.shell {
  max-width: 920px;
  margin: 0 auto;
  padding: 2.25rem 1.25rem 4rem;
}
header.brand {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--cc-blue-soft);
}
header.brand .product {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--cc-blue);
  background: var(--cc-blue-soft);
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
}
header.brand h1 {
  margin: 0.65rem 0 0;
  font-family: "Source Serif 4", "Noto Sans SC", serif;
  font-size: clamp(1.55rem, 3vw, 2rem);
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.25;
}
article.report {
  background: var(--cc-card);
  border: 1px solid var(--cc-border);
  border-radius: 16px;
  padding: 1.75rem 1.5rem 2.25rem;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.06);
}
article.report > :first-child { margin-top: 0; }
article.report h1,
article.report h2,
article.report h3,
article.report h4 {
  font-family: "Source Serif 4", "Noto Sans SC", serif;
  line-height: 1.35;
  color: #0b1220;
  margin: 1.6em 0 0.55em;
  font-weight: 700;
}
article.report h1 { font-size: 1.55rem; }
article.report h2 {
  font-size: 1.28rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--cc-border);
}
article.report h3 { font-size: 1.1rem; color: #1e293b; }
article.report p { margin: 0.75em 0; }
article.report ul, article.report ol {
  margin: 0.65em 0 0.9em;
  padding-left: 1.35em;
}
article.report li { margin: 0.28em 0; }
article.report a { color: var(--cc-blue); text-decoration-thickness: 1px; }
article.report hr {
  border: 0;
  border-top: 1px solid var(--cc-border);
  margin: 1.75rem 0;
}
article.report blockquote {
  margin: 1rem 0;
  padding: 0.65rem 1rem;
  border-left: 3px solid var(--cc-blue);
  background: #f8fafc;
  color: #334155;
  border-radius: 0 8px 8px 0;
}
article.report code {
  background: #f1f5f9;
  padding: 0.12em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
}
article.report pre {
  background: #0f172a;
  color: #e2e8f0;
  padding: 1rem 1.1rem;
  border-radius: 10px;
  overflow-x: auto;
  font-size: 0.88rem;
  line-height: 1.55;
}
article.report pre code { background: transparent; color: inherit; padding: 0; }
.table-scroll {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin: 1.1rem 0 1.35rem;
  border: 1px solid var(--cc-border);
  border-radius: 10px;
}
article.report table {
  width: 100%;
  min-width: 520px;
  border-collapse: collapse;
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.45;
}
article.report th,
article.report td {
  border-bottom: 1px solid var(--cc-border);
  border-right: 1px solid var(--cc-border);
  padding: 0.65rem 0.75rem;
  text-align: left;
  vertical-align: top;
}
article.report th:last-child,
article.report td:last-child { border-right: 0; }
article.report thead th {
  background: var(--cc-thead);
  color: #1e3a8a;
  font-weight: 600;
  white-space: nowrap;
}
article.report tbody tr:nth-child(even) td { background: var(--cc-stripe); }
article.report tbody tr:hover td { background: #eff6ff; }
.chart-figure,
.diagram-figure {
  margin: 1.35rem 0;
  padding: 0.9rem 1rem 1rem;
  border: 1px solid var(--cc-border);
  border-radius: 12px;
  background: linear-gradient(180deg, #fafcff 0%, #fff 40%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
}
.diagram-caption,
.chart-toolbar figcaption {
  margin: 0 0 0.55rem;
  font-weight: 600;
  font-size: 0.92rem;
  color: #1e293b;
}
.chart-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
}
.chart-fs-btn {
  border: 1px solid var(--cc-border);
  background: #fff;
  color: var(--cc-text);
  border-radius: 6px;
  padding: 0.25rem 0.65rem;
  cursor: pointer;
  font-size: 0.8rem;
}
.chart-fs-btn:hover { border-color: var(--cc-blue); color: var(--cc-blue); }
.chart-wrap {
  position: relative;
  height: 320px;
  width: 100%;
}
.chart-wrap:fullscreen,
.chart-wrap:-webkit-full-screen {
  background: #fff;
  padding: 1.5rem;
  height: 100%;
}
.mermaid-wrap {
  overflow-x: auto;
  padding: 0.5rem 0.25rem;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
}
.mermaid {
  display: flex;
  justify-content: center;
  background: transparent;
}
.mermaid-fallback {
  margin: 0;
  white-space: pre-wrap;
  background: #f8fafc !important;
  color: #334155 !important;
  border: 1px solid var(--cc-border);
  font-size: 0.82rem;
}
.chart-error, .chart-missing {
  color: #b91c1c;
  background: #fef2f2;
  border-radius: 8px;
  padding: 0.75rem 1rem;
}
footer.note {
  margin-top: 1.35rem;
  color: var(--cc-muted);
  font-size: 0.78rem;
  text-align: center;
}
@media (max-width: 640px) {
  .shell { padding: 1.25rem 0.85rem 3rem; max-width: 100%; }
  article.report { padding: 1.2rem 1rem 1.6rem; border-radius: 12px; }
  article.report table { min-width: 480px; font-size: 0.85rem; }
  .chart-wrap { height: clamp(280px, 52vw, 420px); }
}
"""
