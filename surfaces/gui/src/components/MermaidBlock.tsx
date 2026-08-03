import { useEffect, useRef, useState } from "react";
import {
  MERMAID_MAX_TEXT_SIZE,
  downloadPng,
  downloadSvg,
  mermaidExportFilename,
} from "../mermaidExports";
import { useI18n } from "../i18n";

let mermaidReady: Promise<typeof import("mermaid")> | null = null;

function ensureMermaid(): Promise<typeof import("mermaid")> {
  if (!mermaidReady) {
    mermaidReady = import("mermaid").then((mod) => {
      mod.default.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        maxTextSize: MERMAID_MAX_TEXT_SIZE,
        suppressErrorRendering: true,
        theme: "neutral",
      });
      return mod;
    });
  }
  return mermaidReady;
}

type ViewMode = "diagram" | "source";

export function MermaidBlock({ source }: { source: string }): JSX.Element {
  const { t } = useI18n();
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("diagram");
  const [lockedHeight, setLockedHeight] = useState<number | undefined>(undefined);
  // Reserved for Task 3 MermaidLightbox wiring (fullscreen omitted this task).
  const [lightboxOpen, setLightboxOpen] = useState(false);
  void lightboxOpen;
  void setLightboxOpen;
  const renderIdRef = useRef(0);
  const diagramRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const renderId = ++renderIdRef.current;
    setExportError(null);

    if (source.length > MERMAID_MAX_TEXT_SIZE) {
      setSvg(null);
      setError(t("mermaid.tooLong"));
      setView("source");
      return;
    }

    setError(null);
    setSvg(null);
    setView("diagram");
    setLockedHeight(undefined);

    let cancelled = false;
    (async () => {
      try {
        const mod = await ensureMermaid();
        if (cancelled || renderId !== renderIdRef.current) return;
        const id = `mermaid-${renderId}-${Math.random().toString(36).slice(2, 9)}`;
        const result = await mod.default.render(id, source);
        if (cancelled || renderId !== renderIdRef.current) return;
        setSvg(result.svg);
        setError(null);
      } catch {
        if (cancelled || renderId !== renderIdRef.current) return;
        setSvg(null);
        setError(t("mermaid.renderError"));
        setView("source");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [source, t]);

  useEffect(() => {
    if (!svg || view !== "diagram" || !diagramRef.current) return;
    const el = diagramRef.current;
    const h = el.offsetHeight || el.scrollHeight;
    if (h > 0) setLockedHeight(h);
  }, [svg, view]);

  async function onExportSvg() {
    if (!svg) return;
    setExportError(null);
    try {
      downloadSvg(svg, mermaidExportFilename("svg"));
    } catch {
      setExportError(t("mermaid.exportFailed"));
    }
  }

  async function onExportPng() {
    if (!svg) return;
    setExportError(null);
    try {
      await downloadPng(svg, mermaidExportFilename("png"));
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      setExportError(
        message === "PNG_TOO_LARGE" ? t("mermaid.pngTooLarge") : t("mermaid.exportFailed"),
      );
    }
  }

  const showDiagram = view === "diagram" && !!svg && !error;
  const showSource = view === "source" || !!error;

  return (
    <div
      className="mermaid-block"
      data-testid="mermaid-block"
      style={{
        minHeight: svg ? undefined : 180,
        height: lockedHeight,
      }}
    >
      <div className="mermaid-block-toolbar">
        <button
          type="button"
          disabled={!svg || !!error}
          aria-pressed={view === "diagram"}
          onClick={() => setView("diagram")}
        >
          {t("mermaid.diagram")}
        </button>
        <button
          type="button"
          aria-pressed={showSource}
          onClick={() => setView("source")}
        >
          {t("mermaid.source")}
        </button>
        <button type="button" disabled={!svg} onClick={() => void onExportSvg()}>
          {t("mermaid.exportSvg")}
        </button>
        <button type="button" disabled={!svg} onClick={() => void onExportPng()}>
          {t("mermaid.exportPng")}
        </button>
      </div>
      {(error || exportError) && (
        <div className="mermaid-block-error" data-testid="mermaid-error">
          {error || exportError}
        </div>
      )}
      {showDiagram && (
        <div
          ref={diagramRef}
          className="mermaid-block-diagram"
          data-testid="mermaid-diagram"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      )}
      {!svg && !error && (
        <div className="mermaid-block-diagram" aria-busy="true">
          {t("mermaid.loading")}
        </div>
      )}
      {showSource && (
        <pre className="mermaid-block-source" data-testid="mermaid-source">
          {source}
        </pre>
      )}
    </div>
  );
}
