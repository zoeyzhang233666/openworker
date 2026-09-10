"""Chart preview PNG for Channel delivery (D-199b / D-203).

Primary path: Matplotlib (Agg) from ChartSpec v1 — professional charts with
system CJK fonts. No Playwright / Chromium required. Optional Playwright remains
only as a last-resort HTML screenshot when Matplotlib is unavailable.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Callable, Optional

PreviewRenderer = Callable[[Path], bytes]

_LINE_COLORS = (
    "#2563EB",
    "#DC2626",
    "#16A34A",
    "#EA580C",
    "#7C3AED",
    "#0891B2",
)
_UP = "#EF4444"
_DOWN = "#22C55E"
_FONT_CANDIDATES = (
    "Microsoft YaHei",
    "Microsoft YaHei UI",
    "SimHei",
    "SimSun",
    "PingFang SC",
    "Hiragino Sans GB",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
    "Arial Unicode MS",
)


def render_chart_preview_png(
    html_path: Path | str,
    *,
    render: Optional[PreviewRenderer] = None,
    html_bytes: bytes | None = None,
    chart_specs: list[dict[str, Any]] | None = None,
) -> bytes | None:
    """Return PNG bytes for the first chart. Prefer Matplotlib ChartSpec render."""
    if chart_specs:
        png = render_chart_spec_png(chart_specs[0])
        if png:
            return png

    path = Path(html_path) if html_path else None
    if path is not None and path.is_file() and render is not None:
        try:
            png = render(path)
            if png:
                return png
        except Exception:
            pass
    _ = html_bytes
    return None


def render_chart_spec_png(spec: dict[str, Any]) -> bytes | None:
    """Rasterize ChartSpec v1 with Matplotlib Agg + system CJK fonts."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
    except ImportError:
        return None
    try:
        return _render_with_matplotlib(spec, plt, font_manager)
    except Exception:
        return None


def _configure_cjk_font(font_manager: Any, plt: Any) -> str:
    """Pick a system CJK font so Chinese titles/legends render on Windows/macOS/Linux."""
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((name for name in _FONT_CANDIDATES if name in available), None)
    if chosen is None:
        # Path-based fallback for Windows Fonts not yet registered by name.
        windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot") or r"C:\Windows"
        for filename, family in (
            ("msyh.ttc", "Microsoft YaHei"),
            ("msyhbd.ttc", "Microsoft YaHei"),
            ("simhei.ttf", "SimHei"),
            ("simsun.ttc", "SimSun"),
        ):
            path = Path(windir) / "Fonts" / filename
            if path.is_file():
                try:
                    font_manager.fontManager.addfont(str(path))
                    chosen = family
                    break
                except Exception:
                    continue
    if chosen:
        plt.rcParams["font.sans-serif"] = [chosen, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    return chosen or "DejaVu Sans"


def _render_with_matplotlib(spec: dict[str, Any], plt: Any, font_manager: Any) -> bytes:
    from matplotlib.patches import Rectangle

    _configure_cjk_font(font_manager, plt)
    title = str(spec.get("title") or "价格走势")
    unit = str(spec.get("unit") or "")
    ctype = str(spec.get("type") or "line")
    labels = [str(x) for x in (spec.get("labels") or [])]

    fig, ax = plt.subplots(figsize=(9.6, 5.4), dpi=120)
    fig.patch.set_facecolor("#FAFCFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_title(title, fontsize=14, fontweight="bold", color="#0F172A", pad=12)
    if unit:
        ax.set_ylabel(unit, fontsize=10, color="#64748B")

    if ctype == "candlestick":
        ohlc = [bar for bar in (spec.get("ohlc") or []) if isinstance(bar, dict)]
        if not ohlc:
            raise ValueError("empty ohlc")
        xs = list(range(len(ohlc)))
        for i, bar in enumerate(ohlc):
            o, h, l, c = float(bar["o"]), float(bar["h"]), float(bar["l"]), float(bar["c"])
            color = _UP if c >= o else _DOWN
            ax.vlines(i, l, h, color=color, linewidth=1.0, zorder=2)
            body_low, body_high = min(o, c), max(o, c)
            if body_high - body_low < (h - l) * 0.002:
                body_high = body_low + max((h - l) * 0.002, 1e-6)
            ax.add_patch(
                Rectangle(
                    (i - 0.3, body_low),
                    0.6,
                    body_high - body_low,
                    facecolor=color,
                    edgecolor=color,
                    linewidth=0.5,
                    zorder=3,
                )
            )
        ax.set_xlim(-0.8, len(ohlc) - 0.2)
        _set_x_ticks(ax, labels, xs)
    else:
        series = [item for item in (spec.get("series") or []) if isinstance(item, dict)]
        if not series:
            raise ValueError("empty series")
        xs = list(range(len(labels))) if labels else None
        for s_idx, item in enumerate(series[:8]):
            values = item.get("values") or []
            ys = [
                float(v) if isinstance(v, (int, float)) and v == v else None
                for v in values
            ]
            if xs is None:
                xs = list(range(len(ys)))
            color = _LINE_COLORS[s_idx % len(_LINE_COLORS)]
            name = str(item.get("name") or f"系列{s_idx + 1}")
            ax.plot(
                xs[: len(ys)],
                ys,
                color=color,
                linewidth=2.0,
                label=name,
                solid_capstyle="round",
            )
        if xs:
            ax.set_xlim(xs[0] - 0.2, xs[-1] + 0.2)
        _set_x_ticks(ax, labels, xs or [])
        if len(series) > 1 or (series and series[0].get("name")):
            ax.legend(
                loc="upper left",
                frameon=True,
                fancybox=False,
                edgecolor="#E2E8F0",
                fontsize=9,
            )

    ax.grid(True, axis="y", color="#E2E8F0", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#94A3B8")
    ax.spines["bottom"].set_color("#94A3B8")
    ax.tick_params(colors="#64748B", labelsize=9)
    fig.tight_layout(pad=1.2)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def _set_x_ticks(ax: Any, labels: list[str], xs: list[int]) -> None:
    if not labels or not xs:
        return
    n = min(len(labels), len(xs))
    step = max(1, (n - 1) // 6)
    tick_idx = list(range(0, n, step))
    if tick_idx[-1] != n - 1:
        tick_idx.append(n - 1)
    ax.set_xticks([xs[i] for i in tick_idx])
    ax.set_xticklabels([labels[i][-10:] for i in tick_idx], rotation=0)
