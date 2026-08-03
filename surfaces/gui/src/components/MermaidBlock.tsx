import { useEffect, useRef, useState } from "react";
import {
  MERMAID_MAX_TEXT_SIZE,
  downloadPng,
  downloadSvg,
  mermaidExportFilename,
} from "../mermaidExports";
import { useI18n } from "../i18n";
import { MermaidLightbox } from "./MermaidLightbox";

let mermaidReady: Promise<typeof import("mermaid")> | null = null;

function ensureMermaid(): Promise<typeof import("mermaid")> {
  if (!mermaidReady) {
    mermaidReady = import("mermaid").then((mod) => {
      mod.default.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        maxTextSize: MERMAID_MAX_TEXT_SIZE,
        suppressErrorRendering: true,
        theme: "neo",
      });
      return mod;
    });
  }
  return mermaidReady;
}

type ViewMode = "diagram" | "source";

export function MermaidBlock({ source }: { source: string }): JSX.Element {
  const { t } = useI18n();
  const tRef = useRef(t);
  tRef.current = t;
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("diagram");
  const [lockedHeight, setLockedHeight] = useState<number | undefined>(undefined);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const renderIdRef = useRef(0);
  const diagramRef = useRef<HTMLDivElement | null>(null);
  const renderedSourceRef = useRef<string | null>(null);

  useEffect(() => {
    setExportError(null);

    if (source.length > MERMAID_MAX_TEXT_SIZE) {
      renderIdRef.current += 1;
      setSvg(null);
      renderedSourceRef.current = null;
      setError(tRef.current("mermaid.tooLong"));
      setView("source");
      setLockedHeight(undefined);
      return;
    }

    // Same source already committed — skip (avoids scrollHeight collapse on re-entry).
    if (renderedSourceRef.current === source) {
      return;
    }

    const renderId = ++renderIdRef.current;
    setError(null);
    setLockedHeight(undefined);

    let cancelled = false;
    (async () => {
      try {
        const mod = await ensureMermaid();
        if (cancelled || renderId !== renderIdRef.current) return;
        const id = `mermaid-${renderId}-${Math.random().toString(36).slice(2, 9)}`;
        const result = await mod.default.render(id, source);
        if (cancelled || renderId !== renderIdRef.current) return;
        renderedSourceRef.current = source;
        setSvg(result.svg);
        setError(null);
        setView("diagram");
      } catch {
        if (cancelled || renderId !== renderIdRef.current) return;
        renderedSourceRef.current = null;
        setSvg(null);
        setError(tRef.current("mermaid.renderError"));
        setView("source");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [source]);

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

  const diagramBoxStyle = {
    // Lock as minHeight only — never fixed height (fixed height + overflow traps the wheel).
    minHeight: lockedHeight ?? 180,
  } as const;

  return (
    <div className="mermaid-block" data-testid="mermaid-block">
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
        <button
          type="button"
          disabled={!svg || !!error}
          onClick={() => setLightboxOpen(true)}
        >
          {t("mermaid.fullscreen")}
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
          style={diagramBoxStyle}
          role="button"
          tabIndex={0}
          onClick={() => setLightboxOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              setLightboxOpen(true);
            }
          }}
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      )}
      {!svg && !error && (
        <div className="mermaid-block-diagram" style={diagramBoxStyle} aria-busy="true">
          {t("mermaid.loading")}
        </div>
      )}
      {showSource && (
        <pre className="mermaid-block-source" data-testid="mermaid-source">
          {source}
        </pre>
      )}
      {lightboxOpen && svg && (
        <MermaidLightbox
          svg={svg}
          onClose={() => setLightboxOpen(false)}
          onExportSvg={() => void onExportSvg()}
          onExportPng={() => void onExportPng()}
        />
      )}
    </div>
  );
}
