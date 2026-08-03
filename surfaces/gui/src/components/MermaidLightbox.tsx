import { useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent, type PointerEvent as ReactPointerEvent } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "../i18n";
import { fitLightboxSize, prepareLightboxSvg } from "../mermaidSvg";

const MIN_SCALE = 0.5;
const MAX_SCALE = 8;
const DRAG_THRESHOLD_PX = 4;
const VIEWPORT_PAD = 48;

type MermaidLightboxProps = {
  svg: string;
  onClose: () => void;
  onExportSvg?: () => void;
  onExportPng?: () => void;
};

export function MermaidLightbox({
  svg,
  onClose,
  onExportSvg,
  onExportPng,
}: MermaidLightboxProps): JSX.Element {
  const { t } = useI18n();
  const prepared = useMemo(() => prepareLightboxSvg(svg), [svg]);
  const [scale, setScale] = useState(1);
  const [fit, setFit] = useState({ w: 800, h: 600 });
  const [tx, setTx] = useState(0);
  const [ty, setTy] = useState(0);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originTx: number;
    originTy: number;
    moved: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);
  const viewportRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  // Fit the SVG to the viewport; zoom changes CSS width/height (vector), not bitmap scale().
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const update = () => {
      // jsdom reports 0×0; fall back so tests and first paint still get a usable fit.
      const vw = el.clientWidth > 32 ? el.clientWidth - VIEWPORT_PAD : Math.min(window.innerWidth || 960, 960) - VIEWPORT_PAD;
      const vh = el.clientHeight > 32 ? el.clientHeight - VIEWPORT_PAD : Math.min(window.innerHeight || 720, 720) - VIEWPORT_PAD;
      setFit(
        fitLightboxSize(
          prepared.naturalW,
          prepared.naturalH,
          Math.max(1, vw),
          Math.max(1, vh),
        ),
      );
    };
    update();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", update);
      return () => window.removeEventListener("resize", update);
    }
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, [prepared.naturalW, prepared.naturalH]);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    function onWheel(event: WheelEvent) {
      event.preventDefault();
      const delta = event.deltaY > 0 ? -0.12 : 0.12;
      setScale((prev) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, +(prev + delta).toFixed(2))));
    }
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  function onPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    suppressClickRef.current = false;
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originTx: tx,
      originTy: ty,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moved && (Math.abs(dx) > DRAG_THRESHOLD_PX || Math.abs(dy) > DRAG_THRESHOLD_PX)) {
      drag.moved = true;
      suppressClickRef.current = true;
    }
    if (!drag.moved) return;
    setTx(drag.originTx + dx);
    setTy(drag.originTy + dy);
  }

  function onPointerUp(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function onViewportClick(event: ReactMouseEvent<HTMLDivElement>) {
    if (suppressClickRef.current) {
      suppressClickRef.current = false;
      return;
    }
    if (event.target === event.currentTarget) onClose();
  }

  const displayW = Math.max(1, Math.round(fit.w * scale));
  const displayH = Math.max(1, Math.round(fit.h * scale));

  return createPortal(
    <div
      className="mermaid-lightbox"
      data-testid="mermaid-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label={t("mermaid.fullscreen")}
    >
      <div className="mermaid-lightbox-toolbar">
        {onExportSvg && (
          <button type="button" onClick={() => onExportSvg()}>
            {t("mermaid.exportSvg")}
          </button>
        )}
        {onExportPng && (
          <button type="button" onClick={() => onExportPng()}>
            {t("mermaid.exportPng")}
          </button>
        )}
        <button type="button" className="mermaid-lightbox-close" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>
      <div
        ref={viewportRef}
        className="mermaid-lightbox-viewport"
        onClick={onViewportClick}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div
          className="mermaid-lightbox-stage"
          data-testid="mermaid-lightbox-stage"
          style={{
            width: displayW,
            height: displayH,
            transform: `translate(${tx}px, ${ty}px)`,
          }}
          dangerouslySetInnerHTML={{ __html: prepared.html }}
        />
      </div>
    </div>,
    document.body,
  );
}
