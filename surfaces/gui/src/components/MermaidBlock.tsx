import { useEffect, useRef, useState } from "react";
import { repairMermaid } from "../api";
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
    mermaidReady = import("mermaid")
      .then((mod) => {
        mod.default.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          maxTextSize: MERMAID_MAX_TEXT_SIZE,
          suppressErrorRendering: true,
          theme: "neo",
        });
        return mod;
      })
      .catch((err) => {
        mermaidReady = null;
        throw err;
      });
  }
  return mermaidReady;
}

type ViewMode = "diagram" | "source";
type FailKind = "syntax" | "tooLong" | "loadFailed" | null;

export type MermaidRepairContext = {
  sessionId: string;
  messageTs?: number;
  onRepaired?: (info: {
    oldSource: string;
    newSource: string;
    content: string;
    messageTs?: number;
  }) => void;
};

const autoRepairKeys = new Set<string>();

function repairKey(ctx: MermaidRepairContext, source: string): string {
  return `${ctx.sessionId}:${ctx.messageTs ?? ""}:${source.length}:${source.slice(0, 80)}`;
}

export function MermaidBlock({
  source,
  repairContext,
}: {
  source: string;
  repairContext?: MermaidRepairContext;
}): JSX.Element {
  const { t } = useI18n();
  const tRef = useRef(t);
  tRef.current = t;
  const repairRef = useRef(repairContext);
  repairRef.current = repairContext;
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [failKind, setFailKind] = useState<FailKind>(null);
  const [repairing, setRepairing] = useState(false);
  const repairingRef = useRef(false);
  const [manualLeft, setManualLeft] = useState(2);
  const [view, setView] = useState<ViewMode>("diagram");
  const [lockedHeight, setLockedHeight] = useState<number | undefined>(undefined);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const renderIdRef = useRef(0);
  const diagramRef = useRef<HTMLDivElement | null>(null);
  const renderedSourceRef = useRef<string | null>(null);
  const lastRenderErrorRef = useRef("");

  async function runRepair(isAuto: boolean) {
    const ctx = repairRef.current;
    if (!ctx?.sessionId || repairingRef.current) return;
    if (isAuto) {
      const key = repairKey(ctx, source);
      if (autoRepairKeys.has(key)) return;
      autoRepairKeys.add(key);
    } else if (manualLeft <= 0) {
      return;
    }

    repairingRef.current = true;
    setRepairing(true);
    setError(tRef.current("mermaid.repairing"));
    setExportError(null);
    try {
      const result = await repairMermaid(ctx.sessionId, {
        source,
        error: lastRenderErrorRef.current || tRef.current("mermaid.renderError"),
        message_ts: ctx.messageTs,
      });
      if (!result.ok || !result.source) {
        setError(result.error || tRef.current("mermaid.repairFailed"));
        setFailKind("syntax");
        setView("source");
        if (!isAuto) setManualLeft((n) => Math.max(0, n - 1));
        return;
      }
      const content =
        typeof result.message?.content === "string" ? result.message.content : "";
      if (content && ctx.onRepaired) {
        ctx.onRepaired({
          oldSource: source,
          newSource: result.source,
          content,
          messageTs:
            typeof result.message_ts === "number"
              ? result.message_ts
              : typeof result.message?.ts === "number"
                ? result.message.ts
                : ctx.messageTs,
        });
      } else {
        setError(tRef.current("mermaid.repairFailed"));
        setFailKind("syntax");
      }
      if (!isAuto) setManualLeft((n) => Math.max(0, n - 1));
    } catch {
      setError(tRef.current("mermaid.repairFailed"));
      setFailKind("syntax");
      setView("source");
      if (!isAuto) setManualLeft((n) => Math.max(0, n - 1));
    } finally {
      repairingRef.current = false;
      setRepairing(false);
    }
  }

  useEffect(() => {
    setExportError(null);

    if (source.length > MERMAID_MAX_TEXT_SIZE) {
      renderIdRef.current += 1;
      setSvg(null);
      renderedSourceRef.current = null;
      setError(tRef.current("mermaid.tooLong"));
      setFailKind("tooLong");
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
    setFailKind(null);
    setLockedHeight(undefined);

    let cancelled = false;
    (async () => {
      let mod: typeof import("mermaid");
      try {
        mod = await ensureMermaid();
      } catch {
        if (cancelled || renderId !== renderIdRef.current) return;
        renderedSourceRef.current = null;
        setSvg(null);
        setError(tRef.current("mermaid.loadFailed"));
        setFailKind("loadFailed");
        setView("source");
        return;
      }
      if (cancelled || renderId !== renderIdRef.current) return;
      try {
        const id = `mermaid-${renderId}-${Math.random().toString(36).slice(2, 9)}`;
        const result = await mod.default.render(id, source);
        if (cancelled || renderId !== renderIdRef.current) return;
        renderedSourceRef.current = source;
        setSvg(result.svg);
        setError(null);
        setFailKind(null);
        setView("diagram");
      } catch (err) {
        if (cancelled || renderId !== renderIdRef.current) return;
        renderedSourceRef.current = null;
        setSvg(null);
        lastRenderErrorRef.current = err instanceof Error ? err.message : String(err || "");
        setError(tRef.current("mermaid.renderError"));
        setFailKind("syntax");
        setView("source");
        const ctx = repairRef.current;
        if (ctx?.sessionId) {
          const key = repairKey(ctx, source);
          if (!autoRepairKeys.has(key)) {
            void runRepair(true);
          }
        }
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- auto-repair keyed off source only
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

  function onRetryLoad() {
    mermaidReady = null;
    renderedSourceRef.current = null;
    setError(null);
    setFailKind(null);
    setSvg(null);
    // Bump effect by forcing a noop state then re-run via source identity:
    renderIdRef.current += 1;
    const renderId = renderIdRef.current;
    setLockedHeight(undefined);
    void (async () => {
      try {
        const mod = await ensureMermaid();
        if (renderId !== renderIdRef.current) return;
        const id = `mermaid-${renderId}-${Math.random().toString(36).slice(2, 9)}`;
        const result = await mod.default.render(id, source);
        if (renderId !== renderIdRef.current) return;
        renderedSourceRef.current = source;
        setSvg(result.svg);
        setError(null);
        setFailKind(null);
        setView("diagram");
      } catch (err) {
        if (renderId !== renderIdRef.current) return;
        if (err && typeof err === "object" && "message" in err) {
          // load vs syntax: if mermaid loaded, treat as syntax
        }
        const loaded = !!mermaidReady;
        if (!loaded) {
          setError(t("mermaid.loadFailed"));
          setFailKind("loadFailed");
        } else {
          lastRenderErrorRef.current = err instanceof Error ? err.message : String(err || "");
          setError(t("mermaid.renderError"));
          setFailKind("syntax");
        }
        setView("source");
        setSvg(null);
      }
    })();
  }

  const showDiagram = view === "diagram" && !!svg && !error && !repairing;
  const showSource = view === "source" || !!error || repairing;
  const busy = repairing || (!svg && !error && !failKind);

  const diagramBoxStyle = {
    // Lock as minHeight only — never fixed height (fixed height + overflow traps the wheel).
    minHeight: lockedHeight ?? 180,
  } as const;

  const hasError = !!(error || exportError);
  const canRepair =
    !!repairContext?.sessionId &&
    failKind === "syntax" &&
    !repairing &&
    manualLeft > 0;

  return (
    <div
      className={`mermaid-block${hasError || repairing ? " is-error" : ""}`}
      data-testid="mermaid-block"
    >
      <div className="mermaid-block-toolbar">
        <button
          type="button"
          disabled={!svg || !!error || repairing}
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
        <button type="button" disabled={!svg || repairing} onClick={() => void onExportSvg()}>
          {t("mermaid.exportSvg")}
        </button>
        <button type="button" disabled={!svg || repairing} onClick={() => void onExportPng()}>
          {t("mermaid.exportPng")}
        </button>
        <button
          type="button"
          disabled={!svg || !!error || repairing}
          onClick={() => setLightboxOpen(true)}
        >
          {t("mermaid.fullscreen")}
        </button>
        {canRepair && (
          <button
            type="button"
            data-testid="mermaid-repair"
            onClick={() => void runRepair(false)}
          >
            {t("mermaid.repair")}
          </button>
        )}
        {failKind === "loadFailed" && !repairing && (
          <button type="button" data-testid="mermaid-retry-load" onClick={onRetryLoad}>
            {t("mermaid.retryLoad")}
          </button>
        )}
      </div>
      {(error || exportError || repairing) && (
        <div className="mermaid-block-error" data-testid="mermaid-error">
          {repairing ? t("mermaid.repairing") : error || exportError}
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
      {busy && !repairing && (
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
