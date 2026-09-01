"""Chart preview PNG for Channel delivery (D-199b).

Screenshots the first ``.chart-figure`` from a cooked report HTML page so IM clients
can show an inline image while the COS HTML link remains the interactive full version.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

PreviewRenderer = Callable[[Path], bytes]


def render_chart_preview_png(
    html_path: Path | str,
    *,
    render: Optional[PreviewRenderer] = None,
) -> bytes | None:
    """Return PNG bytes for the first chart on the page, or None on failure."""
    path = Path(html_path)
    if not path.is_file():
        return None
    try:
        if render is not None:
            return render(path)
        return _render_with_playwright(path)
    except Exception:
        return None


def _render_with_playwright(html_path: Path) -> bytes:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 800, "height": 480})
            page.goto(html_path.as_uri(), wait_until="domcontentloaded")
            page.wait_for_selector(".chart-figure canvas", timeout=5000)
            page.wait_for_function(
                """() => {
                  const canvas = document.querySelector('.chart-figure canvas');
                  if (!canvas) return false;
                  const ctx = canvas.getContext('2d');
                  if (!ctx) return false;
                  const sample = ctx.getImageData(0, 0, 1, 1).data;
                  return sample[3] > 0;
                }""",
                timeout=5000,
            )
            figure = page.locator(".chart-figure").first
            return figure.screenshot(type="png")
        finally:
            browser.close()
