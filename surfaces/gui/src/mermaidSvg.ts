export type PreparedLightboxSvg = {
  html: string;
  naturalW: number;
  naturalH: number;
};

export type LightboxSize = { w: number; h: number };

/**
 * Normalize Mermaid SVG for crisp fullscreen display: keep viewBox, drop fixed
 * width/height so CSS can size the vector without rasterizing a small bitmap.
 */
export function prepareLightboxSvg(svg: string): PreparedLightboxSvg {
  const doc = new DOMParser().parseFromString(svg, "image/svg+xml");
  const root = doc.documentElement;
  if (!root || root.tagName.toLowerCase() !== "svg") {
    return { html: svg, naturalW: 800, naturalH: 600 };
  }

  let naturalW = 800;
  let naturalH = 600;
  const viewBox = root.getAttribute("viewBox")?.trim();
  if (viewBox) {
    const parts = viewBox.split(/[\s,]+/).map(Number);
    if (parts.length === 4 && parts.every((n) => Number.isFinite(n))) {
      naturalW = Math.max(1, parts[2]);
      naturalH = Math.max(1, parts[3]);
    }
  } else {
    const w = parseFloat(root.getAttribute("width") || "");
    const h = parseFloat(root.getAttribute("height") || "");
    if (Number.isFinite(w) && Number.isFinite(h) && w > 0 && h > 0) {
      naturalW = w;
      naturalH = h;
      root.setAttribute("viewBox", `0 0 ${w} ${h}`);
    }
  }

  root.removeAttribute("width");
  root.removeAttribute("height");
  root.setAttribute("preserveAspectRatio", "xMidYMid meet");

  return {
    html: new XMLSerializer().serializeToString(root),
    naturalW,
    naturalH,
  };
}

/** Contain-fit a diagram into a viewport box, preserving aspect ratio. */
export function fitLightboxSize(
  naturalW: number,
  naturalH: number,
  viewportW: number,
  viewportH: number,
): LightboxSize {
  const nw = Math.max(1, naturalW);
  const nh = Math.max(1, naturalH);
  const vw = Math.max(1, viewportW);
  const vh = Math.max(1, viewportH);
  const scale = Math.min(vw / nw, vh / nh);
  return {
    w: Math.max(1, Math.round(nw * scale)),
    h: Math.max(1, Math.round(nh * scale)),
  };
}
