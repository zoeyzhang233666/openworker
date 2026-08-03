export const MERMAID_MAX_TEXT_SIZE = 50_000;
export const MERMAID_PNG_MAX_EDGE = 8192;
export const MERMAID_PNG_MAX_PIXELS = 16_000_000;

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

export function mermaidExportFilename(ext: "svg" | "png", at: Date = new Date()): string {
  const y = at.getFullYear();
  const mo = pad(at.getMonth() + 1);
  const d = pad(at.getDate());
  const h = pad(at.getHours());
  const mi = pad(at.getMinutes());
  const s = pad(at.getSeconds());
  return `chemclaw-diagram-${y}${mo}${d}-${h}${mi}${s}.${ext}`;
}

export function assertPngBounds(width: number, height: number): void {
  if (
    width > MERMAID_PNG_MAX_EDGE ||
    height > MERMAID_PNG_MAX_EDGE ||
    width * height > MERMAID_PNG_MAX_PIXELS
  ) {
    throw new Error("PNG_TOO_LARGE");
  }
}

export function downloadSvg(svg: string, filename = mermaidExportFilename("svg")): void {
  const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadPng(
  svg: string,
  filename = mermaidExportFilename("png"),
): Promise<void> {
  const svgUrl = URL.createObjectURL(
    new Blob([svg], { type: "image/svg+xml;charset=utf-8" }),
  );
  try {
    const img = await loadImage(svgUrl);
    assertPngBounds(img.naturalWidth || img.width, img.naturalHeight || img.height);
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("PNG_CANVAS_UNAVAILABLE");
    ctx.drawImage(img, 0, 0);
    const pngUrl = canvas.toDataURL("image/png");
    const a = document.createElement("a");
    a.href = pngUrl;
    a.download = filename;
    a.click();
  } finally {
    URL.revokeObjectURL(svgUrl);
  }
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("PNG_IMAGE_LOAD_FAILED"));
    img.src = url;
  });
}
